import { Ionicons } from '@expo/vector-icons';
import { StyleSheet, Text, View } from 'react-native';

import { EMERGENCY_NOTE, SAFETY_DISCLAIMER } from '../lib/disclaimers';
import { colors, spacing } from '../theme';

/** Shown at the bottom of every screen so the safety message is never out of view for long. */
export function DisclaimerFooter() {
  return (
    <View style={styles.footer} accessibilityRole="summary">
      <Ionicons name="shield-checkmark-outline" size={18} color={colors.muted} />
      <View style={{ flex: 1, gap: 4 }}>
        <Text style={styles.text}>{SAFETY_DISCLAIMER}</Text>
        <Text style={styles.text}>{EMERGENCY_NOTE}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  footer: {
    flexDirection: 'row',
    gap: spacing.md,
    paddingVertical: spacing.xl,
    paddingHorizontal: spacing.xs,
    alignItems: 'flex-start',
  },
  text: { fontSize: 11, lineHeight: 16, color: colors.muted },
});
