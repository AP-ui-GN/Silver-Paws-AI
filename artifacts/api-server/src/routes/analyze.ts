/**
 * POST /api/analyze — measure one movement clip.
 *
 * The route owns request handling only: read the upload, check it, hand the file
 * to the analysis pipeline, let the explanation layer produce the final text, and
 * always delete the temporary file.
 */

import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

import express, { Router, type IRouter, type Request, type Response } from "express";

import { AnalyzeMovementClipResponse, type AnalyzeError } from "@workspace/api-zod";

import { runAnalysis } from "../lib/analysis-runner";
import { explainObservation } from "../lib/explanation";
import { logger } from "../lib/logger";
import { MultipartError, parseBoundary, parseMultipart } from "../lib/multipart";

const MAX_UPLOAD_MB = Number(process.env["MAX_UPLOAD_MB"] ?? 60);
const MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024;

const MAX_PET_NAME_LENGTH = 40;

const KNOWN_PIPELINES = ["movenet", "opencv-motion"];

const router: IRouter = Router();

function sendError(res: Response, status: number, error: string) {
  const body: AnalyzeError = { ok: false, error };
  res.status(status).json(body);
}

/** Keep only a short, single-line pet name for the observation text. */
function readPetName(value: string | undefined): string | undefined {
  const cleaned = value?.replace(/\s+/g, " ").trim().slice(0, MAX_PET_NAME_LENGTH);
  return cleaned ? cleaned : undefined;
}

/** Accept a previous score only when it is a real 0-100 number. */
function readPreviousOverall(value: string | undefined): number | undefined {
  if (value === undefined || value.trim() === "") return undefined;
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < 0 || parsed > 100) return undefined;
  return parsed;
}

function readPreviousPipeline(value: string | undefined): string | undefined {
  return value && KNOWN_PIPELINES.includes(value) ? value : undefined;
}

function looksLikeVideo(contentType: string, fileName: string): boolean {
  if (contentType.toLowerCase().startsWith("video/")) return true;
  // Some browsers send an empty or generic type for less common containers.
  return /\.(mp4|mov|m4v|webm|avi|mkv)$/i.test(fileName);
}

router.post(
  "/analyze",
  express.raw({ type: "multipart/form-data", limit: MAX_UPLOAD_BYTES }),
  async (req: Request, res: Response) => {
    const boundary = parseBoundary(req.headers["content-type"]);
    if (!boundary || !Buffer.isBuffer(req.body)) {
      sendError(res, 400, "The upload was not sent as a video form submission.");
      return;
    }

    let form;
    try {
      form = parseMultipart(req.body, boundary);
    } catch (error) {
      if (error instanceof MultipartError) {
        sendError(res, 400, `${error.message} Please try the upload again.`);
        return;
      }
      throw error;
    }

    const video = form.files.find((file) => file.fieldName === "video");
    if (!video || video.data.length === 0) {
      sendError(res, 400, "Choose a video file to analyze.");
      return;
    }

    if (!looksLikeVideo(video.contentType, video.fileName)) {
      sendError(
        res,
        400,
        "That file is not a video SilverPaws can read. MP4, MOV, and WebM work best.",
      );
      return;
    }

    const workingDirectory = await mkdtemp(path.join(tmpdir(), "silverpaws-clip-"));
    // The original name is never reused as a path, so a crafted filename cannot
    // escape this directory.
    const videoPath = path.join(workingDirectory, "clip");

    try {
      await writeFile(videoPath, video.data);

      const outcome = await runAnalysis({
        videoPath,
        petName: readPetName(form.fields["petName"]),
        previousOverall: readPreviousOverall(form.fields["previousOverall"]),
        previousPipeline: readPreviousPipeline(form.fields["previousPipeline"]),
      });

      if (!outcome.ok) {
        sendError(res, outcome.status, outcome.error);
        return;
      }

      const explanation = await explainObservation({
        petName: readPetName(form.fields["petName"]),
        fallbackObservation: outcome.result.observation,
        overallScore: outcome.result.overallScore,
        factors: outcome.result.factors,
        measurements: outcome.result.measurements,
        signalNote: outcome.result.signalNote,
        concerningChange: outcome.result.concerningChange,
      });

      if (explanation.rejectedReason) {
        logger.warn(
          { reason: explanation.rejectedReason },
          "Model rewrite not used; showing the rule-based observation",
        );
      }

      // Validate once more, because the observation text just changed.
      const finalResult = AnalyzeMovementClipResponse.safeParse({
        ...outcome.result,
        observation: explanation.observation,
        usedLlm: explanation.usedLlm,
      });

      if (!finalResult.success) {
        logger.error(
          { issues: finalResult.error.issues.slice(0, 5) },
          "Final analysis payload failed validation",
        );
        sendError(res, 502, "The analysis result could not be prepared for display.");
        return;
      }

      res.json(finalResult.data);
    } finally {
      await rm(workingDirectory, { recursive: true, force: true });
    }
  },
);

/**
 * Express raises this when the upload is larger than the configured limit, or the
 * body could not be read. Handled here so the client always receives our JSON
 * error shape instead of an HTML error page.
 */
router.use(
  "/analyze",
  (
    error: Error & { type?: string; status?: number },
    _req: Request,
    res: Response,
    next: (error?: unknown) => void,
  ) => {
    if (res.headersSent) {
      next(error);
      return;
    }

    if (error.type === "entity.too.large") {
      sendError(
        res,
        413,
        `That clip is larger than the ${MAX_UPLOAD_MB} MB beta limit. Try a shorter clip.`,
      );
      return;
    }

    logger.error({ err: error }, "Unexpected failure while analyzing a clip");
    sendError(res, 502, "Something went wrong while analyzing this clip.");
  },
);

export default router;
