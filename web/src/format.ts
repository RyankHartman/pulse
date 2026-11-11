export const compact = (n: number): string => {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 100_000) return `${Math.round(n / 1000)}K`;
  if (n >= 10_000) return `${(n / 1000).toFixed(0)}K`;
  if (n >= 1_000) return `${(n / 1000).toFixed(1)}K`;
  return `${Math.round(n)}`;
};

export const pct = (n: number, digits = 0): string => `${(n * 100).toFixed(digits)}%`;

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** "2018-12-07" or "2018-12-07T09:00" -> "Dec 7". Parses by hand so time zones never shift the day. */
export const shortDate = (iso: string): string => {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  void y;
  return `${MONTHS[(m ?? 1) - 1]} ${d}`;
};

export const longDate = (iso: string): string => {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return `${MONTHS[(m ?? 1) - 1]} ${d}, ${y}`;
};

export const hourLabel = (iso: string): string => {
  const hour = iso.length > 10 ? Number(iso.slice(11, 13)) : 0;
  return `${shortDate(iso)} ${String(hour).padStart(2, "0")}:00`;
};
