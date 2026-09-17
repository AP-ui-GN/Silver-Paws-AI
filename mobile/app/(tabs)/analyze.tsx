/**
 * Record or choose a walking clip, send it to the analysis API, save the result.
 *
 * The screen owns the upload state machine only. Clip checks live in lib/api.ts
 * and every measurement comes back from the server; nothing is computed here.
 */

import * as ImagePicker from 'expo-image-picker';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useMemo, useRef, useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { DisclaimerFooter } from '../../src/components/disclaimer-footer';
import { ScoreBadge } from '../../src/components/score';
import { Button, Card, Chip, EmptyState, Eyebrow, Muted, Note, Tag } from '../../src/components/ui';
import { useLocalData } from '../../src/hooks/use-local-data';
import {
  checkClip,
  describeAnalysisError,
  MAX_CLIP_SECONDS,
  MAX_UPLOAD_MB,
  requestAnalysis,
  resolveApiUrl,
  type ClipAsset,
} from '../../src/lib/api';
import { formatBytes, formatDuration, SIGNAL_LABELS } from '../../src/lib/format';
import { findBaseline, toAnalysisRecord } from '../../src/lib/storage';
import type { Analysis } from '../../src/lib/types';
import { colors, radius, spacing } from '../../src/theme';

type Phase = 'idle' | 'uploading' | 'analyzing' | 'done' | 'error';

/** Map what the picker returns onto the fields the API client needs. */
function toClipAsset(asset: ImagePicker.ImagePickerAsset): ClipAsset {
  const name = asset.fileName?.trim() || `walk-${Date.now()}.mp4`;
  return {
    uri: asset.uri,
    name,
    mimeType: asset.mimeType || (name.toLowerCase().endsWith('.mov') ? 'video/quicktime' : 'video/mp4'),
    sizeBytes: typeof asset.fileSize === 'number' ? asset.fileSize : null,
    durationSeconds: typeof asset.duration === 'number' && asset.duration > 0 ? asset.duration / 1000 : null,
  };
}

