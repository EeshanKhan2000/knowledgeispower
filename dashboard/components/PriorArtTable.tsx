"use client";
import React, { useMemo, useState } from "react";

export type PaRow = {
  id: string;
  title: string;
  authors: string;
  venue: string;
  year: string;
  url: string;
  cls: string;
  verified: boolean | null;
  unverified_note: string;
  differentiation: React.ReactNode;
  what: React.ReactNode;
  search: string;
};

export function PriorArtTable({ rows, classes }: { rows: PaRow[]; classes: string[] }) {
  const [cls, setCls] = useState<string>("all");
  const [q, setQ] = useState("");
  const shown = useMemo(() => {
    const t = q.trim().toLowerCase();
    return rows.filter((r) => (cls === "all" || r.cls === cls) && (!t || r.search.includes(t)));
  }, [rows, cls, q]);
  return (
    <div>
      <div className="flex flex-col gap-3 md:flex-row md:items-end">
        <label className="flex-1 text-sm text-ink2">
          Search
          <input
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="title, author, venue, text…"
            className="mt-1 block w-full rounded-lg border border-line bg-surface px-3 py-2 text-ink placeholder:text-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          />
        </label>
        <div className="text-sm text-ink2" role="group" aria-label="Filter by class">
          <div>Class</div>
          <div className="mt-1 flex flex-wrap gap-1.5">
            {["all", ...classes].map((c) => (
              <button
                key={c}
                type="button"
                aria-pressed={cls === c}
                onClick={() => setCls(c)}
                className={"chip " + (cls === c ? "border-accent bg-accent text-white" : "")}
              >
                {c} ({c === "all" ? rows.length : rows.filter((r) => r.cls === c).length})
              </button>
            ))}
          </div>
        </div>
      </div>
      <p className="mt-3 text-xs text-muted" aria-live="polite">
        Showing {shown.length} of {rows.length}.
      </p>
      <ul className="mt-2 space-y-3">
        {shown.map((r) => (
          <li key={r.id} className="card">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <span className="chip !py-0.5 text-xs">{r.cls}</span>
              {r.verified === true ? (
                <span className="badge badge-good">✓ verified</span>
              ) : (
                <span className="badge badge-bad">✗ not verified</span>
              )}
            </div>
            <h3 className="mt-2 font-semibold text-ink">
              {r.url ? (
                <a href={r.url} className="link break-words" target="_blank" rel="noreferrer noopener">
                  {r.title}
                </a>
              ) : (
                r.title
              )}
            </h3>
            <p className="mt-1 text-sm text-ink2">{r.authors}</p>
            <p className="text-xs text-muted">
              {r.venue}
              {r.venue && r.year ? " · " : ""}
              {r.year}
            </p>
            <div className="mt-2 text-sm text-ink2">
              <span className="font-semibold text-ink">How we differ: </span>
              {r.differentiation}
            </div>
            {r.unverified_note && (
              <p className="mt-2 rounded-lg bg-badbg px-3 py-2 text-xs text-bad">Unverified note: {r.unverified_note}</p>
            )}
            <details className="mt-2 text-sm">
              <summary className="cursor-pointer text-muted">What it does</summary>
              <div className="mt-1 text-ink2">{r.what}</div>
            </details>
          </li>
        ))}
      </ul>
    </div>
  );
}
