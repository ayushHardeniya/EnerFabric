/**
 * Site-wide header/nav shell. Only "Overview" is a real, implemented
 * page in Milestone 7 — the rest are plain (non-navigable) labels that
 * establish where Milestone 8's dashboard sections will land, so the
 * nav's final shape doesn't need to be re-built from scratch later.
 */

const FUTURE_SECTIONS = ["Assets", "Intents & Policies", "Coordination", "Impact"];

export function Header() {
  return (
    <header className="border-b border-black/10 dark:border-white/10">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-4">
        <div>
          <p className="text-lg font-semibold tracking-tight">EnerFabric</p>
          <p className="text-xs text-zinc-500 dark:text-zinc-400">
            Intent-driven DER orchestration
          </p>
        </div>
        <nav className="hidden items-center gap-5 text-sm sm:flex">
          <span className="font-medium text-foreground">Overview</span>
          {FUTURE_SECTIONS.map((section) => (
            <span
              key={section}
              className="text-zinc-400 dark:text-zinc-600"
              title="Coming in Milestone 8"
            >
              {section}
            </span>
          ))}
        </nav>
      </div>
    </header>
  );
}
