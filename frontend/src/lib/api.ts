/**
 * A small typed client around the existing backend REST endpoints
 * (backend/app/api/routes/). Deliberately not a generated SDK — one
 * function per endpoint this frontend actually uses, all sharing one
 * fetch wrapper. No business logic lives here: it only shapes HTTP
 * calls and parses JSON into the existing backend contract's types.
 */

import { API_BASE_URL, API_V1_PREFIX } from "./config";
import type { Asset, HealthResponse, IntentSummary, Policy } from "@/types/domain";

const RESOURCE_BASE = `${API_BASE_URL}${API_V1_PREFIX}`;

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function get<T>(url: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(url);
  } catch {
    // fetch() rejects (rather than resolving with a non-ok status) for
    // network-level failures — no server listening at this URL, DNS
    // failure, or a CORS-blocked response. Naming the URL here is what
    // makes a misconfigured/wrong-port NEXT_PUBLIC_API_URL diagnosable
    // from the rendered error instead of a generic "unreachable".
    throw new ApiError(0, `could not reach ${url} — is a backend actually running there?`);
  }
  if (!response.ok) {
    const body = await response.text().catch(() => "");
    throw new ApiError(response.status, body || `request to ${url} failed with ${response.status}`);
  }
  return (await response.json()) as T;
}

export const api = {
  health: () => get<HealthResponse>(`${API_BASE_URL}/health`),
  listAssets: () => get<Asset[]>(`${RESOURCE_BASE}/assets`),
  listIntents: () => get<IntentSummary[]>(`${RESOURCE_BASE}/intents`),
  listPolicies: () => get<Policy[]>(`${RESOURCE_BASE}/policies`),
};
