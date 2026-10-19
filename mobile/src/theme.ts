/** Shared colours and spacing, matched to the warm palette of the web beta. */

export type ThemeColors = {
  background: string;
  card: string;
  border: string;
  text: string;
  muted: string;
  accent: string;
  accentSoft: string;
  good: string;
  warn: string;
  warnSoft: string;
  error: string;
  errorSoft: string;
  track: string;
};

export const colors: ThemeColors = {
  background: '#f7f2eb',
  card: '#ffffff',
  border: '#e6ddd2',
  text: '#2b2622',
  muted: '#7a6f66',
  accent: '#b9684d',
  accentSoft: '#f4e3dc',
  good: '#3d7a5a',
  warn: '#b3791c',
  warnSoft: '#fbf1dd',
  error: '#a33a2a',
  errorSoft: '#f9e4e0',
  track: '#ece4da',
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
};

export const radius = {
  sm: 8,
  md: 12,
  lg: 18,
  pill: 999,
};
