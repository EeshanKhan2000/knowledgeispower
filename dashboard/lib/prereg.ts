import { repoText } from "./data";

export type PreregTest = { n: string; title: string; pass: string };

/** Extract "**Test N (...): title.**" headings and their "**Pass:**" criteria from PREREGISTRATION.md. */
export function preregTests(): { ok: boolean; file: string; tests: PreregTest[] } {
  const t = repoText("benchmarks/PREREGISTRATION.md");
  if (!t.ok) return { ok: false, file: t.file, tests: [] };
  const lines = t.data.split(/\r?\n/);
  const tests: PreregTest[] = [];
  let cur: PreregTest | null = null;
  for (let i = 0; i < lines.length; i++) {
    const h = /^\*\*Test (\d+)(?:\s*\([^)]*\))?:\s*(.+?)\*\*/.exec(lines[i]);
    if (h) {
      cur = { n: h[1], title: h[2].replace(/\.$/, ""), pass: "" };
      tests.push(cur);
      continue;
    }
    if (/^\*\*|^##/.test(lines[i])) cur = null;
    const p = /\*\*Pass:\*\*\s*(.*)$/.exec(lines[i]);
    if (cur && p) {
      let txt = p[1];
      for (let j = i + 1; j < lines.length && /^\s{2,}\S/.test(lines[j]) && !/^\s*-\s/.test(lines[j]); j++) txt += " " + lines[j].trim();
      cur.pass = txt.replace(/`/g, "").replace(/\*\*/g, "");
    }
  }
  return { ok: true, file: t.file, tests };
}
