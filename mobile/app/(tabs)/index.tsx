import { Ionicons } from '@expo/vector-icons';
import { Link, useRouter } from 'expo-router';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { DisclaimerFooter } from '../../src/components/disclaimer-footer';
import { ScoreBadge } from '../../src/components/score';
import { Button, Card, EmptyState, Eyebrow, Muted, Title } from '../../src/components/ui';
import { useLocalData } from '../../src/hooks/use-local-data';
import { formatDate } from '../../src/lib/format';
import type { Analysis, Pet } from '../../src/lib/types';
import { colors, spacing } from '../../src/theme';

function describePet(pet: Pet) {
  const parts = [pet.species, pet.breed].filter((part) => part.trim());
  const age = pet.age.trim();
  if (age) parts.push(/^\d+(\.\d+)?$/.test(age) ? `${age} yrs` : age);
  return parts.join(' · ') || 'No details yet';
}

function PetCard({ pet, latest }: { pet: Pet; latest?: Analysis }) {
  const router = useRouter();
  return (
    <Card>
      <View style={styles.petRow}>
        <View style={{ flex: 1, gap: 4 }}>
          <Text style={styles.petName}>{pet.name}</Text>
          <Muted>{describePet(pet)}</Muted>
          <Muted>{latest ? `Last walk ${formatDate(latest.createdAt)}` : 'No walks recorded yet'}</Muted>
        </View>
        <ScoreBadge score={latest?.overallScore} size="small" />
      </View>
      <View style={styles.petActions}>
        <Button
          label="Record a walk"
          icon="videocam-outline"
          onPress={() => router.push({ pathname: '/analyze', params: { petId: pet.id } })}
          style={{ flex: 1 }}
        />
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={`Edit ${pet.name}`}
          onPress={() => router.push({ pathname: '/pet/[id]', params: { id: pet.id } })}
          style={styles.iconButton}
        >
          <Ionicons name="create-outline" size={20} color={colors.text} />
        </Pressable>
      </View>
    </Card>
  );
}

export default function HomeScreen() {
  const { loading, pets, analyses } = useLocalData();
  const router = useRouter();

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={colors.accent} />
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.page}>
      <View style={{ gap: 4 }}>
        <Eyebrow>Observational wellness notes</Eyebrow>
        <Title>{pets.length ? 'Your pets' : 'Welcome'}</Title>
        <Muted>
          Record a short walk, and SilverPaws measures how steady and even the movement looked. It never diagnoses.
        </Muted>
      </View>

      {pets.length === 0 ? (
        <Card>
          <EmptyState
            icon="paw-outline"
            title="Add your first pet"
            body="A profile only needs a name. Breed, age, and notes help you remember what a normal walk looks like."
          />
          <Button label="Create a pet profile" icon="add" onPress={() => router.push('/pet/new')} />
        </Card>
      ) : (
        <>
          {pets.map((pet) => (
            <PetCard key={pet.id} pet={pet} latest={analyses.find((item) => item.petId === pet.id)} />
          ))}
          <Button label="Add another pet" icon="add" variant="secondary" onPress={() => router.push('/pet/new')} />
        </>
      )}

      {analyses.length > 0 && (
        <Link href="/history" asChild>
          <Pressable accessibilityRole="link" style={styles.historyLink}>
            <Ionicons name="time-outline" size={18} color={colors.accent} />
            <Text style={styles.historyText}>
              {analyses.length} saved {analyses.length === 1 ? 'walk' : 'walks'} · open history
            </Text>
          </Pressable>
        </Link>
      )}

      <DisclaimerFooter />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { padding: spacing.lg, gap: spacing.lg },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  petRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  petName: { fontSize: 20, fontWeight: '700', color: colors.text },
  petActions: { flexDirection: 'row', gap: spacing.sm, marginTop: spacing.sm },
  iconButton: {
    width: 48,
    height: 48,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.card,
  },
  historyLink: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, paddingVertical: spacing.sm },
  historyText: { color: colors.accent, fontWeight: '600', fontSize: 14 },
});
