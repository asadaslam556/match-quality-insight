export const pct = (value: number | null | undefined, digits = 1) =>
  value == null ? "n/a" : `${(value * 100).toFixed(digits)}%`;

export const num = (value: number | null | undefined, digits = 3) =>
  value == null ? "n/a" : value.toFixed(digits);
