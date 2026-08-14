"use client";

/** Site-wide header/nav shell. */

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/", label: "Overview" },
  { href: "/assets", label: "Assets" },
  { href: "/intents-policies", label: "Intents & Policies" },
  { href: "/coordination", label: "Coordination" },
  { href: "/impact", label: "Impact" },
];

export function Header() {
  const pathname = usePathname();

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
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={
                  active
                    ? "font-medium text-foreground"
                    : "text-zinc-500 hover:text-foreground dark:text-zinc-400"
                }
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
