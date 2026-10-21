"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

const ITEMS = [
  { href: "/", label: "Overview" },
  { href: "/mechanism/", label: "Mechanism" },
  { href: "/pipeline/", label: "Pipeline" },
  { href: "/results/", label: "Results" },
  { href: "/prior-art/", label: "Prior art" },
  { href: "/agent-demo/", label: "Agent demo" },
  { href: "/glossary/", label: "Glossary" },
];

export function Nav() {
  const path = usePathname() || "/";
  const [open, setOpen] = useState(false);
  useEffect(() => setOpen(false), [path]);
  const norm = (p: string) => (p.endsWith("/") ? p : p + "/");
  const active = (h: string) => (h === "/" ? norm(path) === "/" : norm(path).startsWith(h));
  return (
    <nav aria-label="Main" className="relative">
      <button
        type="button"
        className="btn-ghost md:hidden"
        aria-expanded={open}
        aria-controls="main-menu"
        onClick={() => setOpen((o) => !o)}
      >
        {open ? "Close ✕" : "Menu ☰"}
      </button>
      <ul
        id="main-menu"
        className={
          (open ? "flex" : "hidden") +
          " absolute right-0 top-full z-30 mt-2 w-56 flex-col rounded-xl border border-line bg-surface p-2 shadow-xl md:static md:mt-0 md:flex md:w-auto md:flex-row md:flex-wrap md:gap-1 md:border-0 md:bg-transparent md:p-0 md:shadow-none"
        }
      >
        {ITEMS.map((it) => (
          <li key={it.href}>
            <Link
              href={it.href}
              aria-current={active(it.href) ? "page" : undefined}
              className={
                "block rounded-lg px-3 py-2 text-sm md:py-1.5 " +
                (active(it.href) ? "bg-surface2 font-semibold text-ink" : "text-ink2 hover:bg-surface2")
              }
            >
              {it.label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
