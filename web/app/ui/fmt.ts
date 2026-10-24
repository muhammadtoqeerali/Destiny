/** Small formatting helpers shared by the Doctor and Research views. */
export const pct = (x: number, digits = 1) => `${(x * 100).toFixed(digits)}%`;
export const fixed = (x: number, digits = 3) => x.toFixed(digits);
export const int = (x: number) => x.toLocaleString('en-US');
export const prettyFeature = (f: string) =>
  f === 'phq9_score' ? 'PHQ-9 score'
  : f === 'bmi' ? 'BMI'
  : f === 'heart_failure' ? 'Heart failure'
  : f.charAt(0).toUpperCase() + f.slice(1).replaceAll('_', ' ');
