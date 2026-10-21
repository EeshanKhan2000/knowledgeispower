import { glossary, matcher, P } from "@/lib/glossary-server";
import { Linked } from "@/components/Linked";
import { slug } from "@/lib/linkify";
import { NotAvailable } from "@/components/ui";

export const metadata = { title: "Glossary · Complex priors" };

export default function Glossary() {
  const entries = glossary.entries;
  const cats = entries ? [...new Set(entries.map((e) => e.category || "Other"))].sort() : [];
  const known = new Set((entries || []).map((e) => e.term));
  return (
    <div>
      <h1 className="h1">Glossary</h1>
      <P>Every term here can be tapped wherever it appears on the site. Terms inside a definition open the next definition.</P>
      <p className="mt-1 font-mono text-[11px] text-muted">source: {glossary.file}</p>
      {!entries ? (
        <div role="status" className="my-3 rounded-xl border border-dashed border-line bg-neutralbg p-4 text-sm text-ink2">
          <strong className="text-ink">Glossary not available yet.</strong> Expected <code className="font-mono">{glossary.file}</code>
          {glossary.reason ? ` (${glossary.reason})` : ""}.
        </div>
      ) : (
        <>
          <nav aria-label="Categories" className="mt-4 flex flex-wrap gap-2">
            {cats.map((c) => (
              <a key={c} href={`#cat-${slug(c)}`} className="chip">
                {c}
              </a>
            ))}
          </nav>
          {cats.map((c) => (
            <section key={c} id={`cat-${slug(c)}`} className="scroll-mt-20">
              <h2 className="h2">{c}</h2>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                {entries
                  .filter((e) => (e.category || "Other") === c)
                  .sort((a, b) => a.term.localeCompare(b.term))
                  .map((e) => (
                    <article key={e.term} id={slug(e.term)} className="card scroll-mt-20">
                      <h3 className="text-lg font-semibold text-ink">
                        <button type="button" className="term" data-term={e.term}>
                          {e.term}
                        </button>
                      </h3>
                      {e.aka.length > 0 && <p className="text-xs text-muted">also: {e.aka.join(", ")}</p>}
                      <dl className="mt-2 space-y-2 text-sm">
                        {(
                          [
                            ["Why", e.why],
                            ["How", e.how],
                            ["What", e.what],
                            ["Example", e.example],
                            ["Who", e.who],
                          ] as const
                        )
                          .filter(([, v]) => v)
                          .map(([k, v]) => (
                            <div key={k}>
                              <dt className="text-xs font-semibold uppercase tracking-wide text-muted">{k}</dt>
                              <dd className="text-ink2">
                                <Linked text={v} m={matcher} exclude={e.term} />
                              </dd>
                            </div>
                          ))}
                      </dl>
                      {e.links.length > 0 && (
                        <ul className="mt-2 space-y-1 text-sm">
                          {e.links.map((l) => (
                            <li key={l.url}>
                              <a className="link break-words" href={l.url} target="_blank" rel="noreferrer noopener">
                                {l.label}
                              </a>
                            </li>
                          ))}
                        </ul>
                      )}
                      {e.related.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          {e.related.map((r) =>
                            known.has(r) ? (
                              <button key={r} type="button" className="chip !py-0.5 text-xs" data-term={r}>
                                {r}
                              </button>
                            ) : (
                              <span key={r} className="chip !py-0.5 text-xs opacity-60">
                                {r}
                              </span>
                            ),
                          )}
                        </div>
                      )}
                    </article>
                  ))}
              </div>
            </section>
          ))}
        </>
      )}
    </div>
  );
}
