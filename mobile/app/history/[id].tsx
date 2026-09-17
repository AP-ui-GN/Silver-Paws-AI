/**
 * One saved walk in full: overall score, factors, raw measurements, and the
 * plain-language observation. Measurements and interpretation are shown in
 * separate sections on purpose.
 */

import { useLocalSearchParams, useRouter } from 'expo-router';
import { Alert, ScrollView, Share, StyleSheet, Text, View } from 'react-native';

import { DisclaimerFooter } from '../../src/components/disclaimer-footer';
import { FactorRow, ScoreBadge } from '../../src/components/score';
import { Button, Card, EmptyState, Eyebrow, Muted, Note, Tag } from '../../src/components/ui';
import { useLocalData } from '../../src/hooks/use-local-data';
import { EMERGENCY_NOTE, SAFETY_DISCLAIMER } from '../../src/lib/disclaimers';
import {
  FACTOR_LABELS,
  formatDateTime,
  formatDuration,
  formatMeasure,
  PIPELINE_LABELS,
  SIGNAL_LABELS,
} from '../../src/lib/format';
import type { Analysis, Pet } from '../../src/lib/types';
import { colors, spacing } from '../../src/theme';

function Measure({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.measure}>
      <Text style={styles.measureLabel}>{label}</Text>
      <Text style={styles.measureValue}>{value}</Text>
    </View>
  );
}

/** Plain-text version of the record for the share sheet. */
function buildShareText(analysis: Analysis, pet?: Pet) {
  const lines = [
    `SilverPaws AI observation for ${pet?.name ?? 'pet'} — ${formatDateTime(analysis.createdAt)}`,
    `Overall wellness indicator: ${formatMeasure(analysis.overallScore, '/100', 0)}`,
    ...FACTOR_LABELS.map((factor) => `${factor.label}: ${formatMeasure(analysis.factors[factor.key], '/100', 0)}`),
    '',
    analysis.observation,
    '',
    `Measured with: ${PIPELINE_LABELS[analysis.pipeline] ?? analysis.pipeline} (${SIGNAL_LABELS[analysis.signalQuality] ?? analysis.signalQuality})`,
    `Limitations: ${analysis.limitations}`,
    '',
    SAFETY_DISCLAIMER,
  ];
  return lines.join('\n');
}

