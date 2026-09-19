"use client";

import Link from "next/link";
import { useCallback, useState } from "react";
import { ImpactSummary } from "@/components/ImpactSummary";
import { PageHeader } from "@/components/PageHeader";
import { StatCard } from "@/components/StatCard";
import { StatusMessage } from "@/components/StatusMessage";
import { formatDateTime, humanizeSnakeCase } from "@/lib/format";
import { useRealtimeEvents } from "@/lib/useRealtimeEvents";
import type { CoordinationRun } from "@/types/domain";
import type { RealtimeEvent } from "@/types/events";

export default function ImpactPage() {
  const [runs, setRuns] = useState<CoordinationRun[]>([]);

  const handleRealtimeEvent = useCallback((event: RealtimeEvent) => {
    if (event.type !== "coordination.completed") return;
    const run = event.data;
    setRuns((prev) => (prev.some((r) => r.id === run.id) ? prev : [run, ...prev]));
  }, []);

  useRealtimeEvents(handleRealtimeEvent);

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <PageHeader
        title="Impact"
        description="Measurable outcomes of each coordination decision — grid import reduction, renewable utilization, and what was actually allocated."
      />

      <StatusMessage>
        The backend&apos;s Impact Engine hasn&apos;t been implemented yet — every coordination run
        currently reports no impact metrics. This
        page will populate automatically once that engine exists; in the meantime it shows the
        real allocation outcomes of each run triggered or observed this session.
      </StatusMessage>

      <div className="mt-6">
        {runs.length === 0 ? (
          <StatusMessage>
            No coordination runs observed yet this session. Trigger one from the{" "}
            <Link href="/coordination" className="underline">
              Coordination
            </Link>{" "}
            page.
          </StatusMessage>
        ) : (
          <ul className="flex flex-col gap-6">
            {runs.map((run) => (
              <RunImpactCard key={run.id} run={run} />
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function RunImpactCard({ run }: { run: CoordinationRun }) {
  const feasible = run.allocations.filter((a) => a.feasible).length;
  const infeasible = run.allocations.length - feasible;

  return (
    <li className="rounded-lg border border-black/10 p-4 dark:border-white/10">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-medium">{humanizeSnakeCase(run.trigger_reason)}</span>
        <span className="text-xs text-zinc-500 dark:text-zinc-400">
          {formatDateTime(run.triggered_at)}
        </span>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3">
        <StatCard label="Allocations" value={String(run.allocations.length)} />
        <StatCard label="Feasible" value={String(feasible)} />
        <StatCard label="Infeasible" value={String(infeasible)} />
      </div>

      <div className="mt-4">
        {run.impact ? (
          <ImpactSummary impact={run.impact} />
        ) : (
          <StatusMessage>No impact metrics computed for this run.</StatusMessage>
        )}
      </div>
    </li>
  );
}
