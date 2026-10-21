import React from "react";
import { runMeta, resultsDirLabel, type Loaded } from "@/lib/data";

export function NotAvailable({ what, file, reason }: { what: string; file: string; reason?: string }) {
  return (
    <div role="status" className="my-3 rounded-xl border border-dashed border-line bg-neutralbg p-4 text-sm text-ink2">
      <strong className="text-ink">{what}: not available yet.</strong>{" "}
      <span className="break-words">
        Expected <code className="font-mono">{file}</code>
        {reason ? ` (${reason})` : ""}.
      </span>
    </div>
  );
}

/** Render children with loaded data, or a visible "not available yet" notice. */
export function WithData<T>({ r, what, children }: { r: Loaded<T>; what: string; children: (d: T) => React.ReactNode }) {
  if (!r.ok) return <NotAvailable what={what} file={r.file} reason={r.reason} />;
  return <>{children(r.data)}</>;
}

export function Provenance({ files }: { files?: string[] }) {
  const meta = runMeta();
  const dir = resultsDirLabel();
  return (
    <p className="mt-2 break-words rounded-lg bg-surface2 px-3 py-2 font-mono text-[11px] leading-relaxed text-muted">
      source: {dir}/{files && files.length ? `{${files.join(", ")}}` : ""} ·{" "}
      {meta.ok ? (
        <>
          code_commit {String(meta.data.code_commit ?? "?").slice(0, 12)} · quick {String(meta.data.quick ?? "?")} · runtime{" "}
          {typeof meta.data.runtime_seconds === "number" ? `${meta.data.runtime_seconds}s` : "?"}
        </>
      ) : (
        <>run_meta.json not available yet</>
      )}
    </p>
  );
}

export function Verdict({ kind, children }: { kind: "good" | "bad" | "neutral"; children: React.ReactNode }) {
  const icon = kind === "good" ? "✓" : kind === "bad" ? "✗" : "○";
  return (
    <span className={`badge badge-${kind}`}>
      <span aria-hidden="true">{icon}</span>
      {children}
    </span>
  );
}

export function Section({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} className="scroll-mt-20">
      <h2 className="h2">{title}</h2>
      {children}
    </section>
  );
}
