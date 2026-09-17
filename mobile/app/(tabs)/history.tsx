import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useMemo, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { DisclaimerFooter } from '../../src/components/disclaimer-footer';
import { ScoreBadge } from '../../src/components/score';
import { TrendPanel } from '../../src/components/trend-panel';
import { Button, Card, Chip, EmptyState, Muted } from '../../src/components/ui';
import { useLocalData } from '../../src/hooks/use-local-data';
import { formatDateTime, formatDuration, SIGNAL_LABELS } from '../../src/lib/format';
import { colors, spacing } from '../../src/theme';

export default function HistoryScreen() {
  const { pets, analyses } = useLocalData();
  const router = useRouter();
  const [petFilter, setPetFilter] = useState<string | null>(null);

  const visible = useMemo(
    () => (petFilter ? analyses.filter((item) => item.petId === petFilter) : analyses),
    [analyses, petFilter],
  );

  if (analyses.length === 0) {
    return (
      <ScrollView contentContainerStyle={styles.page}>
        <Card>
          <EmptyState icon="footsteps-outline" title="No walks yet" body="Each saved walk shows up here with its score, what was measured, and what it means." />
          <Button label="Record a walk" icon="videocam-outline" onPress={() => router.push('/analyze')} />
        </Card>
        <DisclaimerFooter />
      </ScrollView>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.page}>
      {pets.length > 1 && (
        <View style={styles.chips}>
          <Chip label="All pets" selected={petFilter === null} onPress={() => setPetFilter(null)} />
          {pets.map((pet) => (
            <Chip key={pet.id} label={pet.name} selected={petFilter === pet.id} onPress={() => setPetFilter(pet.id)} />
          ))}
        </View>
      )}

      <TrendPanel analyses={visible} />

      <View style={{ gap: spacing.sm }}>
        {visible.map((analysis) => {
          const pet = pets.find((item) => item.id === analysis.petId);
          return (
            <Pressable
              key={analysis.id}
              accessibilityRole="button"
              onPress={() => router.push({ pathname: '/history/[id]', params: { id: analysis.id } })}
              style={({ pressed }) => [styles.item, pressed && { opacity: 0.8 }]}
            >
              <ScoreBadge score={analysis.overallScore} size="small" />
              <View style={{ flex: 1, gap: 2 }}>
                <Text style={styles.itemTitle}>{pet?.name ?? 'Pet'}</Text>
                <Muted>
                  {formatDateTime(analysis.createdAt)} · {formatDuration(analysis.durationSeconds)}
                </Muted>
                <Muted>
                  {SIGNAL_LABELS[analysis.signalQuality] ?? analysis.signalQuality}
                  {analysis.concerningChange ? ' · worth asking a vet' : ''}
                </Muted>
              </View>
              <Ionicons name="chevron-forward" size={18} color={colors.muted} />
            </Pressable>
          );
        })}
      </View>

      <DisclaimerFooter />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { padding: spacing.lg, gap: spacing.lg },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  item: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 14,
    padding: spacing.md,
  },
  itemTitle: { fontSize: 16, fontWeight: '700', color: colors.text },
});
