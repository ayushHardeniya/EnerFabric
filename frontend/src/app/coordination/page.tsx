"use client";

import { useCallback, useState } from "react";
import { Button } from "@/components/Button";
import { ImpactSummary } from "@/components/ImpactSummary";
import { PageHeader } from "@/components/PageHeader";
import { StatusMessage } from "@/components/StatusMessage";
import { StatusPill, type PillTone } from "@/components/StatusPill";
import { api, ApiError } from "@/lib/api";
import { formatDateTime, formatPercent, formatPowerKw, humanizeSnakeCase } from "@/lib/format";
import { useAssets } from "@/lib/useAssets";
import { useRealtimeEvents } from "@/lib/useRealtimeEvents";
import type { CoordinationRun, TriggerReason } from "@/types/domain";
import type { RealtimeEvent } from "@/types/events";

const TRIGGER_REASONS: { value: TriggerReason; label: string }[] = [
  { value: "solar_surplus", label: "Solar Surplus" },
  { value: "peak_demand", label: "Peak Demand" },
  { value: "grid_outage", label: "Grid Outage" },
  { value: "scheduled", label: "Scheduled" },
  { value: "manual", label: "Manual" },
];

function statusTone(status: CoordinationRun["status"]): PillTone {
  if (status === "completed") return "positive";
  if (status === "failed") return "negative";
  return "neutral";
}

