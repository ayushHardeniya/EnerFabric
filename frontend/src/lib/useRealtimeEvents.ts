"use client";

/**
 * A small, reusable client for the backend's realtime WebSocket
 * endpoint (GET /api/v1/ws, Milestone 6). Connects, parses the
 * existing event envelope, and hands each event to the caller.
 *
 * Reconnects with capped exponential backoff on any close/error so a
 * backend restart or a temporarily unavailable backend doesn't require
 * a page reload, and fails gracefully (status stays "closed"/"error"
 * instead of throwing) when the backend is unreachable entirely.
 */

import { useEffect, useRef, useState } from "react";
import { getWebSocketUrl } from "./config";
import type { RealtimeEvent } from "@/types/events";

export type RealtimeConnectionStatus = "connecting" | "open" | "closed" | "error";

const INITIAL_RETRY_DELAY_MS = 1000;
const MAX_RETRY_DELAY_MS = 15000;

export function useRealtimeEvents(onEvent: (event: RealtimeEvent) => void) {
  const [status, setStatus] = useState<RealtimeConnectionStatus>("connecting");
  const onEventRef = useRef(onEvent);

  useEffect(() => {
    onEventRef.current = onEvent;
  }, [onEvent]);

  useEffect(() => {
    let cancelled = false;
    let socket: WebSocket | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let retryDelay = INITIAL_RETRY_DELAY_MS;

    function connect() {
      if (cancelled) return;
      setStatus("connecting");

      try {
        socket = new WebSocket(getWebSocketUrl());
      } catch {
        setStatus("error");
        scheduleRetry();
        return;
      }

      socket.onopen = () => {
        retryDelay = INITIAL_RETRY_DELAY_MS;
        setStatus("open");
      };

      socket.onmessage = (message: MessageEvent<string>) => {
        try {
          const event = JSON.parse(message.data) as RealtimeEvent;
          onEventRef.current(event);
        } catch {
          // Not a well-formed event envelope — ignore this frame.
        }
      };

      socket.onerror = () => {
        setStatus("error");
      };

      socket.onclose = () => {
        if (cancelled) return;
        setStatus("closed");
        scheduleRetry();
      };
    }

    function scheduleRetry() {
      if (cancelled) return;
      retryTimer = setTimeout(connect, retryDelay);
      retryDelay = Math.min(retryDelay * 2, MAX_RETRY_DELAY_MS);
    }

    connect();

    return () => {
      cancelled = true;
      if (retryTimer) clearTimeout(retryTimer);
      socket?.close();
    };
  }, []);

  return status;
}
