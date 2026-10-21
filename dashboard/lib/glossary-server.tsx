// Server-side glossary helpers: load once at build time, expose a matcher and prose components.
import React from "react";
import { loadGlossary } from "./data";
import { buildMatcher } from "./linkify";
import { Linked } from "@/components/Linked";

export const glossary = loadGlossary();
export const matcher = buildMatcher(glossary.entries);

function linkChildren(children: React.ReactNode, seen: Set<string>): React.ReactNode {
  return React.Children.map(children, (c) => (typeof c === "string" ? <Linked text={c} m={matcher} seen={seen} /> : c));
}

/** Paragraph whose plain-string children get glossary links (first occurrence per paragraph). */
export function P({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <p className={"prose-p " + className}>{linkChildren(children, new Set())}</p>;
}

/** Inline span with glossary links (e.g. list items, table explanations). */
export function L({ children }: { children: React.ReactNode }) {
  return <>{linkChildren(children, new Set())}</>;
}
