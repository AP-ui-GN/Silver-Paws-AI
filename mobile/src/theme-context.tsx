/**
 * Light and dark palettes. Screens read colors from here so a theme change
 * is not stuck in styles created at startup.
 */

import { createContext, useContext, type ReactNode } from 'react';
import { useColorScheme } from 'react-native';

import { usePreferences } from './hooks/use-preferences';
import { colors as lightColors, type ThemeColors } from './theme';

export const darkColors: ThemeColors = {
  background: '#1c1916',
  card: '#2a2522',
  border: '#3d362f',
  text: '#f4efe8',
  muted: '#c4b6a8',
  accent: '#e08a72',
  accentSoft: '#3a2a24',
  good: '#8fd4aa',
  warn: '#e0b15a',
  warnSoft: '#3a311c',
  error: '#f0a090',
  errorSoft: '#3a2420',
  track: '#3d362f',
};

const ThemeContext = createContext<ThemeColors>(lightColors);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const scheme = useColorScheme();
  const { ready, preferences } = usePreferences();
  let mode: 'light' | 'dark' = scheme === 'dark' ? 'dark' : 'light';
  if (ready && preferences.theme === 'light') mode = 'light';
  if (ready && preferences.theme === 'dark') mode = 'dark';
  const palette = mode === 'dark' ? darkColors : lightColors;
  return <ThemeContext.Provider value={palette}>{children}</ThemeContext.Provider>;
}

export function useColors(): ThemeColors {
  return useContext(ThemeContext);
}

export function useColorMode(): 'light' | 'dark' {
  const palette = useColors();
  return palette.background === darkColors.background ? 'dark' : 'light';
}
