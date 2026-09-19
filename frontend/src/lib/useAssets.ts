"use client";

/**
 * Shared "fetch the asset list" hook — every M8 page that needs assets
 * (Overview, Assets, Coordination, Intents & Policies for asset-name
 * lookups) had the same fetch/loading/error boilerplate; this
 * centralizes it. Realtime patching (telemetry.updated) stays with
 * each page's own useRealtimeEvents call via the returned `setAssets`,
 * rather than being baked in here, so this hook doesn't also have to
 * own a WebSocket connection.
 */

import { useEffect, useState } from "react";
import { api, ApiError } from "./api";
import type { Asset } from "@/types/domain";

export type LoadState = "loading" | "ready" | "error";

export function useAssets() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [state, setState] = useState<LoadState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let cancelled = false;
    api
      .listAssets()
      .then((data) => {
        if (cancelled) return;
        setAssets(data);
        setState("ready");
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.message : "Could not reach the backend.");
        setState("error");
      });
    return () => {
      cancelled = true;
    };
  }, [reloadToken]);

  const reload = () => {
    setState("loading");
    setReloadToken((token) => token + 1);
  };

  return { assets, setAssets, state, error, reload };
}
