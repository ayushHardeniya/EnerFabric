import type { Capability, Intent, Policy } from "@/types/domain";

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

export function humanizeSnakeCase(type: string): string {
  return type.replace(/_/g, " ");
}

export function formatCapability(capability: Capability): string {
  const parts = [`${capability.type} ${capability.max_power_kw}kW`];
  if (capability.capacity_kwh !== null) parts.push(`${capability.capacity_kwh}kWh`);
  return parts.join(" / ");
}

export function formatDateTime(value: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const PRIORITY_LABELS: Record<number, string> = {
  1: "Critical",
  2: "High",
  3: "Medium",
  4: "Low",
};

export function formatPriority(priority: number): string {
  return PRIORITY_LABELS[priority] ?? `Priority ${priority}`;
}

/**
 * Human-readable summary of what an intent asks for, per its type.
 * Pure display formatting of already-stored fields — not a decision or
 * a feasibility judgment (that's the coordination engine's job).
 */
export function describeIntent(intent: Intent): string {
  switch (intent.type) {
    case "target_soc_by_deadline":
      return `Reach ${intent.target_soc_percent}% SOC by ${formatDateTime(intent.deadline)}`;
    case "minimum_reserve":
      return `Maintain at least ${intent.min_soc_percent}% reserve`;
    case "minimum_supply":
      return `Maintain at least ${intent.min_power_kw} kW supply`;
    case "deferrable":
      if (intent.window_start && intent.window_end) {
        return `Deferrable within ${formatDateTime(intent.window_start)} – ${formatDateTime(intent.window_end)}`;
      }
      return "Deferrable, no fixed window";
    case "prefer_renewable":
      return "Prefer renewable energy";
  }
}

export function formatPolicyThreshold(policy: Policy): string {
  if (policy.threshold_kw !== null) return `${policy.threshold_kw} kW`;
  if (policy.threshold_percent !== null) return `${policy.threshold_percent}%`;
  return "—";
}
