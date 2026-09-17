/**
 * Tests for the AI output guard. Run with: pnpm run test
 *
 * These cases describe what the app refuses to show a user, so please add a case
 * before loosening any rule in explanation.ts.
 */

import assert from "node:assert/strict";
import test from "node:test";

import {
  buildExplanationPrompt,
  explainObservation,
  validateExplanation,
  type ExplanationContext,
} from "../src/lib/explanation.ts";

const fallback =
  "Across 44 frame comparisons, Mabel's movement scored 91.4 out of 100 overall. " +
  "That comes from movement consistency 87.6 out of 100, activity 100.0 out of 100.";

function context(overrides: Partial<ExplanationContext> = {}): ExplanationContext {
  return {
    petName: "Mabel",
    fallbackObservation: fallback,
    overallScore: 91.4,
    factors: {
      movementConsistency: 87.6,
      symmetry: null,
      mobility: null,
      activity: 100,
      historicalChange: null,
    },
    measurements: {
      frameCount: 45,
      durationSeconds: 3,
      meanKeypointConfidence: null,
      leftAnkleMotion: null,
      rightAnkleMotion: null,
      strideSymmetry: null,
      asymmetryPercent: null,
      motionMean: 0.01033,
      motionStd: 0.001278,
      motionCoverage: 1,
      hipStability: null,
      symmetryReliable: false,
    },
    signalNote: "No pet pose landmarks were available for this clip.",
    concerningChange: false,
    ...overrides,
  };
}

test("accepts a rewrite that only uses measured values", () => {
  const result = validateExplanation(
    "Mabel's walk scored 91.4 out of 100 overall, helped by steady movement " +
      "consistency of 87.6 out of 100.",
    context(),
  );

  assert.equal(result.ok, true);
});

test("rejects a rewrite that invents a measurement", () => {
  const result = validateExplanation(
    "Mabel's walk scored 91.4 out of 100 overall, and her stride symmetry " +
      "reached 64.2 out of 100 during the clip.",
    context(),
  );

  assert.equal(result.ok, false);
  assert.match(result.ok === false ? result.reason : "", /unmeasured number/);
});

test("rejects a rewrite that names a medical condition", () => {
  const result = validateExplanation(
    "Mabel's movement scored 91.4 out of 100, which is a common early sign of " +
      "arthritis in older dogs.",
    context(),
  );

  assert.equal(result.ok, false);
});

test("rejects a rewrite that claims certainty", () => {
  const result = validateExplanation(
    "Mabel is certainly moving well today, scoring 91.4 out of 100 overall.",
    context(),
  );

  assert.equal(result.ok, false);
});

test("rejects a rewrite that drops the veterinarian recommendation", () => {
  const result = validateExplanation(
    "Mabel's walk scored 91.4 out of 100 overall, which is lower than her last " +
      "saved walk, so keep watching how she moves.",
    context({ concerningChange: true }),
  );

  assert.equal(result.ok, false);
  assert.match(result.ok === false ? result.reason : "", /veterinarian/);
});

test("keeps a rewrite that retains the veterinarian recommendation", () => {
  const result = validateExplanation(
    "Mabel's walk scored 91.4 out of 100 overall, lower than her last saved walk. " +
      "It is worth asking a veterinarian to take a look.",
    context({ concerningChange: true }),
  );

  assert.equal(result.ok, true);
});

test("rejects empty and oversized rewrites", () => {
  assert.equal(validateExplanation("Fine.", context()).ok, false);
  assert.equal(validateExplanation("100 ".repeat(400), context()).ok, false);
});

test("rejects a rewrite containing a link", () => {
  const result = validateExplanation(
    "Mabel scored 91.4 out of 100 overall. Read more at http://example.com/pets.",
    context(),
  );

  assert.equal(result.ok, false);
});

test("the rule-based observation is used when no provider is configured", async () => {
  delete process.env["SILVERPAWS_LLM_URL"];

  const outcome = await explainObservation(context());

  assert.equal(outcome.observation, fallback);
  assert.equal(outcome.usedLlm, false);
  assert.equal(outcome.rejectedReason, undefined);
});

test("a configured provider that returns nothing is reported, not hidden", async () => {
  process.env["SILVERPAWS_LLM_URL"] = "https://example.invalid/v1/chat/completions";

  try {
    const outcome = await explainObservation(context());

    assert.equal(outcome.observation, fallback);
    assert.equal(outcome.usedLlm, false);
    assert.match(outcome.rejectedReason ?? "", /no rewrite/);
  } finally {
    delete process.env["SILVERPAWS_LLM_URL"];
  }
});

test("the prompt carries the measured values and the no-invention rule", () => {
  const prompt = buildExplanationPrompt(context());

  assert.match(prompt, /Never add a value/);
  assert.match(prompt, /"overallScore":91.4/);
  assert.ok(prompt.includes(fallback));
});