export default function CoordinationPage() {
  const { assets } = useAssets();
  const assetNameById = new Map(assets.map((asset) => [asset.id, asset.name]));

  const [triggerReason, setTriggerReason] = useState<TriggerReason>("manual");
  const [triggering, setTriggering] = useState(false);
  const [triggerFeedback, setTriggerFeedback] = useState<
    { tone: "positive" | "negative"; message: string } | null
  >(null);

  const [runs, setRuns] = useState<CoordinationRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  const addRun = useCallback((run: CoordinationRun) => {
    setRuns((prev) => (prev.some((r) => r.id === run.id) ? prev : [run, ...prev]));
    setSelectedRunId(run.id);
  }, []);

  const handleRealtimeEvent = useCallback(
    (event: RealtimeEvent) => {
      if (event.type === "coordination.completed") addRun(event.data);
    },
    [addRun],
  );

  useRealtimeEvents(handleRealtimeEvent);

  async function handleTrigger() {
    setTriggering(true);
    setTriggerFeedback(null);
    try {
      const run = await api.triggerCoordinationRun(triggerReason);
      addRun(run);
      setTriggerFeedback({
        tone: "positive",
        message: `Run completed — ${run.allocations.length} allocation${run.allocations.length === 1 ? "" : "s"} decided.`,
      });
    } catch (err) {
      setTriggerFeedback({
        tone: "negative",
        message: err instanceof ApiError ? err.message : "Could not reach the backend.",
      });
    } finally {
      setTriggering(false);
    }
  }

  const selectedRun = runs.find((run) => run.id === selectedRunId) ?? runs[0] ?? null;

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <PageHeader
        title="Coordination"
        description="Trigger a coordination cycle and see exactly what EnerFabric decided, per asset, and why."
      />

      <section className="mt-6 rounded-lg border border-black/10 p-4 dark:border-white/10">
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
              Trigger reason
            </span>
            <select
              value={triggerReason}
              onChange={(e) => setTriggerReason(e.target.value as TriggerReason)}
              className="rounded-md border border-black/10 bg-transparent px-2 py-1.5 text-sm dark:border-white/10"
            >
              {TRIGGER_REASONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <Button onClick={handleTrigger} disabled={triggering}>
            {triggering ? "Running…" : "Run coordination"}
          </Button>
        </div>
        {triggerFeedback && (
          <p
            className={`mt-3 text-sm ${
              triggerFeedback.tone === "positive"
                ? "text-emerald-600 dark:text-emerald-400"
                : "text-red-600 dark:text-red-400"
            }`}
          >
            {triggerFeedback.message}
          </p>
        )}
      </section>

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-[280px_1fr]">
        <section>
          <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
            Recent runs
          </h2>
          <div className="mt-3">
            {runs.length === 0 ? (
              <StatusMessage>
                No runs yet this session. Trigger one above, or one broadcast by another client
                (e.g. the DER simulator) will appear here automatically.
              </StatusMessage>
            ) : (
              <ul className="flex flex-col gap-2">
                {runs.map((run) => (
                  <li key={run.id}>
                    <button
                      onClick={() => setSelectedRunId(run.id)}
                      className={`w-full rounded-md border px-3 py-2 text-left text-sm transition-colors ${
                        run.id === selectedRun?.id
                          ? "border-zinc-900 bg-zinc-50 dark:border-zinc-100 dark:bg-zinc-900"
                          : "border-black/10 hover:bg-black/5 dark:border-white/10 dark:hover:bg-white/5"
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-medium">{humanizeSnakeCase(run.trigger_reason)}</span>
                        <StatusPill label={run.status} tone={statusTone(run.status)} />
                      </div>
                      <span className="text-xs text-zinc-500 dark:text-zinc-400">
                        {formatDateTime(run.triggered_at)} · {run.allocations.length} allocation
                        {run.allocations.length === 1 ? "" : "s"}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>

        <section>
          <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
            Decision detail
          </h2>
          <div className="mt-3">
            {!selectedRun ? (
              <StatusMessage>Select a run to see its allocations and reasoning.</StatusMessage>
            ) : (
              <RunDetail run={selectedRun} assetNameById={assetNameById} />
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

function RunDetail({
  run,
  assetNameById,
}: {
  run: CoordinationRun;
  assetNameById: Map<string, string>;
}) {
  return (
    <div className="flex flex-col gap-4">
      {run.summary && (
        <p className="rounded-md bg-zinc-50 px-3 py-2 text-sm text-zinc-700 dark:bg-zinc-900 dark:text-zinc-300">
          {run.summary}
        </p>
      )}

      {run.grid_snapshot && (
        <div className="flex flex-wrap gap-4 text-sm text-zinc-600 dark:text-zinc-300">
          <span>Grid: {formatPowerKw(run.grid_snapshot.power_kw)}</span>
          <span>{run.grid_snapshot.available ? "available" : "unavailable"}</span>
        </div>
      )}

      <div className="overflow-x-auto rounded-lg border border-black/10 dark:border-white/10">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead className="border-b border-black/10 text-xs uppercase tracking-wide text-zinc-500 dark:border-white/10 dark:text-zinc-400">
            <tr>
              <th className="px-4 py-2 font-medium">Asset</th>
              <th className="px-4 py-2 font-medium">Action</th>
              <th className="px-4 py-2 font-medium">Power</th>
              <th className="px-4 py-2 font-medium">Target SOC</th>
              <th className="px-4 py-2 font-medium">Feasible</th>
              <th className="px-4 py-2 font-medium">Reason</th>
            </tr>
          </thead>
          <tbody>
            {run.allocations.map((allocation) => (
              <tr key={allocation.id} className="border-b border-black/5 align-top last:border-0 dark:border-white/5">
                <td className="px-4 py-2 font-medium">
                  {assetNameById.get(allocation.asset_id) ?? allocation.asset_id}
                </td>
                <td className="px-4 py-2 capitalize text-zinc-600 dark:text-zinc-300">
                  {allocation.action}
                </td>
                <td className="px-4 py-2 tabular-nums">
                  {formatPowerKw(allocation.allocated_power_kw)}
                </td>
                <td className="px-4 py-2 tabular-nums">
                  {formatPercent(allocation.target_soc_percent)}
                </td>
                <td className="px-4 py-2">
                  <StatusPill
                    label={allocation.feasible ? "yes" : "no"}
                    tone={allocation.feasible ? "positive" : "negative"}
                  />
                </td>
                <td className="px-4 py-2 text-zinc-600 dark:text-zinc-300">{allocation.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {run.impact ? (
        <ImpactSummary impact={run.impact} />
      ) : (
        <StatusMessage>
          No impact metrics for this run — the backend&apos;s Impact Engine hasn&apos;t been
          implemented yet (see the Impact page for details).
        </StatusMessage>
      )}
    </div>
  );
}
