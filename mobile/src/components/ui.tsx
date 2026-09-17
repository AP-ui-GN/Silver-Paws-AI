/**
 * Small building blocks used on every screen: cards, buttons, tags, notes.
 * Plain React Native views with the shared theme; nothing clever.
 */

import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps, ReactNode } from 'react';
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
  type StyleProp,
  type TextStyle,
  type ViewStyle,
} from 'react-native';

import { colors, radius, spacing } from '../theme';

export function Card({ children, style }: { children: ReactNode; style?: StyleProp<ViewStyle> }) {
  return <View style={[styles.card, style]}>{children}</View>;
}

export function Eyebrow({ children }: { children: ReactNode }) {
  return <Text style={styles.eyebrow}>{children}</Text>;
}

export function Title({ children }: { children: ReactNode }) {
  return <Text style={styles.title}>{children}</Text>;
}

export function Muted({ children, style }: { children: ReactNode; style?: StyleProp<TextStyle> }) {
  return <Text style={[styles.muted, style]}>{children}</Text>;
}

type ButtonProps = {
  label: string;
  onPress: () => void;
  icon?: ComponentProps<typeof Ionicons>['name'];
  variant?: 'primary' | 'secondary' | 'danger';
  disabled?: boolean;
  busy?: boolean;
  style?: StyleProp<ViewStyle>;
};

export function Button({ label, onPress, icon, variant = 'primary', disabled, busy, style }: ButtonProps) {
  const inactive = disabled || busy;
  const textColor = variant === 'primary' ? '#fff' : variant === 'danger' ? colors.error : colors.text;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: inactive, busy }}
      onPress={onPress}
      disabled={inactive}
      style={({ pressed }) => [
        styles.button,
        variant === 'primary' && styles.buttonPrimary,
        variant === 'secondary' && styles.buttonSecondary,
        variant === 'danger' && styles.buttonDanger,
        inactive && styles.buttonDisabled,
        pressed && !inactive && { opacity: 0.85 },
        style,
      ]}
    >
      {busy ? (
        <ActivityIndicator color={textColor} />
      ) : (
        icon && <Ionicons name={icon} size={18} color={textColor} />
      )}
      <Text style={[styles.buttonText, { color: textColor }]}>{label}</Text>
    </Pressable>
  );
}

export function Tag({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'accent' | 'warn' }) {
  return (
    <View
      style={[
        styles.tag,
        tone === 'accent' && { backgroundColor: colors.accentSoft },
        tone === 'warn' && { backgroundColor: colors.warnSoft },
      ]}
    >
      <Text style={styles.tagText}>{children}</Text>
    </View>
  );
}

/** Highlighted note: errors, warnings, and the vet-recommendation banner. */
export function Note({ tone, title, children }: { tone: 'error' | 'warn' | 'info'; title?: string; children: ReactNode }) {
  const palette = {
    error: { bg: colors.errorSoft, fg: colors.error, icon: 'alert-circle' as const },
    warn: { bg: colors.warnSoft, fg: colors.warn, icon: 'warning' as const },
    info: { bg: colors.accentSoft, fg: colors.accent, icon: 'information-circle' as const },
  }[tone];
  return (
    <View accessibilityRole="alert" style={[styles.note, { backgroundColor: palette.bg }]}>
      <Ionicons name={palette.icon} size={20} color={palette.fg} />
      <View style={{ flex: 1 }}>
        {title && <Text style={[styles.noteTitle, { color: palette.fg }]}>{title}</Text>}
        <Text style={styles.noteText}>{children}</Text>
      </View>
    </View>
  );
}

/** Selectable chip, used for pet and species pickers. */
export function Chip({ label, selected, onPress }: { label: string; selected: boolean; onPress: () => void }) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected }}
      onPress={onPress}
      style={[styles.chip, selected && styles.chipSelected]}
    >
      <Text style={[styles.chipText, selected && { color: '#fff' }]}>{label}</Text>
    </Pressable>
  );
}

export function EmptyState({ icon, title, body }: { icon: ComponentProps<typeof Ionicons>['name']; title: string; body: string }) {
  return (
    <View style={styles.empty}>
      <Ionicons name={icon} size={36} color={colors.accent} />
      <Text style={styles.emptyTitle}>{title}</Text>
      <Text style={styles.muted}>{body}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.card,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.lg,
    gap: spacing.sm,
  },
  eyebrow: {
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 1.2,
    textTransform: 'uppercase',
    color: colors.muted,
  },
  title: { fontSize: 24, fontWeight: '700', color: colors.text },
  muted: { fontSize: 13, color: colors.muted, lineHeight: 19 },
  button: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.sm,
    paddingVertical: 14,
    paddingHorizontal: spacing.lg,
    borderRadius: radius.md,
    minHeight: 48,
  },
  buttonPrimary: { backgroundColor: colors.accent },
  buttonSecondary: { backgroundColor: colors.card, borderWidth: 1, borderColor: colors.border },
  buttonDanger: { backgroundColor: colors.errorSoft },
  buttonDisabled: { opacity: 0.5 },
  buttonText: { fontSize: 15, fontWeight: '600' },
  tag: {
    backgroundColor: colors.track,
    borderRadius: radius.pill,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  tagText: { fontSize: 12, fontWeight: '600', color: colors.text },
  note: {
    flexDirection: 'row',
    gap: spacing.md,
    padding: spacing.md,
    borderRadius: radius.md,
    alignItems: 'flex-start',
  },
  noteTitle: { fontWeight: '700', fontSize: 14, marginBottom: 2 },
  noteText: { fontSize: 13, lineHeight: 19, color: colors.text },
  chip: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.card,
  },
  chipSelected: { backgroundColor: colors.accent, borderColor: colors.accent },
  chipText: { fontSize: 14, fontWeight: '600', color: colors.text },
  empty: { alignItems: 'center', gap: spacing.sm, padding: spacing.xl },
  emptyTitle: { fontSize: 17, fontWeight: '700', color: colors.text, textAlign: 'center' },
});
