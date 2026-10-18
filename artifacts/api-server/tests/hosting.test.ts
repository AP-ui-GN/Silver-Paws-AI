/**
 * Production HTTPS rule and the per-address analysis limit.
 */

import assert from "node:assert/strict";
import test from "node:test";

import {
  clientAddress,
  httpsOnlyApplies,
  requestIsHttps,
  resetAnalyzeSlots,
  takeAnalyzeSlot,
} from "../src/lib/hosting.ts";

test("production requires https except for the health check", () => {
  assert.equal(httpsOnlyApplies("production", "/api/analyze"), true);
  assert.equal(httpsOnlyApplies("production", "/api/healthz"), false);
  assert.equal(httpsOnlyApplies("development", "/api/analyze"), false);
  assert.equal(requestIsHttps(true, undefined), true);
  assert.equal(requestIsHttps(false, "https"), true);
  assert.equal(requestIsHttps(false, "http, https"), false);
  assert.equal(requestIsHttps(false, undefined), false);
});

test("the analysis limit counts a client and then refuses", () => {
  resetAnalyzeSlots();
  const now = 1_000_000;
  assert.equal(takeAnalyzeSlot("10.0.0.8", now, 2), true);
  assert.equal(takeAnalyzeSlot("10.0.0.8", now + 1, 2), true);
  assert.equal(takeAnalyzeSlot("10.0.0.8", now + 2, 2), false);
  assert.equal(takeAnalyzeSlot("10.0.0.9", now + 2, 2), true);
  assert.equal(takeAnalyzeSlot("10.0.0.8", now + 60_001, 2), true);
  assert.equal(clientAddress("203.0.113.5, 10.0.0.1", "127.0.0.1"), "203.0.113.5");
});
