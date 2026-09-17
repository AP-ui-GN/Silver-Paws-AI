import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { LocalDataProvider } from '../src/hooks/use-local-data';
import { colors } from '../src/theme';

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <LocalDataProvider>
        <StatusBar style="dark" />
        <Stack
          screenOptions={{
            headerStyle: { backgroundColor: colors.background },
            headerTintColor: colors.text,
            headerShadowVisible: false,
            contentStyle: { backgroundColor: colors.background },
          }}
        >
          <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
          <Stack.Screen name="history/[id]" options={{ title: 'Walk details' }} />
          <Stack.Screen name="pet/[id]" options={{ title: 'Pet profile' }} />
        </Stack>
      </LocalDataProvider>
    </SafeAreaProvider>
  );
}
