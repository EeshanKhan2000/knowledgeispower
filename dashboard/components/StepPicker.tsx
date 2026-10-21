"use client";
import React, { useState } from "react";

export type Step = { id: string; title: string; short: string; body: React.ReactNode };

export function StepPicker({ steps }: { steps: Step[] }) {
  const [sel, setSel] = useState(0);
  const cur = steps[sel];
  return (
    <div>
      <ol className="flex flex-col gap-1 md:flex-row md:flex-wrap md:items-center" role="tablist" aria-label="Pipeline steps">
        {steps.map((s, i) => (
          <li key={s.id} className="flex flex-col md:flex-row md:items-center">
            <button
              type="button"
              role="tab"
              id={`tab-${s.id}`}
              aria-selected={i === sel}
              aria-controls="step-panel"
              onClick={() => setSel(i)}
              onKeyDown={(e) => {
                if (e.key === "ArrowRight" || e.key === "ArrowDown") {
                  e.preventDefault();
                  const n = (i + 1) % steps.length;
                  setSel(n);
                  document.getElementById(`tab-${steps[n].id}`)?.focus();
                } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
                  e.preventDefault();
                  const n = (i - 1 + steps.length) % steps.length;
                  setSel(n);
                  document.getElementById(`tab-${steps[n].id}`)?.focus();
                }
              }}
              tabIndex={i === sel ? 0 : -1}
              className={
                "w-full rounded-xl border px-3 py-2 text-left text-sm transition focus:outline-none focus-visible:ring-2 focus-visible:ring-accent md:w-auto " +
                (i === sel ? "border-accent bg-surface font-semibold text-ink shadow" : "border-line bg-surface2 text-ink2 hover:bg-surface")
              }
            >
              <span className="mr-2 inline-flex h-5 w-5 items-center justify-center rounded-full bg-accent text-[11px] font-bold text-white">
                {i + 1}
              </span>
              {s.title}
              <span className="block text-xs font-normal text-muted md:hidden">{s.short}</span>
            </button>
            {i < steps.length - 1 && (
              <span aria-hidden="true" className="self-center px-1 text-muted">
                <span className="md:hidden">↓</span>
                <span className="hidden md:inline">→</span>
              </span>
            )}
          </li>
        ))}
      </ol>
      <div id="step-panel" role="tabpanel" aria-labelledby={`tab-${cur.id}`} className="card mt-4">
        <h2 className="text-lg font-semibold text-ink">
          Step {sel + 1}: {cur.title}
        </h2>
        <p className="text-xs text-muted">{cur.short}</p>
        <div className="mt-2">{cur.body}</div>
        <div className="mt-4 flex justify-between gap-2">
          <button type="button" className="btn-ghost" disabled={sel === 0} onClick={() => setSel(sel - 1)}>
            ← Previous
          </button>
          <button type="button" className="btn-ghost" disabled={sel === steps.length - 1} onClick={() => setSel(sel + 1)}>
            Next →
          </button>
        </div>
      </div>
    </div>
  );
}
