/**
 * Mobile walk rules that must stay true without a device:
 * sample data is not history, and two pipelines are not compared.
 */

import assert from "node:assert/strict";
import test from "node:test";

import { vetSummaryHtml, walkReportHtml } from "../../../mobile/src/lib/report-html.ts";
import { sampleWalk } from "../../../mobile/src/lib/sample-walk.ts";
import {
  compareBlockReason,
  isDemoWalk,
  realWalks,
  recentWalks,
  weightUnitForPet,
} from "../../../mobile/src/lib/walks.ts";
import type { Analysis } from "../../../mobile/src/lib/types.ts";

function walk(id: string, pipeline: Analysis["pipeline"]): Analysis {
  return {
    ...sampleWalk,
    id,
    demo: false,
    petId: "pet-1",
    pipeline,
    modelInfo: { ...sampleWalk.modelInfo, pipeline },
    createdAt: "2026-10-02T00:00:00.000Z",
  };
}

test("sample data is not a real walk and is dropped from history helpers", () => {
  assert.equal(isDemoWalk(sampleWalk), true);
  assert.deepEqual(realWalks([sampleWalk, walk("a", "opencv-motion")]).map((item) => item.id), ["a"]);
  assert.equal(recentWalks([sampleWalk]).length, 0);
});

test("different pipelines are refused and the same pipeline is allowed", () => {
  const motion = walk("m", "opencv-motion");
  const pose = walk("p", "movenet");
  assert.match(compareBlockReason(motion, pose) ?? "", /different ways/);
  assert.equal(compareBlockReason(motion, { ...motion, id: "m2" }), null);
  assert.match(compareBlockReason(sampleWalk, motion) ?? "", /Sample data/);
});

test("a missing score is not written as zero in the report", () => {
  const html = walkReportHtml(sampleWalk, []);
  assert.match(html, /Sample data — not your pet/);
  assert.match(html, /Not measured/);
  assert.doesNotMatch(html, /Stride symmetry<\/th><td>0/);
  assert.match(html, /registry/);
  const summary = vetSummaryHtml([sampleWalk], []);
  assert.match(summary, /No saved walks yet/);
});

test("new pets use the chosen unit and older phone profiles stay labeled lb", () => {
  assert.equal(weightUnitForPet(undefined, "kg", true), "kg");
  assert.equal(weightUnitForPet(undefined, "kg", false), "lb");
  assert.equal(weightUnitForPet("lb", "kg", false), "lb");
});
