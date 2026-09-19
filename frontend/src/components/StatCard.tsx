import Link from "next/link";

function CardContent({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <>
      <p className="text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
        {label}
      </p>
      <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
      {hint ? <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">{hint}</p> : null}
    </>
  );
}

export function StatCard({
  label,
  value,
  hint,
  href,
}: {
  label: string;
  value: string;
  hint?: string;
  href?: string;
}) {
  const className =
    "block rounded-lg border border-black/10 px-4 py-3 dark:border-white/10" +
    (href ? " transition-colors hover:border-black/20 dark:hover:border-white/20" : "");

  if (href) {
    return (
      <Link href={href} className={className}>
        <CardContent label={label} value={value} hint={hint} />
      </Link>
    );
  }

  return (
    <div className={className}>
      <CardContent label={label} value={value} hint={hint} />
    </div>
  );
}
