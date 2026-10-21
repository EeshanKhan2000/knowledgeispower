// Build-time data access. Everything shown about results is read here, from files, with fs.
// This module is only imported by server components, so it runs at `next build` time.
import fs from "node:fs";
import path from "node:path";

const ROOT = process.cwd();

export const RESULTS_DIR = path.resolve(ROOT, process.env.RESULTS_DIR || "../results");
export const REPO_DIR = path.resolve(ROOT, "..");
export const GLOSSARY_FILE = path.resolve(ROOT, process.env.GLOSSARY_FILE || "../docs/glossary.json");

export type Loaded<T> =
  | { ok: true; data: T; file: string }
  | { ok: false; file: string; reason: string };

export function rel(p: string): string {
  return path.relative(REPO_DIR, p) || p;
}

function readText(file: string): Loaded<string> {
  try {
    if (!fs.existsSync(file)) return { ok: false, file: rel(file), reason: "file not found" };
    return { ok: true, data: fs.readFileSync(file, "utf8"), file: rel(file) };
  } catch (e) {
    return { ok: false, file: rel(file), reason: String(e) };
  }
}

function readJson<T>(file: string): Loaded<T> {
  const t = readText(file);
  if (!t.ok) return t;
  try {
    return { ok: true, data: JSON.parse(t.data) as T, file: t.file };
  } catch (e) {
    return { ok: false, file: t.file, reason: "invalid JSON: " + String((e as Error).message) };
  }
}

export const resultJson = <T = any>(name: string) => readJson<T>(path.join(RESULTS_DIR, name));
export const repoText = (p: string) => readText(path.join(REPO_DIR, p));
export const repoJson = <T = any>(p: string) => readJson<T>(path.join(REPO_DIR, p));

// ---------- CSV ----------
export function parseCsv(text: string): Record<string, string>[] {
  const rows: string[][] = [];
  let row: string[] = [];
  let cur = "";
  let q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) {
      if (c === '"') {
        if (text[i + 1] === '"') { cur += '"'; i++; } else q = false;
      } else cur += c;
    } else if (c === '"') q = true;
    else if (c === ",") { row.push(cur); cur = ""; }
    else if (c === "\n" || c === "\r") {
      if (c === "\r" && text[i + 1] === "\n") i++;
      row.push(cur); cur = "";
      if (row.some((x) => x !== "")) rows.push(row);
      row = [];
    } else cur += c;
  }
  if (cur !== "" || row.length) { row.push(cur); if (row.some((x) => x !== "")) rows.push(row); }
  if (!rows.length) return [];
  const [head, ...body] = rows;
  return body.map((r) => Object.fromEntries(head.map((h, i) => [h, r[i] ?? ""])));
}

export function resultCsv(name: string): Loaded<Record<string, string>[]> {
  const t = readText(path.join(RESULTS_DIR, name));
  if (!t.ok) return t;
  try {
    return { ok: true, data: parseCsv(t.data), file: t.file };
  } catch (e) {
    return { ok: false, file: t.file, reason: String(e) };
  }
}

// ---------- run meta / provenance ----------
export type RunMeta = {
  code_commit?: string;
  quick?: boolean;
  runtime_seconds?: number;
  [k: string]: unknown;
};

export function runMeta(): Loaded<RunMeta> {
  return resultJson<RunMeta>("run_meta.json");
}

export function resultsDirLabel(): string {
  return rel(RESULTS_DIR);
}

// ---------- glossary ----------
export type GlossaryLink = { label: string; url: string };
export type GlossaryEntry = {
  term: string;
  aka: string[];
  category: string;
  who: string;
  why: string;
  how: string;
  what: string;
  example: string;
  links: GlossaryLink[];
  related: string[];
};

const str = (v: unknown) => (typeof v === "string" ? v : "");

export function loadGlossary(): { entries: GlossaryEntry[] | null; file: string; reason?: string } {
  const r = readJson<unknown>(GLOSSARY_FILE);
  if (!r.ok) return { entries: null, file: r.file, reason: r.reason };
  let list: unknown = r.data;
  if (list && !Array.isArray(list) && typeof list === "object") {
    const o = list as Record<string, unknown>;
    list = Array.isArray(o.terms) ? o.terms : Array.isArray(o.entries) ? o.entries : null;
  }
  if (!Array.isArray(list)) return { entries: null, file: r.file, reason: "unexpected structure (expected a list of terms)" };
  const entries: GlossaryEntry[] = [];
  for (const x of list) {
    if (!x || typeof x !== "object") continue;
    const o = x as Record<string, unknown>;
    if (!str(o.term).trim()) continue;
    entries.push({
      term: str(o.term).trim(),
      aka: Array.isArray(o.aka) ? o.aka.filter((a): a is string => typeof a === "string" && a.trim() !== "") : [],
      category: str(o.category),
      who: str(o.who),
      why: str(o.why),
      how: str(o.how),
      what: str(o.what),
      example: str(o.example),
      links: Array.isArray(o.links)
        ? o.links
            .filter((l): l is Record<string, unknown> => !!l && typeof l === "object")
            .map((l) => ({ label: str(l.label) || str(l.url), url: str(l.url) }))
            .filter((l) => /^https?:\/\//.test(l.url))
        : [],
      related: Array.isArray(o.related) ? o.related.filter((a): a is string => typeof a === "string") : [],
    });
  }
  if (!entries.length) return { entries: null, file: r.file, reason: "no valid terms" };
  return { entries, file: r.file };
}
