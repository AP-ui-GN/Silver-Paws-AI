/**
 * Decide whether JSON already written by the pipeline is a finished analysis.
 *
 * This file stays free of extensionless local imports so the Node test runner
 * can load it. The API still validates the same object with the generated
 * schema before sending it.
 */

// A cold pose load on a small CPU can run past two minutes. 120000 was short
// enough that the same clip timed out on every retry. This is a ceiling, not
// a typical runtime. The motion result is already on disk before pose starts.
export const DEFAULT_ANALYSIS_TIMEOUT_MS = 600_000;

export const ANALYSIS_TIMEOUT_MS = Number(
  process.env["ANALYSIS_TIMEOUT_MS"] ?? DEFAULT_ANALYSIS_TIMEOUT_MS,
);

/** The CLI reports its own failures as `{ ok: false, error: "..." }`. */
export function readPipelineFailure(payload: unknown): string | null {
  if (typeof payload !== "object" || payload === null) return null;

  const record = payload as Record<string, unknown>;
  if (record["ok"] !== false) return null;

  return typeof record["error"] === "string"
    ? record["error"]
    : "The clip could not be analyzed.";
}

/**
 * A deadline can land while pose weights are still loading. The CLI writes a
 * finished motion result before that load. A failure object is not one.
 * Stride fields may be null. They are not treated as zero.
 */
export function isFinishedAnalysis(
  payload: unknown,
): payload is Record<string, unknown> {
  if (typeof payload !== "object" || payload === null) return false;
  if (readPipelineFailure(payload) !== null) return false;

  const record = payload as Record<string, unknown>;
  if (record["ok"] !== true) return false;
  if (typeof record["pipeline"] !== "string") return false;
  if (typeof record["signalNote"] !== "string") return false;
  if (typeof record["measurements"] !== "object" || record["measurements"] === null) {
    return false;
  }

  const measurements = record["measurements"] as Record<string, unknown>;
  const stride = measurements["strideSymmetry"];
  return stride === undefined || stride === null || typeof stride === "number";
}
