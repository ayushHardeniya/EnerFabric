export type PillTone = "neutral" | "positive" | "negative";

const TONE_CLASSES: Record<PillTone, string> = {
  neutral: "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300",
  positive: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400",
  negative: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-400",
};

export function StatusPill({ label, tone }: { label: string; tone: PillTone }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${TONE_CLASSES[tone]}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {label}
    </span>
  );
}