export default function AnalyzeScreen() {
  const { pets, analyses, addAnalysis } = useLocalData();
  const router = useRouter();
  const params = useLocalSearchParams<{ petId?: string }>();

  const [petId, setPetId] = useState<string | null>(params.petId ?? pets[0]?.id ?? null);
  const [clip, setClip] = useState<ClipAsset | null>(null);
  const [clipProblem, setClipProblem] = useState<string | null>(null);
  const [phase, setPhase] = useState<Phase>('idle');
  const [uploadFraction, setUploadFraction] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [saved, setSaved] = useState<Analysis | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Follow the pet the user came from (Home → "Record a walk").
  useEffect(() => {
    if (params.petId) setPetId(params.petId);
  }, [params.petId]);

  // If the chosen pet was deleted, fall back to the first one.
  useEffect(() => {
    if (petId && !pets.some((pet) => pet.id === petId)) setPetId(pets[0]?.id ?? null);
  }, [pets, petId]);

  // Simple elapsed-seconds counter while work is in flight.
  const busy = phase === 'uploading' || phase === 'analyzing';
  useEffect(() => {
    if (!busy) return;
    const started = Date.now();
    const timer = setInterval(() => setElapsed(Math.round((Date.now() - started) / 1000)), 1000);
    return () => clearInterval(timer);
  }, [busy]);

  // Leaving the screen cancels an in-flight request.
  useEffect(() => () => abortRef.current?.abort(), []);

  const pet = useMemo(() => pets.find((item) => item.id === petId), [pets, petId]);

  async function pickClip(source: 'library' | 'camera') {
    setErrorMessage(null);
    setSaved(null);
    setPhase('idle');

    try {
      if (source === 'camera') {
        const permission = await ImagePicker.requestCameraPermissionsAsync();
        if (!permission.granted) {
          setClipProblem('Camera access is needed to record a walk. You can still choose a saved video.');
          return;
        }
      }

      const options: ImagePicker.ImagePickerOptions = {
        mediaTypes: ['videos'],
        allowsEditing: false,
        videoMaxDuration: 60,
        quality: 0.7,
      };
      const result =
        source === 'camera'
          ? await ImagePicker.launchCameraAsync(options)
          : await ImagePicker.launchImageLibraryAsync(options);

      if (result.canceled || !result.assets[0]) return;

      const chosen = toClipAsset(result.assets[0]);
      const problem = checkClip(chosen);
      setClipProblem(problem?.message ?? null);
      setClip(problem ? null : chosen);
    } catch {
      setClipProblem('The video could not be opened. Please try a different clip.');
    }
  }

  async function run() {
    if (!clip || !pet) return;

    const controller = new AbortController();
    abortRef.current = controller;
    setPhase('uploading');
    setUploadFraction(0);
    setElapsed(0);
    setErrorMessage(null);
    setSaved(null);

    try {
      const baseUrl = await resolveApiUrl();
      const baseline = findBaseline(analyses, pet.id);

      const result = await requestAnalysis({
        baseUrl,
        clip,
        petName: pet.name,
        previousOverall: baseline?.overallScore,
        previousPipeline: baseline?.pipeline,
        signal: controller.signal,
        onUploadProgress: (fraction) => {
          setUploadFraction(fraction);
          if (fraction >= 1) setPhase('analyzing');
        },
      });

      const record = toAnalysisRecord(result, {
        petId: pet.id,
        fileName: clip.name,
        durationSeconds: clip.durationSeconds ?? 0,
      });
      addAnalysis(record);
      setSaved(record);
      setPhase('done');
      setClip(null);
    } catch (error) {
      setErrorMessage(describeAnalysisError(error));
      setPhase('error');
    } finally {
      abortRef.current = null;
    }
  }

  function cancel() {
    abortRef.current?.abort();
  }

  if (pets.length === 0) {
    return (
      <ScrollView contentContainerStyle={styles.page}>
        <Card>
          <EmptyState icon="paw-outline" title="Add a pet first" body="Walks are saved against a pet profile so they can be compared over time." />
          <Button label="Create a pet profile" icon="add" onPress={() => router.push('/pet/new')} />
        </Card>
        <DisclaimerFooter />
      </ScrollView>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.page} keyboardShouldPersistTaps="handled">
      <Card>
        <Eyebrow>1 · Which pet?</Eyebrow>
        <View style={styles.chips}>
          {pets.map((item) => (
            <Chip key={item.id} label={item.name} selected={item.id === petId} onPress={() => setPetId(item.id)} />
          ))}
        </View>
      </Card>

      <Card>
        <Eyebrow>2 · The walk</Eyebrow>
        <Muted>
          Film from the side while your pet walks in a straight line, 5 to 60 seconds, in good light. Clips up to{' '}
          {MAX_CLIP_SECONDS} seconds and {MAX_UPLOAD_MB} MB are accepted.
        </Muted>
        <View style={styles.row}>
          <Button label="Record" icon="videocam-outline" onPress={() => pickClip('camera')} disabled={busy} style={{ flex: 1 }} />
          <Button label="Choose video" icon="images-outline" variant="secondary" onPress={() => pickClip('library')} disabled={busy} style={{ flex: 1 }} />
        </View>

        {clipProblem && <Note tone="error">{clipProblem}</Note>}

        {clip && (
          <View style={styles.clipMeta}>
            <Text style={styles.clipName} numberOfLines={1}>
              {clip.name}
            </Text>
            <Muted>
              {clip.durationSeconds ? formatDuration(clip.durationSeconds) : 'Length unknown'} · {formatBytes(clip.sizeBytes)}
            </Muted>
          </View>
        )}
      </Card>

      <Card>
        <Eyebrow>3 · Analyze</Eyebrow>
        {!busy && (
          <Button
            label={pet ? `Analyze ${pet.name}'s walk` : 'Analyze walk'}
            icon="analytics-outline"
            onPress={run}
            disabled={!clip || !pet}
          />
        )}

        {busy && (
          <View style={{ gap: spacing.sm }}>
            <Text style={styles.stage}>
              {phase === 'uploading' ? `Uploading clip · ${Math.round(uploadFraction * 100)}%` : 'Measuring movement…'}
            </Text>
            <View style={styles.track} accessibilityRole="progressbar" accessibilityValue={{ min: 0, max: 100, now: Math.round(uploadFraction * 100) }}>
              <View style={[styles.fill, { width: `${Math.max(3, uploadFraction * 100)}%` }, phase === 'analyzing' && styles.fillIndeterminate]} />
            </View>
            <Muted>
              {phase === 'analyzing'
                ? `Reading frames and comparing left and right movement. ${elapsed}s so far; short clips usually finish within 10 seconds.`
                : 'Large clips take longer on Wi-Fi. Keep the app open.'}
            </Muted>
            <Button label="Cancel" variant="secondary" onPress={cancel} />
          </View>
        )}

        {phase === 'error' && errorMessage && (
          <Note tone="error" title="Analysis did not finish">
            {errorMessage}
          </Note>
        )}

        {phase === 'done' && saved && (
          <View style={{ gap: spacing.md }}>
            <View style={styles.resultRow}>
              <ScoreBadge score={saved.overallScore} />
              <View style={{ flex: 1, gap: 6 }}>
                <Text style={styles.resultTitle}>Saved to history</Text>
                <View style={styles.chips}>
                  <Tag>{SIGNAL_LABELS[saved.signalQuality] ?? saved.signalQuality}</Tag>
                  {saved.concerningChange && <Tag tone="warn">Worth asking a vet</Tag>}
                </View>
              </View>
            </View>
            <Text style={styles.observation}>{saved.observation}</Text>
            <Button label="See the full breakdown" icon="arrow-forward" onPress={() => router.push({ pathname: '/history/[id]', params: { id: saved.id } })} />
          </View>
        )}
      </Card>

      <DisclaimerFooter />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { padding: spacing.lg, gap: spacing.lg },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  row: { flexDirection: 'row', gap: spacing.sm, marginTop: spacing.xs },
  clipMeta: { marginTop: spacing.xs, gap: 2 },
  clipName: { fontWeight: '600', color: colors.text, fontSize: 14 },
  stage: { fontWeight: '700', color: colors.text, fontSize: 15 },
  track: { height: 8, borderRadius: radius.pill, backgroundColor: colors.track, overflow: 'hidden' },
  fill: { height: '100%', backgroundColor: colors.accent, borderRadius: radius.pill },
  fillIndeterminate: { opacity: 0.6 },
  resultRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.lg },
  resultTitle: { fontSize: 18, fontWeight: '700', color: colors.text },
  observation: { fontSize: 15, lineHeight: 22, color: colors.text },
});
