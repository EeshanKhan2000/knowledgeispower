// Pure helpers (usable on server and client) to find glossary terms in prose.

export type TermLike = { term: string; aka: string[] };
export type Segment = { text: string; id?: string };

type Cand = { key: string; id: string; exact: boolean };

export type Matcher = {
  re: RegExp | null;
  byLower: Map<string, Cand[]>;
};

const esc = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/** Acronym-like or mixed-case names (CORUM, kNN, AnnData) match case-sensitively; plain words match any case. */
function isExact(s: string): boolean {
  return /[A-Z]/.test(s.slice(1)) || s.length <= 3;
}

export function buildMatcher(entries: TermLike[] | null | undefined): Matcher {
  const byLower = new Map<string, Cand[]>();
  if (!entries) return { re: null, byLower };
  for (const e of entries) {
    for (const k of [e.term, ...(e.aka || [])]) {
      const key = k.trim();
      if (key.length < 2) continue;
      const lk = key.toLowerCase();
      const list = byLower.get(lk) || [];
      if (!list.some((c) => c.id === e.term && c.key === key)) list.push({ key, id: e.term, exact: isExact(key) });
      byLower.set(lk, list);
    }
  }
  const keys = [...byLower.keys()].sort((a, b) => b.length - a.length);
  if (!keys.length) return { re: null, byLower };
  const re = new RegExp(`(?<![\\w\\-])(${keys.map(esc).join("|")})(?:s|es)?(?![\\w\\-])`, "gi");
  return { re, byLower };
}

/** Split text into segments; the first occurrence of each term (per call / per `seen` set) gets an id. */
export function linkSegments(text: string, m: Matcher, seen: Set<string> = new Set(), exclude?: string): Segment[] {
  if (!m.re || !text) return [{ text }];
  const re = new RegExp(m.re.source, "gi");
  const out: Segment[] = [];
  let last = 0;
  let match: RegExpExecArray | null;
  while ((match = re.exec(text))) {
    const word = match[1];
    const cands = m.byLower.get(word.toLowerCase()) || [];
    const c = cands.find((c) => (c.exact ? c.key === word : true));
    if (!c || c.id === exclude || seen.has(c.id)) {
      re.lastIndex = match.index + 1;
      continue;
    }
    seen.add(c.id);
    if (match.index > last) out.push({ text: text.slice(last, match.index) });
    out.push({ text: match[0], id: c.id });
    last = match.index + match[0].length;
  }
  if (last < text.length) out.push({ text: text.slice(last) });
  return out;
}

const attr = (s: string) => s.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");

/** Linkify text nodes inside an HTML string (from marked). Skips code/pre/a/headings; resets per block. */
export function linkifyHtml(html: string, m: Matcher): string {
  if (!m.re) return html;
  const parts = html.split(/(<[^>]+>)/g);
  const skipTags = new Set(["code", "pre", "a", "button", "h1", "h2", "h3", "h4", "h5", "h6", "script", "style"]);
  const blockTags = new Set(["p", "li", "blockquote", "td", "th", "dd", "dt"]);
  let skip = 0;
  let seen = new Set<string>();
  return parts
    .map((p) => {
      if (p.startsWith("<")) {
        const t = /^<\s*(\/)?\s*([a-zA-Z0-9]+)/.exec(p);
        if (t) {
          const name = t[2].toLowerCase();
          if (skipTags.has(name) && !p.endsWith("/>")) skip += t[1] ? -1 : 1;
          if (skip < 0) skip = 0;
          if (blockTags.has(name)) seen = new Set();
        }
        return p;
      }
      if (skip > 0 || !p.trim()) return p;
      return linkSegments(p, m, seen)
        .map((s) => (s.id ? `<button type="button" class="term" data-term="${attr(s.id)}">${s.text}</button>` : s.text))
        .join("");
    })
    .join("");
}

export const slug = (s: string) =>
  s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "term";
