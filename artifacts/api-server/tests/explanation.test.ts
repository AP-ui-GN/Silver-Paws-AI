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
  delete process.env["SILVERPAWS_LLM_KEY"];
  delete process.env["SILVERPAWS_LLM_MODEL"];

  const outcome = await explainObservation(context());

  assert.equal(outcome.observation, fallback);
  assert.equal(outcome.usedLlm, false);
  assert.equal(outcome.rejectedReason, undefined);
});

test("a configured provider that returns nothing is reported, not hidden", async () => {
  process.env["SILVERPAWS_LLM_URL"] = "https://example.invalid/v1/chat/completions";
  delete process.env["SILVERPAWS_LLM_MODEL"];
  delete process.env["SILVERPAWS_LLM_KEY"];

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

const validRewrite =
  "Mabel's walk scored 91.4 out of 100 overall, helped by steady movement " +
  "consistency of 87.6 out of 100.";

const inventedRewrite =
  "Mabel's walk scored 91.4 out of 100 overall, and her stride symmetry " +
  "reached 64.2 out of 100 during the clip.";

function providerResponse(content: string, status = 200): Response {
  return new Response(JSON.stringify({ choices: [{ message: { content } }] }), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

async function withMockProvider(
  fetchImpl: typeof fetch,
  run: () => Promise<void>,
): Promise<void> {
  const previous = {
    url: process.env["SILVERPAWS_LLM_URL"],
    key: process.env["SILVERPAWS_LLM_KEY"],
    model: process.env["SILVERPAWS_LLM_MODEL"],
    fetch: globalThis.fetch,
  };
  process.env["SILVERPAWS_LLM_URL"] = "https://llm.test/v1/chat/completions";
  process.env["SILVERPAWS_LLM_KEY"] = "sk-test-secret";
  process.env["SILVERPAWS_LLM_MODEL"] = "test-model";
  globalThis.fetch = fetchImpl;
  try {
    await run();
  } finally {
    globalThis.fetch = previous.fetch;
    if (previous.url === undefined) delete process.env["SILVERPAWS_LLM_URL"];
    else process.env["SILVERPAWS_LLM_URL"] = previous.url;
    if (previous.key === undefined) delete process.env["SILVERPAWS_LLM_KEY"];
    else process.env["SILVERPAWS_LLM_KEY"] = previous.key;
    if (previous.model === undefined) delete process.env["SILVERPAWS_LLM_MODEL"];
    else process.env["SILVERPAWS_LLM_MODEL"] = previous.model;
  }
}

test("a valid provider rewrite replaces the rule-based text", async () => {
  let authorization: string | null = null;
  let body = "";

  await withMockProvider(async (_input, init) => {
    authorization = new Headers(init?.headers).get("authorization");
    body = String(init?.body ?? "");
    return providerResponse(validRewrite);
  }, async () => {
    const outcome = await explainObservation(context());

    assert.equal(outcome.usedLlm, true);
    assert.equal(outcome.observation, validRewrite);
    assert.equal(outcome.rejectedReason, undefined);
    assert.equal(authorization, "Bearer sk-test-secret");
    assert.match(body, /"model":"test-model"/);
    assert.equal(body.includes("sk-test-secret"), false);
    assert.equal(outcome.observation.includes("sk-test-secret"), false);
  });
});

test("an invalid provider rewrite is discarded and the fallback is shown", async () => {
  await withMockProvider(async () => providerResponse(inventedRewrite), async () => {
    const outcome = await explainObservation(context());

    assert.equal(outcome.usedLlm, false);
    assert.equal(outcome.observation, fallback);
    assert.match(outcome.rejectedReason ?? "", /unmeasured number/);
  });
});

test("a provider error returns null and keeps the rule-based text", async () => {
  await withMockProvider(async () => {
    throw new Error("network down");
  }, async () => {
    const outcome = await explainObservation(context());

    assert.equal(outcome.usedLlm, false);
    assert.equal(outcome.observation, fallback);
    assert.match(outcome.rejectedReason ?? "", /no rewrite/);
  });
});

test("a slow provider is aborted and does not replace the fallback", async () => {
  const { mock } = await import("node:test");
  mock.timers.enable({ apis: ["setTimeout"] });

  try {
    await withMockProvider((_input, init) => {
      return new Promise((_resolve, reject) => {
        init?.signal?.addEventListener("abort", () => {
          reject(new DOMException("The operation was aborted", "AbortError"));
        });
      });
    }, async () => {
      const pending = explainObservation(context());
      mock.timers.tick(8_000);
      const outcome = await pending;

      assert.equal(outcome.usedLlm, false);
      assert.equal(outcome.observation, fallback);
    });
  } finally {
    mock.timers.reset();
  }
});
