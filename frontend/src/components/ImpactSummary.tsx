import { formatPercent, formatPowerKw } from "@/lib/format";
import type { Impact } from "@/types/domain";

export function ImpactSummary({ impact }: { impact: Impact }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      <ImpactStat label="Grid import reduction" value={formatPowerKw(impact.grid_import_reduction_kw)} />
      <ImpactStat label="Renewable utilization" value={formatPercent(impact.renewable_utilization_percent)} />
      <ImpactStat label="Peak demand reduction" value={formatPowerKw(impact.peak_demand_reduction_kw)} />
      <ImpactStat label="Curtailed energy" value={impact.curtailed_energy_kwh === null ? "—" : `${impact.curtailed_energy_kwh} kWh`} />
      <ImpactStat label="Critical load served" value={formatPercent(impact.critical_load_served_percent)} />
      <ImpactStat
        label="Battery reserve maintained"
        value={impact.battery_reserve_maintained === null ? "—" : impact.battery_reserve_maintained ? "yes" : "no"}
      />
    </div>
  );
}

function ImpactStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-black/10 px-3 py-2 dark:border-white/10">
      <p className="text-xs text-zinc-500 dark:text-zinc-400">{label}</p>
      <p className="mt-0.5 text-sm font-medium tabular-nums">{value}</p>
    </div>
  );
}
