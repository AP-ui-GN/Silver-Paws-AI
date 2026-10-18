/**
 * Rules for saved walks. Demo rows are not walks, and two pipelines are never
 * compared as if they were the same measurement.
 */

import type { Analysis } from './types.ts';

export const SAMPLE_WALK_ID = 'sample-walk';

export const VET_SUMMARY_LIMIT = 8;

export type WeightUnit = 'kg' | 'lb';

/** Unit shown on a pet form. Old phone profiles were labeled lb and are not converted. */
export function weightUnitForPet(stored: WeightUnit | undefined, preference: WeightUnit, isNew: boolean): WeightUnit {
  if (stored === 'kg' || stored === 'lb') return stored;
  if (isNew) return preference;
  return 'lb';
}

export function isDemoWalk(walk: { id?: string; demo?: boolean } | null | undefined): boolean {
  return Boolean(walk && (walk.demo || walk.id === SAMPLE_WALK_ID));
}

/** Saved walks only. Sample data is dropped even if it was written by mistake. */
export function realWalks(walks: Analysis[]): Analysis[] {
  return walks.filter((walk) => !isDemoWalk(walk));
}

export function walksForPet(walks: Analysis[], petId: string): Analysis[] {
  return realWalks(walks).filter((walk) => walk.petId === petId);
}

/**
 * Why two walks cannot be shown side by side, or null when they can.
 * Different pipelines are refused. Demo rows are refused.
 */
export function compareBlockReason(left: Analysis, right: Analysis): string | null {
  if (isDemoWalk(left) || isDemoWalk(right)) {
    return 'Sample data is not a saved walk, so it is not compared with a real one.';
  }
  if (left.id === right.id) {
    return 'Choose two different saved walks.';
  }
  if (left.pipeline !== right.pipeline) {
    return 'These walks were measured in different ways, so they are not shown side by side.';
  }
  return null;
}

/** Newest first, real walks only, capped for the vet summary. */
export function recentWalks(walks: Analysis[], limit = VET_SUMMARY_LIMIT): Analysis[] {
  return realWalks(walks)
    .slice()
    .sort((a, b) => b.createdAt.localeCompare(a.createdAt))
    .slice(0, limit);
}
