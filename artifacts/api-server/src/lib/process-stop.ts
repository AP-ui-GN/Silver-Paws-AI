/**
 * Stop a pipeline process that has stopped answering.
 *
 * The timeout path uses SIGKILL on the process group. A long native call can
 * ignore the default terminate signal, and a child started by the pipeline
 * has to stop with it.
 */

import { spawn, type ChildProcess } from "node:child_process";

export function spawnAnalysisProcess(
  command: string,
  args: string[],
  cwd: string,
): ChildProcess {
  return spawn(command, args, {
    cwd,
    detached: process.platform !== "win32",
  });
}

export function stopAnalysisProcess(child: ChildProcess): void {
  const pid = child.pid;
  if (pid && process.platform !== "win32") {
    try {
      process.kill(-pid, "SIGKILL");
      return;
    } catch {
      // The group is already gone. Signal the child directly.
    }
  }
  try {
    child.kill("SIGKILL");
  } catch {
    // Already exited.
  }
}
