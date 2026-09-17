/**
 * Where the analysis API lives, plus data reset and the safety text in full.
 *
 * In Expo Go the API address is guessed from the dev server, so most testers
 * never touch this screen. It exists for the cases where the guess is wrong.
 */

import Constants from 'expo-constants';
import { useEffect, useState } from 'react';
import { Alert, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';

import { Button, Card, Eyebrow, Muted, Note } from '../../src/components/ui';
import { useLocalData } from '../../src/hooks/use-local-data';
import { checkHealth, getSavedApiUrl, guessApiUrl, normalizeApiUrl, resolveApiUrl, saveApiUrl } from '../../src/lib/api';
import { EMERGENCY_NOTE, SAFETY_DISCLAIMER } from '../../src/lib/disclaimers';
import { colors, radius, spacing } from '../../src/theme';

type Status = { kind: 'idle' } | { kind: 'checking' } | { kind: 'ok'; url: string } | { kind: 'fail'; message: string };

export default function SettingsScreen() {
  const { pets, analyses, resetAll } = useLocalData();
  const [draft, setDraft] = useState('');
  const [usingSaved, setUsingSaved] = useState(false);
  const [status, setStatus] = useState<Status>({ kind: 'idle' });

  useEffect(() => {
    void (async () => {
      const saved = await getSavedApiUrl();
      setUsingSaved(Boolean(saved));
      setDraft(saved ?? (await resolveApiUrl()));
    })();
  }, []);

  async function test(urlToTest?: string) {
    const normalized = normalizeApiUrl(urlToTest ?? draft);
    if (!normalized) {
      setStatus({ kind: 'fail', message: 'Enter an address like 192.168.1.20:8080.' });
      return;
    }
    setStatus({ kind: 'checking' });
    const outcome = await checkHealth(normalized);
    setStatus(outcome.ok ? { kind: 'ok', url: normalized } : { kind: 'fail', message: outcome.message });
  }

  async function save() {
    const normalized = normalizeApiUrl(draft);
    if (!normalized) {
      setStatus({ kind: 'fail', message: 'Enter an address like 192.168.1.20:8080.' });
      return;
    }
    await saveApiUrl(normalized);
    setDraft(normalized);
    setUsingSaved(true);
    await test(normalized);
  }

  async function useDetected() {
    await saveApiUrl(null);
    setUsingSaved(false);
    const detected = await resolveApiUrl();
    setDraft(detected);
    await test(detected);
  }

  function confirmReset() {
    Alert.alert('Delete all local data?', `${pets.length} pets and ${analyses.length} walks will be removed from this phone.`, [
      { text: 'Keep', style: 'cancel' },
      { text: 'Delete everything', style: 'destructive', onPress: () => void resetAll() },
    ]);
  }

  const guess = guessApiUrl();

  return (
    <ScrollView contentContainerStyle={styles.page} keyboardShouldPersistTaps="handled">
      <Card>
        <Eyebrow>Analysis server</Eyebrow>
        <Muted>
          Clips are analyzed by the SilverPaws API running on a laptop on the same Wi-Fi network.{' '}
          {guess ? `Detected from the Expo dev server: ${guess}.` : 'No dev server address detected; enter the address by hand.'}
        </Muted>
        <TextInput
          accessibilityLabel="API server address"
          value={draft}
          onChangeText={setDraft}
          autoCapitalize="none"
          autoCorrect={false}
          keyboardType="url"
          placeholder="192.168.1.20:8080"
          placeholderTextColor={colors.muted}
          style={styles.input}
        />
        <View style={styles.row}>
          <Button label="Test connection" icon="pulse-outline" variant="secondary" onPress={() => void test()} busy={status.kind === 'checking'} style={{ flex: 1 }} />
          <Button label="Save" icon="checkmark" onPress={() => void save()} style={{ flex: 1 }} />
        </View>
        {usingSaved && <Button label="Use detected address instead" variant="secondary" onPress={() => void useDetected()} />}

        {status.kind === 'ok' && <Note tone="info" title="Connected">The API at {status.url} answered the health check.</Note>}
        {status.kind === 'fail' && <Note tone="error" title="Not reachable">{status.message}</Note>}
      </Card>

      <Card>
        <Eyebrow>Local data</Eyebrow>
        <Muted>
          {pets.length} {pets.length === 1 ? 'pet' : 'pets'} · {analyses.length} saved {analyses.length === 1 ? 'walk' : 'walks'}. Everything is stored on this
          phone only; no account exists.
        </Muted>
        <Button label="Delete all local data" icon="trash-outline" variant="danger" onPress={confirmReset} disabled={pets.length === 0 && analyses.length === 0} />
      </Card>

      <Card>
        <Eyebrow>About</Eyebrow>
        <Text style={styles.body}>{SAFETY_DISCLAIMER}</Text>
        <Text style={styles.body}>{EMERGENCY_NOTE}</Text>
        <Muted>
          SilverPaws AI mobile beta {Constants.expoConfig?.version ?? ''} · built for the Congressional App Challenge by Abhi, Sudarshan, and Kavin.
        </Muted>
      </Card>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { padding: spacing.lg, gap: spacing.lg },
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    paddingVertical: 12,
    fontSize: 16,
    color: colors.text,
    backgroundColor: colors.background,
  },
  row: { flexDirection: 'row', gap: spacing.sm },
  body: { fontSize: 14, lineHeight: 21, color: colors.text },
});
