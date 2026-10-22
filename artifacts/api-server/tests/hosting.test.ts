/**
 * Production HTTPS rule and the per-address analysis limit.
 */

import assert from "node:assert/strict";
import test from "node:test";

import {
  clientAddress,
  finishAnalysis,
  httpsOnlyApplies,
  positiveInteger,
  requestIsHttps,
  resetAnalyzeSlots,
  takeAnalyzeSlot,
  tryStartAnalysis,
} from "../src/lib/hosting.ts";

test("production requires https except for the health check", () => {
  assert.equal(httpsOnlyApplies("production", "/api/analyze"), true);
  assert.equal(httpsOnlyApplies("production", "/api/healthz"), false);
  assert.equal(httpsOnlyApplies("development", "/api/analyze"), false);
  assert.equal(requestIsHttps(true, undefined), true);
  assert.equal(requestIsHttps(false, "https", true), true);
  assert.equal(requestIsHttps(false, "https", false), false);
  assert.equal(requestIsHttps(false, "http, https", true), false);
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
});

test("forwarded addresses are ignored unless a proxy is trusted", () => {
  assert.equal(
    clientAddress("203.0.113.5, 198.51.100.10", "127.0.0.1", false),
    "127.0.0.1",
  );
  assert.equal(
    clientAddress("203.0.113.5, 198.51.100.10", "10.0.0.1", true),
    "198.51.100.10",
  );
  assert.equal(clientAddress(undefined, undefined, false), "unknown");
});

test("only a finite upload and timeout setting is accepted", () => {
  assert.equal(positiveInteger(undefined, 60, 1), 60);
  assert.equal(positiveInteger("not-a-number", 60, 1), 60);
  assert.equal(positiveInteger("0", 60, 1), 60);
  assert.equal(positiveInteger("15.9", 60, 1), 15);
});

test("a full analysis slot refuses the next start until one finishes", () => {
  resetAnalyzeSlots();
  const previous = process.env["ANALYZE_MAX_CONCURRENT"];
  process.env["ANALYZE_MAX_CONCURRENT"] = "1";
  try {
    assert.equal(tryStartAnalysis(), true);
    assert.equal(tryStartAnalysis(), false);
    finishAnalysis();
    assert.equal(tryStartAnalysis(), true);
    finishAnalysis();
  } finally {
    if (previous === undefined) delete process.env["ANALYZE_MAX_CONCURRENT"];
    else process.env["ANALYZE_MAX_CONCURRENT"] = previous;
    resetAnalyzeSlots();
  }
});
