/**
 * Backend connection config. A single place that reads
 * NEXT_PUBLIC_API_URL, so no component or util hardcodes a backend
 * host — see README.md for the local default.
 */

const DEFAULT_API_URL = "http://localhost:8000";

export const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL ?? DEFAULT_API_URL).replace(
  /\/+$/,
  "",
);

export const API_V1_PREFIX = "/api/v1";

/** Derives the WebSocket URL from API_BASE_URL (http->ws, https->wss). */
export function getWebSocketUrl(): string {
  if (API_BASE_URL === "") {
    // Same-origin deployment (e.g. behind a reverse proxy that routes
    // /api/* to the backend on the same public host/port) — derive
    // protocol/host from the page itself rather than a configured URL.
    const wsProtocol = window.location.protocol === "https:" ? "wss://" : "ws://";
    return `${wsProtocol}${window.location.host}${API_V1_PREFIX}/ws`;
  }
  const wsProtocol = API_BASE_URL.startsWith("https://") ? "wss://" : "ws://";
  const host = API_BASE_URL.replace(/^https?:\/\//, "");
  return `${wsProtocol}${host}${API_V1_PREFIX}/ws`;
}
