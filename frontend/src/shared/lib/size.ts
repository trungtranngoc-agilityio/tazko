const UNITS = ["B", "KB", "MB", "GB", "TB"] as const;

/** One decimal under 10, whole numbers above, as the prototype writes sizes. */
function rounded(value: number): number {
  return value < 10 ? Math.round(value * 10) / 10 : Math.round(value);
}

/** Bytes as the prototype writes sizes: "512 MB", "2 GB", "2.5 GB". */
export function size(bytes: number): string {
  let value = Math.max(0, bytes);
  let unit = 0;
  // Carry on after rounding too, so 1,048,575 bytes is "1 MB", not "1024 KB".
  while (rounded(value) >= 1024 && unit < UNITS.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${rounded(value)} ${UNITS[unit]}`;
}
