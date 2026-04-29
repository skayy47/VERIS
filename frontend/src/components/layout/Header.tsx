"use client";

import Link from "next/link";

export function Header() {
  return (
    <header
      className="px-6 py-3 flex items-center justify-between"
      style={{ borderBottom: "1px solid var(--color-border)" }}
    >
      <Link
        href="/research"
        className="font-bold text-lg tracking-wide"
        style={{ color: "var(--color-accent)" }}
      >
        VERIS
      </Link>
      <nav className="flex gap-6 text-sm" style={{ color: "var(--color-muted)" }}>
        <Link href="/research" className="hover:opacity-80 transition-opacity">
          Research
        </Link>
        <Link href="/bench" className="hover:opacity-80 transition-opacity">
          Bench
        </Link>
        <Link href="/ops" className="hover:opacity-80 transition-opacity">
          Ops
        </Link>
      </nav>
    </header>
  );
}
