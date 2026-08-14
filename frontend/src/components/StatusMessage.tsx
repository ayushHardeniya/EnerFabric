import type { ReactNode } from "react";

export function StatusMessage({
  tone = "muted",
  children,
}: {
  tone?: "muted" | "error";
  children: ReactNode;
}) {
  const cls = tone === "error" ? "text-red-600 dark:text-red-400" : "text-zinc-500 dark:text-zinc-400";
  return <p className={`text-sm ${cls}`}>{children}</p>;
}
