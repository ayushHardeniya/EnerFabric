import { formatTimestamp } from "@/lib/format";
import type { RealtimeEvent } from "@/types/events";

function describeEvent(event: RealtimeEvent): string {
  if (event.type === "telemetry.updated") {
    return `${event.data.asset_id} reported ${event.data.power_kw.toFixed(1)} kW`;
  }
  return `run ${event.data.id.slice(0, 8)} completed (${event.data.trigger_reason}, ${event.data.allocations.length} allocation${event.data.allocations.length === 1 ? "" : "s"})`;
}

export function EventLog({ events }: { events: RealtimeEvent[] }) {
  if (events.length === 0) {
    return (
      <p className="text-sm text-zinc-500 dark:text-zinc-400">
        No realtime events yet. Waiting for MQTT telemetry or a coordination run to be broadcast
        over the WebSocket.
      </p>
    );
  }

  return (
    <ul className="divide-y divide-black/5 rounded-lg border border-black/10 text-sm dark:divide-white/5 dark:border-white/10">
      {events.map((event, index) => (
        <li key={`${event.timestamp}-${index}`} className="flex items-center justify-between gap-3 px-4 py-2">
          <span>
            <span className="font-medium">{event.type}</span>{" "}
            <span className="text-zinc-500 dark:text-zinc-400">— {describeEvent(event)}</span>
          </span>
          <span className="shrink-0 text-xs text-zinc-400 dark:text-zinc-500">
            {formatTimestamp(event.timestamp)}
          </span>
        </li>
      ))}
    </ul>
  );
}
