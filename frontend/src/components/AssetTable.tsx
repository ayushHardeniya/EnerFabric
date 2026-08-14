import {
  humanizeSnakeCase,
  formatCapability,
  formatPercent,
  formatPowerKw,
  formatTimestamp,
} from "@/lib/format";
import type { Asset } from "@/types/domain";
import { StatusPill } from "./StatusPill";

export function AssetTable({ assets, detailed = false }: { assets: Asset[]; detailed?: boolean }) {
  if (assets.length === 0) {
    return (
      <p className="text-sm text-zinc-500 dark:text-zinc-400">
        No assets registered yet. Run <code className="font-mono">make seed-assets</code> (or{" "}
        <code className="font-mono">python -m app.mqtt.seed_assets</code> from{" "}
        <code className="font-mono">backend/</code>) against a running backend, then reload.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-black/10 dark:border-white/10">
      <table className="w-full min-w-[640px] text-left text-sm">
        <thead className="border-b border-black/10 text-xs uppercase tracking-wide text-zinc-500 dark:border-white/10 dark:text-zinc-400">
          <tr>
            <th className="px-4 py-2 font-medium">Asset</th>
            <th className="px-4 py-2 font-medium">Type</th>
            {detailed && <th className="px-4 py-2 font-medium">Capabilities</th>}
            <th className="px-4 py-2 font-medium">State</th>
            <th className="px-4 py-2 font-medium">Power</th>
            <th className="px-4 py-2 font-medium">SOC</th>
            <th className="px-4 py-2 font-medium">Last reading</th>
          </tr>
        </thead>
        <tbody>
          {assets.map((asset) => {
            const telemetry = asset.latest_telemetry;
            return (
              <tr key={asset.id} className="border-b border-black/5 last:border-0 dark:border-white/5">
                <td className="px-4 py-2 font-medium">{asset.name}</td>
                <td className="px-4 py-2 capitalize text-zinc-600 dark:text-zinc-300">
                  {humanizeSnakeCase(asset.type)}
                </td>
                {detailed && (
                  <td className="px-4 py-2 text-zinc-600 dark:text-zinc-300">
                    {asset.capabilities.length === 0 ? (
                      "—"
                    ) : (
                      <div className="flex flex-wrap gap-1">
                        {asset.capabilities.map((capability) => (
                          <span
                            key={capability.type}
                            className="rounded bg-zinc-100 px-1.5 py-0.5 text-xs dark:bg-zinc-800"
                          >
                            {formatCapability(capability)}
                          </span>
                        ))}
                      </div>
                    )}
                  </td>
                )}
                <td className="px-4 py-2">
                  {telemetry ? (
                    <StatusPill
                      label={telemetry.available ? telemetry.operating_state : "unavailable"}
                      tone={telemetry.available ? "positive" : "negative"}
                    />
                  ) : (
                    <StatusPill label="no telemetry" tone="neutral" />
                  )}
                </td>
                <td className="px-4 py-2 tabular-nums">
                  {telemetry ? formatPowerKw(telemetry.power_kw) : "—"}
                </td>
                <td className="px-4 py-2 tabular-nums">
                  {telemetry ? formatPercent(telemetry.soc_percent) : "—"}
                </td>
                <td className="px-4 py-2 text-zinc-500 dark:text-zinc-400">
                  {telemetry ? formatTimestamp(telemetry.timestamp) : "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
