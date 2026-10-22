/**
 * A timed-out pipeline has to die. SIGTERM is not enough when native code is
 * inside a long call, so the timeout kills the process group.
 */

import assert from "node:assert/strict";
import test from "node:test";

import { spawnAnalysisProcess, stopAnalysisProcess } from "../src/lib/analysis-runner.ts";

test("stopAnalysisProcess ends a still-running pipeline process", async () => {
  const child = spawnAnalysisProcess(process.execPath, [
    "-e",
    "setTimeout(() => {}, 30000)",
  ]);
  try {
    await new Promise<void>((resolve, reject) => {
      child.once("spawn", () => resolve());
      child.once("error", reject);
    });
    assert.ok(child.pid);
    stopAnalysisProcess(child);
    const result = await Promise.race([
      new Promise((resolve) => child.once("close", () => resolve("closed"))),
      new Promise((resolve) => setTimeout(() => resolve("running"), 3000)),
    ]);
    assert.equal(result, "closed");
  } finally {
    if (child.exitCode === null && child.pid) {
      try {
        process.kill(child.pid, "SIGKILL");
      } catch {
        // Already gone.
      }
    }
  }
});
