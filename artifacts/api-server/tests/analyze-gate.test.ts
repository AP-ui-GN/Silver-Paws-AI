/**
 * Capacity checks happen before the upload is parsed. A refused request must
 * not call the body parser, and it must drop the socket after the reply.
 */

import assert from "node:assert/strict";
import test from "node:test";
import type { Request, Response } from "express";

import { gateAnalyzeRequest } from "../src/routes/analyze.ts";
import { resetAnalyzeSlots } from "../src/lib/hosting.ts";

const BUSY = "The analysis service is busy. Wait a moment and try again.";
const RATE = "Too many analyses from this address. Wait a minute and try again.";

function harness(remote = "203.0.113.8", forwarded?: string) {
  const events: Record<string, Array<() => void>> = {};
  let destroyed = false;
  let statusCode = 0;
  let body: { error?: string } | undefined;
  const req = {
    header(name: string) {
      if (name.toLowerCase() === "x-forwarded-for") return forwarded;
      return undefined;
    },
    socket: { remoteAddress: remote },
    destroy() {
      destroyed = true;
    },
  };
  const res = {
    status(code: number) {
      statusCode = code;
      return this;
    },
    json(payload: { error?: string }) {
      body = payload;
      return this;
    },
    on(event: string, fn: () => void) {
      events[event] = events[event] ?? [];
      events[event].push(fn);
      return this;
    },
  };
  return {
    req: req as unknown as Request,
    res: res as unknown as Response,
    events,
    get destroyed() {
      return destroyed;
    },
    get statusCode() {
      return statusCode;
    },
    get body() {
      return body;
    },
  };
}

test("a busy server refuses before the upload is read", () => {
  resetAnalyzeSlots();
  const previousConcurrent = process.env["ANALYZE_MAX_CONCURRENT"];
  const previousTrust = process.env["TRUST_PROXY"];
  process.env["ANALYZE_MAX_CONCURRENT"] = "1";
  delete process.env["TRUST_PROXY"];
  const held = harness();
  let heldNext = false;
  try {
    gateAnalyzeRequest(held.req, held.res, () => {
      heldNext = true;
    });
    assert.equal(heldNext, true);

    const refused = harness("203.0.113.9", "198.51.100.20");
    let refusedNext = false;
    gateAnalyzeRequest(refused.req, refused.res, () => {
      refusedNext = true;
    });
    assert.equal(refusedNext, false);
    assert.equal(refused.statusCode, 429);
    assert.equal(refused.body?.error, BUSY);
    assert.equal(refused.destroyed, false);
    for (const fn of refused.events["finish"] ?? []) fn();
    assert.equal(refused.destroyed, true);

    for (const fn of held.events["close"] ?? []) fn();
    const after = harness();
    let afterNext = false;
    gateAnalyzeRequest(after.req, after.res, () => {
      afterNext = true;
    });
    assert.equal(afterNext, true);
    for (const fn of after.events["close"] ?? []) fn();
  } finally {
    if (previousConcurrent === undefined) delete process.env["ANALYZE_MAX_CONCURRENT"];
    else process.env["ANALYZE_MAX_CONCURRENT"] = previousConcurrent;
    if (previousTrust === undefined) delete process.env["TRUST_PROXY"];
    else process.env["TRUST_PROXY"] = previousTrust;
    resetAnalyzeSlots();
  }
});

test("a spoofed forwarded address does not get a second rate-limit bucket", () => {
  resetAnalyzeSlots();
  const previousRate = process.env["ANALYZE_RATE_LIMIT_PER_MINUTE"];
  const previousConcurrent = process.env["ANALYZE_MAX_CONCURRENT"];
  const previousTrust = process.env["TRUST_PROXY"];
  process.env["ANALYZE_RATE_LIMIT_PER_MINUTE"] = "1";
  process.env["ANALYZE_MAX_CONCURRENT"] = "4";
  delete process.env["TRUST_PROXY"];
  const first = harness("198.51.100.8", "203.0.113.1");
  const second = harness("198.51.100.8", "203.0.113.2");
  try {
    let firstNext = false;
    gateAnalyzeRequest(first.req, first.res, () => {
      firstNext = true;
    });
    assert.equal(firstNext, true);

    let secondNext = false;
    gateAnalyzeRequest(second.req, second.res, () => {
      secondNext = true;
    });
    assert.equal(secondNext, false);
    assert.equal(second.statusCode, 429);
    assert.equal(second.body?.error, RATE);
    for (const fn of second.events["finish"] ?? []) fn();
    assert.equal(second.destroyed, true);
    for (const fn of first.events["close"] ?? []) fn();
  } finally {
    if (previousRate === undefined) delete process.env["ANALYZE_RATE_LIMIT_PER_MINUTE"];
    else process.env["ANALYZE_RATE_LIMIT_PER_MINUTE"] = previousRate;
    if (previousConcurrent === undefined) delete process.env["ANALYZE_MAX_CONCURRENT"];
    else process.env["ANALYZE_MAX_CONCURRENT"] = previousConcurrent;
    if (previousTrust === undefined) delete process.env["TRUST_PROXY"];
    else process.env["TRUST_PROXY"] = previousTrust;
    resetAnalyzeSlots();
  }
});
