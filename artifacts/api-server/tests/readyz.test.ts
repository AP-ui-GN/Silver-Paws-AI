import assert from "node:assert/strict";
import { once } from "node:events";
import { createServer, type Server } from "node:http";
import type { AddressInfo } from "node:net";
import express from "express";
import test from "node:test";

import { createHealthRouter } from "../src/routes/health.ts";
import type { ReadinessReport } from "../src/lib/readiness.ts";

const readyReport: ReadinessReport = {
  status: "ready",
  capabilities: ["opencv-motion"],
  poseModelAvailable: false,
  warnings: [
    "Optional pose dependencies or cached weights are unavailable; only OpenCV picture-motion analysis is available.",
    "Stride length and left/right gait symmetry remain unmeasured with the current checkpoint.",
  ],
};

async function withReadyServer(
  report: ReadinessReport,
  testBody: (baseUrl: string) => Promise<void>,
): Promise<void> {
  const app = express();
  app.use("/api", createHealthRouter(async () => report));
  const server: Server = createServer(app);
  server.listen(0, "127.0.0.1");
  await once(server, "listening");

  try {
    const address = server.address() as AddressInfo;
    await testBody(`http://127.0.0.1:${address.port}`);
  } finally {
    await new Promise<void>((resolve, reject) => {
      server.close((error) => (error ? reject(error) : resolve()));
    });
  }
}

test("readiness returns 200 when the OpenCV fallback is available even without pose weights", async () => {
  await withReadyServer(readyReport, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/readyz`);
    assert.equal(response.status, 200);
    const body = await response.json();
    assert.equal(body.status, "ready");
    assert.deepEqual(body.capabilities, ["opencv-motion"]);
    assert.equal(body.poseModelAvailable, false);
    assert.match(body.warnings.join(" "), /Stride length and left\/right gait symmetry remain unmeasured/);
  });
});

test("readiness returns 503 when the required Python/OpenCV fallback is unavailable", async () => {
  await withReadyServer(
    {
      status: "unavailable",
      capabilities: [],
      poseModelAvailable: false,
      warnings: ["Python is running, but OpenCV is unavailable."],
    },
    async (baseUrl) => {
      const response = await fetch(`${baseUrl}/api/readyz`);
      assert.equal(response.status, 503);
      const body = await response.json();
      assert.equal(body.status, "unavailable");
      assert.deepEqual(body.capabilities, []);
    },
  );
});