export default function WalkDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { pets, analyses, deleteAnalysis } = useLocalData();
  const router = useRouter();

  const analysis = analyses.find((item) => item.id === id);
  const pet = analysis ? pets.find((item) => item.id === analysis.petId) : undefined;

  if (!analysis) {
    return (
      <ScrollView contentContainerStyle={styles.page}>
        <Card>
          <EmptyState icon="search-outline" title="Walk not found" body="This observation may have been deleted." />
          <Button label="Back to history" variant="secondary" onPress={() => router.replace('/history')} />
        </Card>
      </ScrollView>
    );
  }

  const measurements = analysis.measurements;

  function confirmDelete() {
    Alert.alert('Delete this walk?', 'The saved measurements and notes will be removed from this phone.', [
      { text: 'Keep', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: () => {
          deleteAnalysis(analysis!.id);
          router.replace('/history');
        },
      },
    ]);
  }

  return (
    <ScrollView contentContainerStyle={styles.page}>
      <Card>
        <View style={styles.header}>
          <ScoreBadge score={analysis.overallScore} />
          <View style={{ flex: 1, gap: 6 }}>
            <Eyebrow>Overall wellness indicator</Eyebrow>
            <Text style={styles.petName}>{pet?.name ?? 'Pet'}</Text>
            <Muted>
              {formatDateTime(analysis.createdAt)} · {formatDuration(analysis.durationSeconds)}
            </Muted>
          </View>
        </View>
        <View style={styles.tags}>
          <Tag>{SIGNAL_LABELS[analysis.signalQuality] ?? analysis.signalQuality}</Tag>
          <Tag>{PIPELINE_LABELS[analysis.pipeline] ?? analysis.pipeline}</Tag>
          {analysis.usedLlm && <Tag tone="accent">Model-written summary</Tag>}
        </View>
        {analysis.signalNote ? <Muted>{analysis.signalNote}</Muted> : null}
      </Card>

      {analysis.concerningChange && (
        <Note tone="warn" title="Worth asking a veterinarian">
          The measured change from the previous walk was large enough to mention to a vet. This is a prompt to ask a
          professional, not a diagnosis. {EMERGENCY_NOTE}
        </Note>
      )}

      <Card>
        <Eyebrow>What we noticed</Eyebrow>
        <Text style={styles.observation}>{analysis.observation}</Text>
      </Card>

      <Card>
        <Eyebrow>Factors</Eyebrow>
        <Muted>Each factor is scored 0-100 from the measurements below. "Not scored" means there was not enough signal.</Muted>
        {FACTOR_LABELS.map((factor) => (
          <FactorRow key={factor.key} label={factor.label} help={factor.help} score={analysis.factors[factor.key]} />
        ))}
        {analysis.weightsUsed && Object.keys(analysis.weightsUsed).length > 0 && (
          <Muted>
            Weights used:{' '}
            {Object.entries(analysis.weightsUsed)
              .map(([name, weight]) => `${name} ${Math.round((weight ?? 0) * 100)}%`)
              .join(' · ')}
          </Muted>
        )}
      </Card>

      <Card>
        <Eyebrow>Raw measurements</Eyebrow>
        <Muted>Exactly what the pipeline measured, with no interpretation.</Muted>
        <View style={styles.measureGrid}>
          <Measure label="Frames read" value={formatMeasure(measurements.frameCount, '', 0)} />
          <Measure label="Clip length" value={formatMeasure(measurements.durationSeconds, ' s', 1)} />
          <Measure label="Mean frame motion" value={formatMeasure(measurements.motionMean)} />
          <Measure label="Motion variation" value={formatMeasure(measurements.motionStd)} />
          <Measure label="Frames with movement" value={formatMeasure(measurements.motionCoverage * 100, '%', 0)} />
          <Measure label="Stride symmetry" value={formatMeasure(measurements.strideSymmetry)} />
          <Measure label="Asymmetry" value={formatMeasure(measurements.asymmetryPercent, '%', 1)} />
          <Measure label="Hip stability" value={formatMeasure(measurements.hipStability)} />
          <Measure label="Left ankle motion" value={formatMeasure(measurements.leftAnkleMotion)} />
          <Measure label="Right ankle motion" value={formatMeasure(measurements.rightAnkleMotion)} />
          <Measure label="Keypoint confidence" value={formatMeasure(measurements.meanKeypointConfidence)} />
          <Measure label="Symmetry reliable" value={measurements.symmetryReliable ? 'Yes' : 'No'} />
        </View>
      </Card>

      <Card>
        <Eyebrow>Limitations</Eyebrow>
        <Text style={styles.body}>{analysis.limitations}</Text>
      </Card>

      <View style={styles.actions}>
        <Button
          label="Share summary"
          icon="share-outline"
          variant="secondary"
          onPress={() => void Share.share({ message: buildShareText(analysis, pet) })}
          style={{ flex: 1 }}
        />
        <Button label="Delete" icon="trash-outline" variant="danger" onPress={confirmDelete} />
      </View>

      <DisclaimerFooter />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { padding: spacing.lg, gap: spacing.lg },
  header: { flexDirection: 'row', alignItems: 'center', gap: spacing.lg },
  petName: { fontSize: 22, fontWeight: '700', color: colors.text },
  tags: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm, marginTop: spacing.xs },
  observation: { fontSize: 16, lineHeight: 24, color: colors.text },
  body: { fontSize: 14, lineHeight: 21, color: colors.text },
  measureGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm, marginTop: spacing.xs },
  measure: {
    width: '48%',
    backgroundColor: colors.background,
    borderRadius: 10,
    padding: spacing.md,
    gap: 2,
  },
  measureLabel: { fontSize: 11, color: colors.muted, fontWeight: '600' },
  measureValue: { fontSize: 15, color: colors.text, fontWeight: '700' },
  actions: { flexDirection: 'row', gap: spacing.sm },
});
