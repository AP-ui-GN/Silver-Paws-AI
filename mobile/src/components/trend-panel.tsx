import { StyleSheet, Text } from 'react-native';

import type { Analysis } from '../lib/types';
import { colors } from '../theme';
import { Card, Eyebrow } from './ui';

/**
 * ==================================================
 * TEAM TASK: KAVIN
 * PURPOSE:
 * Build the historical comparison view for the phone (score / consistency /
 * symmetry over time), matching what you build for the web in
 * artifacts/silverpaws-beta/src/components/trend-panel.tsx.
 * WHAT TO IMPLEMENT:
 * - a simple chart or table from the `analyses` prop (already newest-first)
 * - only compare walks that share the same `pipeline` value
 * - empty, single-walk, and many-walk states
 * - accessible labels (not colour-only meaning)
 * Do not fake chart data. Use saved analysis fields only.
 * ==================================================
 */
export function TrendPanel({ analyses }: { analyses: Analysis[] }) {
  const scored = analyses.filter((item) => typeof item.overallScore === 'number');
  return (
    <Card>
      <Eyebrow>Trend</Eyebrow>
      <Text style={styles.body}>
        {scored.length === 0
          ? 'Trends appear after the first scored walk.'
          : `${scored.length} scored ${scored.length === 1 ? 'walk' : 'walks'} saved. The trend view is being built by the team.`}
      </Text>
    </Card>
  );
}

const styles = StyleSheet.create({
  body: { fontSize: 14, lineHeight: 20, color: colors.text },
});
