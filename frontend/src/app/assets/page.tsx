"use client";

import { useCallback } from "react";
import { AssetTable } from "@/components/AssetTable";
import { Button } from "@/components/Button";
import { PageHeader } from "@/components/PageHeader";
import { StatusMessage } from "@/components/StatusMessage";
import { useAssets } from "@/lib/useAssets";
import { useRealtimeEvents } from "@/lib/useRealtimeEvents";
import type { RealtimeEvent } from "@/types/events";

export default function AssetsPage() {
  const { assets, setAssets, state, error, reload } = useAssets();

  const handleRealtimeEvent = useCallback(
    (event: RealtimeEvent) => {
      if (event.type !== "telemetry.updated") return;
      const telemetry = event.data;
      setAssets((prev) =>
        prev.map((asset) => (asset.id === telemetry.asset_id ? { ...asset, latest_telemetry: telemetry } : asset)),
      );
    },
    [setAssets],
  );

  useRealtimeEvents(handleRealtimeEvent);

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <PageHeader
        title="Assets"
        description="Every registered DER asset, its capabilities, and its most recent telemetry. Updates live as new readings arrive over MQTT/WebSocket."
        actions={
          <Button variant="secondary" onClick={reload} disabled={state === "loading"}>
            Refresh
          </Button>
        }
      />

      <div className="mt-6">
        {state === "loading" && <StatusMessage>Loading assets…</StatusMessage>}
        {state === "error" && (
          <StatusMessage tone="error">
            Could not load assets from the backend{error ? `: ${error}` : "."}
          </StatusMessage>
        )}
        {state === "ready" && <AssetTable assets={assets} detailed />}
      </div>
    </div>
  );
}
