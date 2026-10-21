import React from "react";
import { linkSegments, type Matcher } from "@/lib/linkify";

/** Renders text with glossary terms as tappable buttons. No hooks: works in server and client components. */
export function Linked({ text, m, seen, exclude }: { text: string; m: Matcher; seen?: Set<string>; exclude?: string }) {
  const segs = linkSegments(text, m, seen ?? new Set(), exclude);
  return (
    <>
      {segs.map((s, i) =>
        s.id ? (
          <button key={i} type="button" className="term" data-term={s.id}>
            {s.text}
          </button>
        ) : (
          <React.Fragment key={i}>{s.text}</React.Fragment>
        ),
      )}
    </>
  );
}
