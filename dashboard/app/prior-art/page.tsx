import { P, L } from "@/lib/glossary-server";
import { repoJson } from "@/lib/data";
import { NotAvailable } from "@/components/ui";
import { PriorArtTable, type PaRow } from "@/components/PriorArtTable";

export const metadata = { title: "Prior art · Complex priors" };

const s = (v: unknown) => (typeof v === "string" ? v : v === null || v === undefined ? "" : String(v));

export default function PriorArt() {
  const r = repoJson<unknown>("docs/prior-art.json");
  const list = r.ok ? (Array.isArray(r.data) ? r.data : Array.isArray((r.data as any)?.entries) ? (r.data as any).entries : null) : null;
  const rows: PaRow[] = (list || [])
    .filter((x: any) => x && typeof x === "object")
    .map((x: any, i: number) => ({
      id: s(x.id) || String(i),
      title: s(x.title),
      authors: s(x.authors),
      venue: s(x.venue),
      year: s(x.year),
      url: /^https?:\/\//.test(s(x.doi_or_url)) ? s(x.doi_or_url) : s(x.doi_or_url) ? `https://doi.org/${s(x.doi_or_url)}` : "",
      cls: s(x.class) || "unclassified",
      verified: typeof x.verified === "boolean" ? x.verified : null,
      unverified_note: s(x.unverified_note),
      differentiation: <L>{s(x.differentiation)}</L>,
      what: <L>{s(x.what_it_does)}</L>,
      search: [x.title, x.authors, x.venue, x.year, x.class, x.differentiation, x.what_it_does, x.id].map(s).join(" ").toLowerCase(),
    }));
  const classes = [...new Set(rows.map((x) => x.cls))].sort();
  return (
    <div>
      <h1 className="h1">Prior art</h1>
      <P>
        Related work found during the prior-art search, each with a note on how this project differs. Entries marked not verified
        could not be confirmed against the publisher or an index; treat them with care.
      </P>
      <p className="mt-1 font-mono text-[11px] text-muted">source: {r.file}</p>
      {!r.ok || !list ? (
        <NotAvailable what="Prior-art table" file={r.file} reason={r.ok ? "unexpected structure" : r.reason} />
      ) : (
        <div className="mt-4">
          <PriorArtTable rows={rows} classes={classes} />
        </div>
      )}
    </div>
  );
}
