import { type Analysis } from '@/lib/storage';

/**
 * TEAM TASK: KAVIN
 * PURPOSE:
 * Build the historical comparison view (score / consistency / symmetry over time).
 * FILE: artifacts/silverpaws-beta/src/components/trend-panel.tsx
 * WHAT TO IMPLEMENT:
 * - charts or a simple table from the analyses prop
 * - empty, loading, and single-point states
 * - accessible labels (not color-only meaning)
 * Do not fake chart data. Use saved analysis fields only.
 */
export function TrendPanel({ analyses }: { analyses: Analysis[] }) {
  const completed = analyses.filter((item) => item.status === 'complete');
  return (
    <section className="soft-note p-5 mt-5" data-testid="kavin-trend-panel">
      <div className="eyebrow">Team task · Kavin</div>
      <h2 className="font-bold text-sm mt-2">Historical trend view</h2>
      <p className="body-muted text-sm leading-relaxed mt-2">
        {completed.length
          ? `${completed.length} saved observation${completed.length === 1 ? ' is' : 's are'} ready to chart. This panel is intentionally unfinished.`
          : 'Charts can appear here after the first walk is saved.'}
      </p>
    </section>
  );
}
