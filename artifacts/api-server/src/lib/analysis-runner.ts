/**
 * Runs the Python analysis pipeline for one clip.
 *
 * The API never re-implements analysis logic. It hands a file to
 * `scripts/analyze_clip.py`, then validates whatever comes back against the
 * generated schema before anything reaches a user.
 */

import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { AnalyzeMovementClipResponse, type AnalyzeResult } from "@workspace/api-zod";

import { logger } from "./logger";

// This file is bundled to artifacts/api-server/dist, so the repository root is
// three levels up. SILVERPAWS_REPO_ROOT overrides it for other layouts.
const REPOSITORY_ROOT =
  process.env["SILVERPAWS_REPO_ROOT"] ??
  path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..", "..");

const ANALYSIS_SCRIPT = path.join(REPOSITORY_ROOT, "scripts", "analyze_clip.py");

/** Exit code the CLI uses when the uploaded clip itself was the problem. */
const CLIP_PROBLEM_EXIT_CODE = 2;

const STDERR_LOG_LIMIT = 4000;

export const ANALYSIS_TIMEOUT_MS = Number(
  process.env["ANALYSIS_TIMEOUT_MS"] ?? 120_000,
);

export interface AnalysisRequest {
  videoPath: string;
  petName?: string;
  previousOverall?: number;
  previousPipeline?: string;
}

export type AnalysisOutcome =
  | { ok: true; result: AnalyzeResult }
  | { ok: false; status: 400 | 502; error: string };

/**
 * Pick the Python interpreter to run. A project virtual environment is used when
 * present so the server does not depend on the machine's global Python.
 */
export function resolvePythonCommand(): string {
  const configured = process.env["SILVERPAWS_PYTHON"];
  if (configured) return configured;

  const candidates =
    process.platform === "win32"
      ? [path.join(REPOSITORY_ROOT, ".venv", "Scripts", "python.exe")]
      : [path.join(REPOSITORY_ROOT, ".venv", "bin", "python")];

  for (const candidate of candidates) {
    if (existsSync(candidate)) return candidate;
  }

  return process.platform === "win32" ? "python" : "python3";
}

function buildArguments(request: AnalysisRequest, outputPath: string): string[] {
  const args = [ANALYSIS_SCRIPT, request.videoPath, "--output-json", outputPath];

  if (request.petName) args.push("--pet-name", request.petName);
  if (request.previousOverall !== undefined) {
    args.push("--previous-overall", String(request.previousOverall));
  }
  if (request.previousPipeline) {
    args.push("--previous-pipeline", request.previousPipeline);
  }

  return args;
}

interface ProcessOutcome {
  exitCode: number | null;
  stdout: string;
  stderr: string;
  timedOut: boolean;
  spawnError: Error | null;
}

function runPython(command: string, args: string[]): Promise<ProcessOutcome> {
  return new Promise((resolve) => {
    const child = spawn(command, args, { cwd: REPOSITORY_ROOT });

    let stdout = "";
    let stderr = "";
    let timedOut = false;
    let spawnError: Error | null = null;

    const timer = setTimeout(() => {
      timedOut = true;
      child.kill();
    }, ANALYSIS_TIMEOUT_MS);

    child.stdout.on("data", (chunk: Buffer) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk: Buffer) => {
      if (stderr.length < STDERR_LOG_LIMIT) stderr += chunk.toString();
    });

    child.on("error", (error: Error) => {
      spawnError = error;
    });

    child.on("close", (exitCode) => {
      clearTimeout(timer);
      resolve({ exitCode, stdout, stderr, timedOut, spawnError });
    });
  });
}

/**
 * Read the JSON the CLI produced. The output file is preferred because library
 * logging can add noise to stdout.
 */
async function readPipelineJson(
  outputPath: string,
  stdout: string,
): Promise<unknown> {
  try {
    return JSON.parse(await readFile(outputPath, "utf8"));
  } catch {
    const lastJsonLine = stdout
      .split("\n")
      .map((line) => line.trim())
      .filter((line) => line.startsWith("{"))
      .pop();

    if (!lastJsonLine) return null;

    try {
      return JSON.parse(lastJsonLine);
    } catch {
      return null;
    }
  }
}

/** The CLI reports its own failures as `{ ok: false, error: "..." }`. */
function readPipelineFailure(payload: unknown): string | null {
  if (typeof payload !== "object" || payload === null) return null;

  const record = payload as Record<string, unknown>;
  if (record["ok"] !== false) return null;

  return typeof record["error"] === "string"
    ? record["error"]
    : "The clip could not be analyzed.";
}

export async function runAnalysis(
  request: AnalysisRequest,
): Promise<AnalysisOutcome> {
  const command = resolvePythonCommand();
  const outputDirectory = await mkdtemp(path.join(tmpdir(), "silverpaws-result-"));
  const outputPath = path.join(outputDirectory, "analysis.json");

  try {
    const outcome = await runPython(command, buildArguments(request, outputPath));

    if (outcome.spawnError) {
      logger.error(
        { err: outcome.spawnError, command },
        "Could not start the analysis pipeline",
      );
      return {
        ok: false,
        status: 502,
        error:
          "The analysis service is not available. Check that Python and the " +
          "requirements in requirements.txt are installed.",
      };
    }

    if (outcome.timedOut) {
      logger.error({ timeoutMs: ANALYSIS_TIMEOUT_MS }, "Analysis pipeline timed out");
      return {
        ok: false,
        status: 502,
        error: "Analysis took too long and was stopped. Try a shorter clip.",
      };
    }

    const payload = await readPipelineJson(outputPath, outcome.stdout);

    if (payload === null) {
      logger.error(
        { exitCode: outcome.exitCode, stderr: outcome.stderr },
        "Analysis pipeline returned no readable JSON",
      );
      return {
        ok: false,
        status: 502,
        error: "The analysis service returned an unreadable result.",
      };
    }

    // The pipeline reports its own failures as JSON so the message stays useful.
    const failure = readPipelineFailure(payload);
    if (failure !== null) {
      logger.warn(
        { exitCode: outcome.exitCode, message: failure },
        "Analysis pipeline failed",
      );
      return {
        ok: false,
        status: outcome.exitCode === CLIP_PROBLEM_EXIT_CODE ? 400 : 502,
        error: failure,
      };
    }

    const parsed = AnalyzeMovementClipResponse.safeParse(payload);
    if (!parsed.success) {
      logger.error(
        { issues: parsed.error.issues.slice(0, 5) },
        "Analysis result did not match the API contract",
      );
      return {
        ok: false,
        status: 502,
        error: "The analysis result did not match the expected format.",
      };
    }

    return { ok: true, result: parsed.data };
  } finally {
    await rm(outputDirectory, { recursive: true, force: true });
  }
}
