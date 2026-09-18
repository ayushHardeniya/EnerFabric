export function formatPowerKw(value: number | null): string {
  if (value === null) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)} kW`;
}

export function formatPercent(value: number | null): string {
  if (value === null) return "—";
  return `${value.toFixed(0)}%`;
}

export function formatTimestamp(value: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function formatAssetType(type: string): string {
  return type.replace(/_/g, " ");
}
