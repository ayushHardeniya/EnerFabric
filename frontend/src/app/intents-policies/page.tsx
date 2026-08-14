"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/Button";
import { PageHeader } from "@/components/PageHeader";
import { StatusMessage } from "@/components/StatusMessage";
import { StatusPill } from "@/components/StatusPill";
import { api, ApiError } from "@/lib/api";
import { describeIntent, humanizeSnakeCase, formatPolicyThreshold, formatPriority } from "@/lib/format";
import { useAssets } from "@/lib/useAssets";
import type { Intent, Policy } from "@/types/domain";

type LoadState = "loading" | "ready" | "error";

export default function IntentsPoliciesPage() {
  const { assets } = useAssets();
  const assetNameById = new Map(assets.map((asset) => [asset.id, asset.name]));

  const [intents, setIntents] = useState<Intent[]>([]);
  const [intentsState, setIntentsState] = useState<LoadState>("loading");
  const [intentsError, setIntentsError] = useState<string | null>(null);

  const [policies, setPolicies] = useState<Policy[]>([]);
  const [policiesState, setPoliciesState] = useState<LoadState>("loading");
  const [policiesError, setPoliciesError] = useState<string | null>(null);

  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let cancelled = false;

    api
      .listIntents()
      .then((data) => {
        if (cancelled) return;
        setIntents(data);
        setIntentsState("ready");
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setIntentsError(err instanceof ApiError ? err.message : "Could not reach the backend.");
        setIntentsState("error");
      });

    api
      .listPolicies()
      .then((data) => {
        if (cancelled) return;
        setPolicies(data);
        setPoliciesState("ready");
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setPoliciesError(err instanceof ApiError ? err.message : "Could not reach the backend.");
        setPoliciesState("error");
      });

    return () => {
      cancelled = true;
    };
  }, [reloadToken]);

  const reload = () => {
    setIntentsState("loading");
    setPoliciesState("loading");
    setReloadToken((t) => t + 1);
  };

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <PageHeader
        title="Intents & Policies"
        description="What each asset needs or prefers (intent), and the system-wide rules EnerFabric must honor (policy)."
        actions={
          <Button
            variant="secondary"
            onClick={reload}
            disabled={intentsState === "loading" || policiesState === "loading"}
          >
            Refresh
          </Button>
        }
      />

      <section className="mt-8">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
          Intents
        </h2>
        <div className="mt-3">
          {intentsState === "loading" && <StatusMessage>Loading intents…</StatusMessage>}
          {intentsState === "error" && (
            <StatusMessage tone="error">
              Could not load intents from the backend{intentsError ? `: ${intentsError}` : "."}
            </StatusMessage>
          )}
          {intentsState === "ready" && intents.length === 0 && (
            <StatusMessage>
              No intents configured yet. Create one via{" "}
              <code className="font-mono">POST /api/v1/intents</code>.
            </StatusMessage>
          )}
          {intentsState === "ready" && intents.length > 0 && (
            <div className="overflow-x-auto rounded-lg border border-black/10 dark:border-white/10">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead className="border-b border-black/10 text-xs uppercase tracking-wide text-zinc-500 dark:border-white/10 dark:text-zinc-400">
                  <tr>
                    <th className="px-4 py-2 font-medium">Asset</th>
                    <th className="px-4 py-2 font-medium">Wants</th>
                    <th className="px-4 py-2 font-medium">Priority</th>
                    <th className="px-4 py-2 font-medium">Description</th>
                  </tr>
                </thead>
                <tbody>
                  {intents.map((intent) => (
                    <tr key={intent.id} className="border-b border-black/5 last:border-0 dark:border-white/5">
                      <td className="px-4 py-2 font-medium">
                        {assetNameById.get(intent.asset_id) ?? intent.asset_id}
                      </td>
                      <td className="px-4 py-2 text-zinc-600 dark:text-zinc-300">
                        {describeIntent(intent)}
                      </td>
                      <td className="px-4 py-2">
                        <StatusPill label={formatPriority(intent.priority)} tone="neutral" />
                      </td>
                      <td className="px-4 py-2 text-zinc-500 dark:text-zinc-400">
                        {intent.description}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>

      <section className="mt-8">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
          Policies
        </h2>
        <div className="mt-3">
          {policiesState === "loading" && <StatusMessage>Loading policies…</StatusMessage>}
          {policiesState === "error" && (
            <StatusMessage tone="error">
              Could not load policies from the backend{policiesError ? `: ${policiesError}` : "."}
            </StatusMessage>
          )}
          {policiesState === "ready" && policies.length === 0 && (
            <StatusMessage>
              No policies configured yet. Create one via{" "}
              <code className="font-mono">POST /api/v1/policies</code>.
            </StatusMessage>
          )}
          {policiesState === "ready" && policies.length > 0 && (
            <div className="overflow-x-auto rounded-lg border border-black/10 dark:border-white/10">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead className="border-b border-black/10 text-xs uppercase tracking-wide text-zinc-500 dark:border-white/10 dark:text-zinc-400">
                  <tr>
                    <th className="px-4 py-2 font-medium">Policy</th>
                    <th className="px-4 py-2 font-medium">Threshold</th>
                    <th className="px-4 py-2 font-medium">Priority</th>
                    <th className="px-4 py-2 font-medium">State</th>
                    <th className="px-4 py-2 font-medium">Description</th>
                  </tr>
                </thead>
                <tbody>
                  {policies.map((policy) => (
                    <tr key={policy.id} className="border-b border-black/5 last:border-0 dark:border-white/5">
                      <td className="px-4 py-2 font-medium capitalize">
                        {humanizeSnakeCase(policy.type)}
                      </td>
                      <td className="px-4 py-2 tabular-nums text-zinc-600 dark:text-zinc-300">
                        {formatPolicyThreshold(policy)}
                      </td>
                      <td className="px-4 py-2">
                        <StatusPill label={formatPriority(policy.priority)} tone="neutral" />
                      </td>
                      <td className="px-4 py-2">
                        <StatusPill
                          label={policy.enabled ? "enabled" : "disabled"}
                          tone={policy.enabled ? "positive" : "neutral"}
                        />
                      </td>
                      <td className="px-4 py-2 text-zinc-500 dark:text-zinc-400">
                        {policy.description}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
