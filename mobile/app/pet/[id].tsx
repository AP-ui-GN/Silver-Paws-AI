/** Create (`/pet/new`) or edit (`/pet/<id>`) a pet profile. Plain form, local save. */

import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import { Alert, KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';

import { DisclaimerFooter } from '../../src/components/disclaimer-footer';
import { Button, Card, Chip, Eyebrow, Muted } from '../../src/components/ui';
import { useLocalData } from '../../src/hooks/use-local-data';
import { petFormIsValid, validatePetForm, type PetFormErrors } from '../../src/lib/pet-form';
import type { PetInput } from '../../src/lib/types';
import { colors, radius, spacing } from '../../src/theme';

const SPECIES = ['Dog', 'Cat', 'Other'];

const EMPTY: PetInput = { name: '', species: 'Dog', breed: '', age: '', weight: '', notes: '' };

function Field({
  label,
  value,
  onChange,
  placeholder,
  keyboardType,
  multiline,
  error,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  keyboardType?: 'default' | 'decimal-pad';
  multiline?: boolean;
  error?: string;
}) {
  return (
    <View style={{ gap: 6 }}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        accessibilityLabel={label}
        value={value}
        onChangeText={onChange}
        placeholder={placeholder}
        placeholderTextColor={colors.muted}
        keyboardType={keyboardType}
        multiline={multiline}
        aria-invalid={error ? true : undefined}
        style={[styles.input, multiline && styles.inputMultiline, error && styles.inputError]}
      />
      {error ? (
        <Text accessibilityRole="alert" style={styles.error}>
          {error}
        </Text>
      ) : null}
    </View>
  );
}

export default function PetScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { pets, addPet, updatePet, deletePet } = useLocalData();
  const router = useRouter();

  const existing = id === 'new' ? undefined : pets.find((pet) => pet.id === id);
  const [form, setForm] = useState<PetInput>(
    existing
      ? { name: existing.name, species: existing.species, breed: existing.breed, age: existing.age, weight: existing.weight, notes: existing.notes }
      : EMPTY,
  );

  const [attempted, setAttempted] = useState(false);
  const set = (key: keyof PetInput) => (value: string) => setForm((current) => ({ ...current, [key]: value }));
  const validated = validatePetForm(form);
  const errors: PetFormErrors = {
    ...(attempted ? validated : {}),
    ...(validated.age ? { age: validated.age } : {}),
    ...(validated.weight ? { weight: validated.weight } : {}),
  };

  function save() {
    const next = validatePetForm(form);
    setAttempted(true);
    if (!petFormIsValid(next)) return;

    if (existing) {
      updatePet(existing.id, form);
      router.back();
    } else {
      const created = addPet(form);
      router.replace({ pathname: '/analyze', params: { petId: created.id } });
    }
  }

  function confirmDelete() {
    if (!existing) return;
    Alert.alert(`Remove ${existing.name}?`, 'Their saved walks will be removed from this phone as well.', [
      { text: 'Keep', style: 'cancel' },
      {
        text: 'Remove',
        style: 'destructive',
        onPress: () => {
          deletePet(existing.id);
          router.replace('/');
        },
      },
    ]);
  }

  return (
    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1 }}>
      <ScrollView contentContainerStyle={styles.page} keyboardShouldPersistTaps="handled">
        <Card>
          <Eyebrow>{existing ? 'Edit profile' : 'New pet'}</Eyebrow>
          <Muted>Only a name is required. Nothing here leaves the phone.</Muted>

          <Field label="Name" value={form.name} onChange={set('name')} placeholder="Mabel" error={errors.name} />

          <View style={{ gap: 6 }}>
            <Text style={styles.label}>Species</Text>
            <View style={styles.chips}>
              {SPECIES.map((species) => (
                <Chip key={species} label={species} selected={form.species === species} onPress={() => set('species')(species)} />
              ))}
            </View>
          </View>

          <Field label="Breed" value={form.breed} onChange={set('breed')} placeholder="Labrador mix" />
          <View style={styles.row}>
            <View style={{ flex: 1 }}>
              <Field label="Age (years)" value={form.age} onChange={set('age')} placeholder="9" keyboardType="decimal-pad" error={errors.age} />
            </View>
            <View style={{ flex: 1 }}>
              <Field label="Weight (lb)" value={form.weight} onChange={set('weight')} placeholder="62" keyboardType="decimal-pad" error={errors.weight} />
            </View>
          </View>
          <Field
            label="Baseline notes"
            value={form.notes}
            onChange={set('notes')}
            placeholder="What a normal walk looks like, past injuries, anything a future you would want to remember."
            multiline
          />

          <Button label={existing ? 'Save changes' : 'Save and record a walk'} icon="checkmark" onPress={save} />
          {existing && <Button label="Remove pet" icon="trash-outline" variant="danger" onPress={confirmDelete} />}
        </Card>
        <DisclaimerFooter />
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  page: { padding: spacing.lg, gap: spacing.lg },
  label: { fontSize: 13, fontWeight: '600', color: colors.text },
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
  inputMultiline: { minHeight: 90, textAlignVertical: 'top' },
  inputError: { borderColor: colors.error },
  error: { fontSize: 13, lineHeight: 18, color: colors.error },
  chips: { flexDirection: 'row', gap: spacing.sm },
  row: { flexDirection: 'row', gap: spacing.md },
});
