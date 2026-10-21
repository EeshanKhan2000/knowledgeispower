"use client";
import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { buildMatcher, slug } from "@/lib/linkify";
import { Linked } from "./Linked";

export type Entry = {
  term: string;
  aka: string[];
  category: string;
  who: string;
  why: string;
  how: string;
  what: string;
  example: string;
  links: { label: string; url: string }[];
  related: string[];
};

const FOCUSABLE = 'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])';

export function GlossaryProvider({ entries, basePath }: { entries: Entry[] | null; basePath: string }) {
  const byId = useMemo(() => new Map((entries || []).map((e) => [e.term, e])), [entries]);
  const m = useMemo(() => buildMatcher(entries), [entries]);
  const [stack, setStack] = useState<string[]>([]);
  const [anchor, setAnchor] = useState<DOMRect | null>(null);
  const [mobile, setMobile] = useState(true);
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);
  const panel = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLElement | null>(null);
  const open = stack.length > 0;
  const current = open ? byId.get(stack[stack.length - 1]) : undefined;

  useEffect(() => {
    const mq = window.matchMedia("(min-width: 768px)");
    const upd = () => setMobile(!mq.matches);
    upd();
    mq.addEventListener("change", upd);
    return () => mq.removeEventListener("change", upd);
  }, []);

  const close = useCallback(() => {
    setStack([]);
    setPos(null);
    const t = trigger.current;
    if (t && document.contains(t)) t.focus();
  }, []);

  // Delegated handler for every [data-term] button on the page (server- or client-rendered).
  useEffect(() => {
    const onClick = (ev: MouseEvent) => {
      const el = (ev.target as HTMLElement | null)?.closest?.("[data-term]") as HTMLElement | null;
      if (!el) return;
      const id = el.getAttribute("data-term") || "";
      if (!byId.has(id)) return;
      ev.preventDefault();
      if (panel.current && panel.current.contains(el)) {
        setStack((s) => (s[s.length - 1] === id ? s : [...s, id]));
      } else {
        trigger.current = el;
        setAnchor(el.getBoundingClientRect());
        setStack([id]);
      }
    };
    document.addEventListener("click", onClick);
    return () => document.removeEventListener("click", onClick);
  }, [byId]);

  // Position the desktop popover next to the tapped term.
  useLayoutEffect(() => {
    if (!open || mobile || !panel.current) return;
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const w = panel.current.offsetWidth;
    const h = panel.current.offsetHeight;
    const a = anchor || new DOMRect(vw / 2, vh / 3, 0, 0);
    const left = Math.max(16, Math.min(a.left, vw - w - 16));
    let top = a.bottom + 8;
    if (top + h > vh - 16) top = Math.max(16, a.top - 8 - h);
    setPos({ top, left });
  }, [open, mobile, anchor, stack]);

  // Focus management + focus trap + Escape.
  useEffect(() => {
    if (!open) return;
    const p = panel.current;
    p?.querySelector<HTMLElement>("[data-autofocus]")?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        close();
        return;
      }
      if (e.key === "Tab" && p) {
        const f = Array.from(p.querySelectorAll<HTMLElement>(FOCUSABLE)).filter((x) => x.offsetParent !== null || x === document.activeElement);
        if (!f.length) return;
        const first = f[0];
        const last = f[f.length - 1];
        if (!p.contains(document.activeElement)) {
          e.preventDefault();
          first.focus();
        } else if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, stack, close]);

  if (!open || !current) return null;

  const sections: [string, string][] = [
    ["Why it matters", current.why],
    ["How it works", current.how],
    ["What it is", current.what],
    ["Example", current.example],
    ["Who", current.who],
  ];
  const related = current.related.filter((r) => byId.has(r) && r !== current.term);
  const titleId = "gl-title-" + slug(current.term);

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/30 md:bg-black/10" onClick={close} aria-hidden="true" />
      <div
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        data-glossary-sheet
        className={
          mobile
            ? "fixed inset-x-0 bottom-0 z-50 max-h-[80vh] overflow-y-auto rounded-t-2xl border-t border-line bg-surface p-4 pb-8 shadow-2xl"
            : "fixed z-50 max-h-[70vh] w-[400px] overflow-y-auto rounded-xl border border-line bg-surface p-4 shadow-2xl"
        }
        style={!mobile ? { top: pos?.top ?? -9999, left: pos?.left ?? -9999 } : undefined}
      >
        {mobile && <div className="mx-auto mb-3 h-1 w-10 rounded-full bg-line" aria-hidden="true" />}
        <div className="flex items-center gap-2">
          {stack.length > 1 && (
            <button type="button" className="btn-ghost" onClick={() => setStack((s) => s.slice(0, -1))} aria-label="Back to previous term">
              ← Back
            </button>
          )}
          <span className="ml-auto" />
          <button type="button" className="btn-ghost" onClick={close} aria-label="Close glossary" data-autofocus>
            Close ✕
          </button>
        </div>
        <h2 id={titleId} className="mt-2 text-lg font-semibold text-ink">
          {current.term}
        </h2>
        <p className="text-xs text-muted">
          {current.category}
          {current.aka.length > 0 && <> · also: {current.aka.join(", ")}</>}
        </p>
        <dl className="mt-3 space-y-3 text-sm">
          {sections
            .filter(([, v]) => v)
            .map(([k, v]) => (
              <div key={k}>
                <dt className="text-xs font-semibold uppercase tracking-wide text-muted">{k}</dt>
                <dd className="mt-0.5 text-ink2">
                  <Linked text={v} m={m} exclude={current.term} />
                </dd>
              </div>
            ))}
        </dl>
        {current.links.length > 0 && (
          <div className="mt-3 text-sm">
            <div className="text-xs font-semibold uppercase tracking-wide text-muted">Links</div>
            <ul className="mt-1 space-y-1">
              {current.links.map((l) => (
                <li key={l.url}>
                  <a className="link break-words" href={l.url} target="_blank" rel="noreferrer noopener">
                    {l.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}
        {related.length > 0 && (
          <div className="mt-3 text-sm">
            <div className="text-xs font-semibold uppercase tracking-wide text-muted">Related</div>
            <div className="mt-1 flex flex-wrap gap-2">
              {related.map((r) => (
                <button key={r} type="button" className="chip" data-term={r}>
                  {r}
                </button>
              ))}
            </div>
          </div>
        )}
        <a className="link mt-4 inline-block text-xs" href={`${basePath}/glossary/#${slug(current.term)}`} onClick={() => setStack([])}>
          Open in glossary page
        </a>
      </div>
    </>
  );
}
