"use client";

import { useCallback, useEffect, useState } from "react";
import { AssetTable } from "@/components/AssetTable";
import { EventLog } from "@/components/EventLog";
import { StatCard } from "@/components/StatCard";
import { StatusPill, type PillTone } from "@/components/StatusPill";
import { api, ApiError } from "@/lib/api";
import { API_BASE_URL } from "@/lib/config";
import { useRealtimeEvents, type RealtimeConnectionStatus } from "@/lib/useRealtimeEvents";
import type { Asset } from "@/types/domain";
import type { RealtimeEvent } from "@/types/events";

type LoadState = "loading" | "ready" | "error";

const MAX_LOGGED_EVENTS = 10;

export default function HomePage() {
  const [healthState, setHealthState] = useState<LoadState>("loading");
  const [healthError, setHealthError] = useState<string | null>(null);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [assetsState, setAssetsState] = useState<LoadState>("loading");
  const [assetsError, setAssetsError] = useState<string | null>(null);
  const [intentCount, setIntentCount] = useState<number | null>(null);
  const [policyCount, setPolicyCount] = useState<number | null>(null);
  const [events, setEvents] = useState<RealtimeEvent[]>([]);

  useEffect(() => {
    let cancelled = false;

    api
      .health()
      .then(() => !cancelled && setHealthState("ready"))
      .catch((err: unknown) => {
        if (cancelled) return;
        setHealthError(err instanceof ApiError ? err.message : "Could not reach the backend.");
        setHealthState("error");
      });

    api
      .listAssets()
      .then((data) => {
        if (cancelled) return;
        setAssets(data);
        setAssetsState("ready");
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setAssetsError(err instanceof ApiError ? err.message : "Could not reach the backend.");
        setAssetsState("error");
      });

    api
      .listIntents()
      .then((data) => !cancelled && setIntentCount(data.length))
      .catch(() => {
        /* intents are a secondary stat — the assets panel already surfaces backend errors */
      });

    api
      .listPolicies()
      .then((data) => !cancelled && setPolicyCount(data.length))
      .catch(() => {
        /* same as intents above */
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const handleRealtimeEvent = useCallback((event: RealtimeEvent) => {
    setEvents((prev) => [event, ...prev].slice(0, MAX_LOGGED_EVENTS));

    if (event.type === "telemetry.updated") {
      const telemetry = event.data;
      setAssets((prev) =>
        prev.map((asset) => (asset.id === telemetry.asset_id ? { ...asset, latest_telemetry: telemetry } : asset)),
      );
    }
  }, []);

  const wsStatus = useRealtimeEvents(handleRealtimeEvent);

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">System Overview</h1>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
            Live state from the EnerFabric backend — assets, latest telemetry, and realtime
            orchestration events.
          </p>
          <p className="mt-1 text-xs text-zinc-400 dark:text-zinc-500">
            Backend: <code className="font-mono">{API_BASE_URL}</code>
          </p>
        </div>
        <div className="flex gap-2">
          <StatusPill label={healthLabel(healthState)} tone={healthTone(healthState)} />
          <StatusPill label={wsLabel(wsStatus)} tone={wsTone(wsStatus)} />
        </div>
      </div>
      {healthState === "error" && (
        <p className="mt-2 text-sm text-red-600 dark:text-red-400">
          {healthError ?? "Could not reach the backend."} Confirm a backend is running at{" "}
          <code className="font-mono">{API_BASE_URL}</code> (start it, or set{" "}
          <code className="font-mono">NEXT_PUBLIC_API_URL</code> in{" "}
          <code className="font-mono">frontend/.env.local</code> to wherever it actually runs,
          then restart <code className="font-mono">npm run dev</code>).
        </p>
      )}

      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard label="Assets" value={assetsState === "ready" ? String(assets.length) : "—"} />
        <StatCard label="Intents" value={intentCount === null ? "—" : String(intentCount)} />
        <StatCard label="Policies" value={policyCount === null ? "—" : String(policyCount)} />
        <StatCard
          label="Realtime events"
          value={String(events.length)}
          hint={events.length > 0 ? `showing last ${Math.min(events.length, MAX_LOGGED_EVENTS)}` : undefined}
        />
      </div>

      <section className="mt-8">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
          Assets
        </h2>
        <div className="mt-3">
          {assetsState === "loading" && (
            <p className="text-sm text-zinc-500 dark:text-zinc-400">Loading assets…</p>
          )}
          {assetsState === "error" && (
            <p className="text-sm text-red-600 dark:text-red-400">
              Could not load assets from the backend
              {assetsError ? `: ${assetsError}` : "."}
            </p>
          )}
          {assetsState === "ready" && <AssetTable assets={assets} />}
        </div>
      </section>

      <section className="mt-8">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
          Recent realtime events
        </h2>
        <div className="mt-3">
          <EventLog events={events} />
        </div>
      </section>
    </div>
  );
}

function healthLabel(state: LoadState): string {
  if (state === "loading") return "Checking backend…";
  if (state === "ready") return "Backend online";
  return "Backend unreachable";
}

function healthTone(state: LoadState): PillTone {
  if (state === "ready") return "positive";
  if (state === "error") return "negative";
  return "neutral";
}

function wsLabel(status: RealtimeConnectionStatus): string {
  switch (status) {
    case "open":
      return "Realtime connected";
    case "connecting":
      return "Realtime connecting…";
    case "closed":
      return "Realtime disconnected — retrying";
    case "error":
      return "Realtime error — retrying";
  }
}

function wsTone(status: RealtimeConnectionStatus): PillTone {
  if (status === "open") return "positive";
  if (status === "connecting") return "neutral";
  return "negative";
}
