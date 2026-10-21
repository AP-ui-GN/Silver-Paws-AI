/**
 * AI explanation layer.
 *
 * The analysis pipeline already writes a rule-based observation from the measured
 * values. A language model may only *rewrite* that text to read more naturally.
 * Anything it returns has to survive validateExplanation() first, and the
 * rule-based text is used whenever validation fails.
 *
 * The rules exist because an unchecked model will happily invent a measurement or
 * a veterinary conclusion, and this app must never show either.
 */

import type { AnalysisFactors, AnalysisMeasurements } from "@workspace/api-zod";

const MIN_LENGTH = 40;
const MAX_LENGTH = 900;

/** Numbers may drift by this much through rounding and still be accepted. */
const NUMBER_TOLERANCE = 0.05;

/** The 0-100 scale itself is always quotable. */
const SCALE_NUMBERS = [0, 100];

/**
 * Wording that turns an observation into a medical claim, a certainty, or an
 * emergency instruction. None of these belong in a wellness observation.
 */
const BANNED_TERMS = [
  "diagnos",
  "disease",
  "arthritis",
  "dysplasia",
  "fracture",
  "infection",
  "prescrib",
  "medication",
  "dosage",
  "treatment",
  "cure",
  "surgery",
  "emergency",
  "definitely",
  "certainly",
  "undoubtedly",
  "guarantee",
];

export interface ExplanationContext {
  petName?: string | undefined;
  fallbackObservation: string;
  overallScore: number | null | undefined;
  factors: AnalysisFactors;
  measurements: AnalysisMeasurements;
  signalNote: string;
  concerningChange: boolean;
}

export type ExplanationCheck =
  | { ok: true; text: string }
  | { ok: false; reason: string };

export interface ExplanationOutcome {
  observation: string;
  usedLlm: boolean;
  /** Set when a rewrite was attempted but not used, so the caller can log it. */
  rejectedReason?: string;
}

/** Every value the explanation is allowed to quote. */
export function collectAllowedNumbers(context: ExplanationContext): number[] {
  const values: (number | null | undefined)[] = [
    ...SCALE_NUMBERS,
    context.overallScore,
    context.factors.movementConsistency,
    context.factors.symmetry,
    context.factors.mobility,
    context.factors.activity,
    context.factors.historicalChange,
    context.measurements.frameCount,
    // The observation text talks about frame comparisons, which is one less.
    context.measurements.frameCount - 1,
    context.measurements.durationSeconds,
    context.measurements.motionMean,
    context.measurements.motionStd,
    context.measurements.motionCoverage,
    context.measurements.strideSymmetry,
    context.measurements.asymmetryPercent,
    context.measurements.meanKeypointConfidence,
    context.measurements.hipStability,
    context.measurements.leftHindPawMotion,
    context.measurements.rightHindPawMotion,
    context.measurements.leftForePawMotion,
    context.measurements.rightForePawMotion,
  ];

  const allowed = new Set<number>();
  for (const value of values) {
    if (typeof value !== "number" || !Number.isFinite(value)) continue;
    allowed.add(value);
    allowed.add(Math.round(value));
    allowed.add(Math.round(value * 10) / 10);
    // Percentages are commonly written from a 0-1 measurement.
    allowed.add(Math.round(value * 100) / 100);
  }

  return [...allowed];
}

/**
 * Check a model-written observation against the measured values.
 *
 * @returns the trimmed text when it is safe to show, otherwise the reason it was
 * rejected so the caller can log it and fall back.
 */
export function validateExplanation(
  candidate: string,
  context: ExplanationContext,
): ExplanationCheck {
  const text = candidate.trim();

  if (text.length < MIN_LENGTH) return { ok: false, reason: "too short" };
  if (text.length > MAX_LENGTH) return { ok: false, reason: "too long" };
  if (text.includes("http")) return { ok: false, reason: "contains a link" };

  const lowered = text.toLowerCase();
  for (const term of BANNED_TERMS) {
    if (lowered.includes(term)) {
      return { ok: false, reason: `uses disallowed wording: ${term}` };
    }
  }

  const allowed = collectAllowedNumbers(context);
  for (const token of text.match(/\d+(?:\.\d+)?/g) ?? []) {
    const value = Number(token);
    const isMeasured = allowed.some(
      (candidateValue) => Math.abs(candidateValue - value) <= NUMBER_TOLERANCE,
    );
    if (!isMeasured) {
      return { ok: false, reason: `quotes an unmeasured number: ${token}` };
    }
  }

  if (context.concerningChange && !lowered.includes("veterinar")) {
    return { ok: false, reason: "drops the veterinarian recommendation" };
  }

  return { ok: true, text };
}

