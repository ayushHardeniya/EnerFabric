/**
 * TypeScript mirrors of the backend's Pydantic domain models
 * (backend/app/domain/), matching their `model_dump(mode="json")`
 * shape exactly. This is a type-only reflection of the existing
 * backend contract, not a reimplementation of any backend logic —
 * nothing here computes, validates, or derives domain state.
 */

export type AssetType =
  | "solar"
  | "battery"
  | "ev_charger"
  | "flexible_load"
  | "critical_load"
  | "grid"
  | "site";

export type CapabilityType = "generate" | "consume" | "charge" | "discharge" | "curtail" | "defer";

export type OperatingState = "online" | "offline" | "fault" | "idle" | "active";

/** Priority.CRITICAL=1 ... Priority.LOW=4 (lower value = higher priority). */
export type Priority = 1 | 2 | 3 | 4;

export type IntentType =
  | "target_soc_by_deadline"
  | "minimum_reserve"
  | "minimum_supply"
  | "deferrable"
  | "prefer_renewable";

export type PolicyType =
  | "protect_critical_loads"
  | "maintain_battery_reserve"
  | "limit_grid_import"
  | "prefer_renewable_energy"
  | "reduce_peak_demand";

export type AllocationAction =
  | "charge"
  | "discharge"
  | "consume"
  | "generate"
  | "curtail"
  | "defer"
  | "hold";

export type CoordinationRunStatus = "pending" | "running" | "completed" | "failed";

export type TriggerReason = "solar_surplus" | "peak_demand" | "grid_outage" | "scheduled" | "manual";

export interface Capability {
  type: CapabilityType;
  max_power_kw: number;
  min_power_kw: number;
  capacity_kwh: number | null;
}

export interface Telemetry {
  asset_id: string;
  timestamp: string;
  power_kw: number;
  energy_kwh: number | null;
  soc_percent: number | null;
  available: boolean;
  operating_state: OperatingState;
}

export interface Asset {
  id: string;
  name: string;
  type: AssetType;
  capabilities: Capability[];
  latest_telemetry: Telemetry | null;
}

/** Fields every Intent subtype shares (IntentBase in the backend). */
export interface IntentBase {
  id: string;
  asset_id: string;
  priority: Priority;
  description: string;
  created_at: string;
}

export interface TargetSocByDeadlineIntent extends IntentBase {
  type: "target_soc_by_deadline";
  target_soc_percent: number;
  deadline: string;
}

export interface MinimumReserveIntent extends IntentBase {
  type: "minimum_reserve";
  min_soc_percent: number;
}

export interface MinimumSupplyIntent extends IntentBase {
  type: "minimum_supply";
  min_power_kw: number;
}

export interface DeferrableIntent extends IntentBase {
  type: "deferrable";
  window_start: string | null;
  window_end: string | null;
}

export interface PreferRenewableIntent extends IntentBase {
  type: "prefer_renewable";
}

/**
 * Mirrors backend/app/domain/intent.py's discriminated union — Intent
 * is a union of five subtypes, discriminated on `type`, each carrying
 * only the fields its shape needs.
 */
export type Intent =
  | TargetSocByDeadlineIntent
  | MinimumReserveIntent
  | MinimumSupplyIntent
  | DeferrableIntent
  | PreferRenewableIntent;

export interface Policy {
  id: string;
  type: PolicyType;
  description: string;
  priority: Priority;
  enabled: boolean;
  threshold_kw: number | null;
  threshold_percent: number | null;
}

export interface Allocation {
  id: string;
  coordination_run_id: string;
  asset_id: string;
  action: AllocationAction;
  allocated_power_kw: number | null;
  target_soc_percent: number | null;
  feasible: boolean;
  reason: string;
  source_intent_id: string | null;
  constraints_considered: string[];
}

export interface Impact {
  coordination_run_id: string;
  grid_import_reduction_kw: number | null;
  renewable_utilization_percent: number | null;
  peak_demand_reduction_kw: number | null;
  curtailed_energy_kwh: number | null;
  critical_load_served_percent: number | null;
  battery_reserve_maintained: boolean | null;
}

export interface CoordinationRun {
  id: string;
  triggered_at: string;
  trigger_reason: TriggerReason;
  status: CoordinationRunStatus;
  grid_snapshot: Telemetry | null;
  allocations: Allocation[];
  impact: Impact | null;
  summary: string | null;
}

export interface HealthResponse {
  status: string;
  service: string;
  environment: string;
}
