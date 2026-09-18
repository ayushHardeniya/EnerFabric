/**
 * Mirrors the WebSocket event envelope from backend/app/realtime/events.py:
 * { "type": "...", "timestamp": "...", "data": { ... } }
 */

import type { CoordinationRun, Telemetry } from "./domain";

export interface TelemetryUpdatedEvent {
  type: "telemetry.updated";
  timestamp: string;
  data: Telemetry;
}

export interface CoordinationCompletedEvent {
  type: "coordination.completed";
  timestamp: string;
  data: CoordinationRun;
}

export type RealtimeEvent = TelemetryUpdatedEvent | CoordinationCompletedEvent;