/**
 * Build the prompt for a rewrite. The model is given the measured values and the
 * rule-based sentence, and is told it may not add anything else.
 */
export function buildExplanationPrompt(context: ExplanationContext): string {
  const facts = {
    petName: context.petName ?? "the pet",
    overallScore: context.overallScore ?? null,
    factors: context.factors,
    measurements: context.measurements,
    signalNote: context.signalNote,
    concerningChange: context.concerningChange,
  };

  return [
    "You rewrite pet movement observations for owners of a wellness app.",
    "Rewrite the draft so it reads naturally and kindly, in at most four sentences.",
    "Rules:",
    "- Use only the numbers and findings in the JSON below. Never add a value.",
    "- Never name a medical condition, diagnose, or say a result is certain.",
    "- Describe what was observed in the clip, not what it means medically.",
    context.concerningChange
      ? "- Keep the recommendation to speak with a veterinarian."
      : "- Do not tell the owner to visit a veterinarian urgently.",
    "",
    `Measured values: ${JSON.stringify(facts)}`,
    "",
    `Draft: ${context.fallbackObservation}`,
  ].join("\n");
}

/** Give up on a provider that has not answered in about eight seconds. */
export const REWRITE_TIMEOUT_MS = 8_000;

/**
 * Ask the configured chat-completions endpoint to rewrite the observation.
 *
 * Reads SILVERPAWS_LLM_URL, SILVERPAWS_LLM_KEY, and SILVERPAWS_LLM_MODEL.
 * Returns null when no provider is configured, the call fails, the deadline
 * passes, or the body is not a usable string. This function never throws and
 * never logs the key.
 */
export async function requestModelRewrite(
  context: ExplanationContext,
): Promise<string | null> {
  const endpoint = process.env["SILVERPAWS_LLM_URL"];
  const model = process.env["SILVERPAWS_LLM_MODEL"];
  if (!endpoint || !model) {
    // No provider configured: the rule-based observation is used as-is.
    return null;
  }

  const apiKey = process.env["SILVERPAWS_LLM_KEY"];
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (apiKey) {
    headers["Authorization"] = `Bearer ${apiKey}`;
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REWRITE_TIMEOUT_MS);

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers,
      signal: controller.signal,
      body: JSON.stringify({
        model,
        temperature: 0.2,
        messages: [{ role: "user", content: buildExplanationPrompt(context) }],
      }),
    });

    if (!response.ok) return null;

    const payload = (await response.json()) as {
      choices?: { message?: { content?: unknown } }[];
    };
    const content = payload.choices?.[0]?.message?.content;
    if (typeof content !== "string") return null;

    const text = content.trim();
    return text.length > 0 ? text : null;
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Produce the observation to show the user, preferring a validated rewrite.
 *
 * This function never throws and never returns empty text: the rule-based
 * observation from the pipeline is always available as a fallback.
 */
export async function explainObservation(
  context: ExplanationContext,
): Promise<ExplanationOutcome> {
  const fallback = context.fallbackObservation;
  let draft: string | null = null;

  try {
    draft = await requestModelRewrite(context);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return {
      observation: fallback,
      usedLlm: false,
      rejectedReason: `provider request failed: ${message}`,
    };
  }

  if (draft === null) {
    return {
      observation: fallback,
      usedLlm: false,
      // Only worth reporting when someone expected a rewrite to happen.
      ...(process.env["SILVERPAWS_LLM_URL"]
        ? { rejectedReason: "no rewrite was returned by the provider" }
        : {}),
    };
  }

  const checked = validateExplanation(draft, context);
  if (!checked.ok) {
    return { observation: fallback, usedLlm: false, rejectedReason: checked.reason };
  }

  return { observation: checked.text, usedLlm: true };
}
