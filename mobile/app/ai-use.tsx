/**
 * Placeholder until the AI-use registry is wired. No extra claims.
 */

import { ScrollView, StyleSheet } from 'react-native';

import { Card, Muted, Title } from '../src/components/ui';
import { spacing } from '../src/theme';

export default function AiUseScreen() {
  return (
    <ScrollView contentContainerStyle={styles.page}>
      <Card>
        <Title>How AI is used</Title>
        <Muted>
          The detailed list will come from the project registry. This screen does not add medical claims, and it does not
          describe any model that is not already named on a saved walk.
        </Muted>
      </Card>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { padding: spacing.lg },
});
