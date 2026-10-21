import { P, L } from "@/lib/glossary-server";
import { resultJson } from "@/lib/data";
import { preregTests } from "@/lib/prereg";
import { NotAvailable, Provenance, Verdict } from "@/components/ui";
import { cmpVerdict, type Imputation } from "@/lib/results";
import { f, label, range, signed } from "@/lib/format";
import { StepDiagram } from "@/components/StepDiagram";

const CLAIM =
  "Curated protein-complex membership (CORUM, EBI Complex Portal) is a better prior for reconstructing a cell's protein state from incomplete single-cell proteomics measurements than data alone, than generic PPI networks (STRING), and than a degree-preserving shuffled version of the same graph.";

type Verdicts = Record<string, unknown>;

function detailText(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "boolean") return v ? "yes" : "no";
  if (typeof v === "number") return Number.isInteger(v) ? String(v) : v.toFixed(3);
  if (Array.isArray(v)) return v.map(detailText).join(", ");
  if (typeof v === "object")
    return Object.entries(v as Record<string, unknown>)
      .map(([k, x]) => `${label(k)}: ${detailText(x)}`)
      .join(" · ");
  return String(v);
}

export default function Overview() {
  const verdicts = resultJson<Verdicts>("verdicts.json");
  const imp = resultJson<Imputation>("imputation.json");
  const prereg = preregTests();
  const testNums = verdicts.ok
    ? [...new Set(Object.keys(verdicts.data).map((k) => /^test(\d+)_pass$/.exec(k)?.[1]).filter((x): x is string => !!x))].sort()
    : [];
  const nPass = verdicts.ok ? testNums.filter((n) => verdicts.data[`test${n}_pass`] === true).length : 0;

  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-muted">The claim under test</p>
      <blockquote className="mt-2 border-l-4 border-accent pl-4 text-lg leading-relaxed text-ink md:text-xl">
        <L>{CLAIM}</L>
      </blockquote>
      <P>
        This dashboard reports the preregistered benchmark of that claim, whichever way it comes out. Every number below is
        read from the benchmark output files when the site is built.
      </P>

      <h2 className="h2">Headline: preregistered tests</h2>
      <Provenance files={["verdicts.json", "imputation.json", "run_meta.json"]} />
      {!verdicts.ok ? (
        <NotAvailable what="Test verdicts" file={verdicts.file} reason={verdicts.reason} />
      ) : (
        <>
          <p className="prose-p">
            <strong className="text-ink">
              {nPass} of {testNums.length}
            </strong>{" "}
            preregistered tests passed in this run.
          </p>
          <ol className="grid gap-3 md:grid-cols-2">
            {testNums.map((n) => {
              const pass = verdicts.data[`test${n}_pass`];
              const pt = prereg.tests.find((t) => t.n === n);
              const details = Object.entries(verdicts.data).filter(([k]) => k.startsWith(`test${n}_`) && k !== `test${n}_pass` || k === `test${n}`);
              return (
                <li key={n} className="card">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h3 className="font-semibold text-ink">
                      Test {n}
                      {pt ? `: ${pt.title}` : ""}
                    </h3>
                    {pass === true ? (
                      <Verdict kind="good">passed</Verdict>
                    ) : pass === false ? (
                      <Verdict kind="bad">did not pass</Verdict>
                    ) : (
                      <Verdict kind="neutral">no verdict</Verdict>
                    )}
                  </div>
                  {pt?.pass && (
                    <p className="mt-2 text-sm text-ink2">
                      <span className="font-semibold">Pass rule: </span>
                      <L>{pt.pass}</L>
                    </p>
                  )}
                  <ul className="mt-2 space-y-1 text-xs text-muted">
                    {details.map(([k, v]) => (
                      <li key={k} className="break-words">
                        <span className="font-mono">{k}</span>: {detailText(v)}
                      </li>
                    ))}
                  </ul>
                </li>
              );
            })}
          </ol>
          {!prereg.ok && <NotAvailable what="Preregistered pass rules" file={prereg.file} />}
        </>
      )}

      <h3 className="h3">Imputation, proteins in a complex: complex prior vs. references</h3>
      <P>
        Each row is a paired comparison on the same masked entries. ΔRMSE is the prior&apos;s error minus the reference&apos;s error,
        so a negative value means the complex prior reconstructed the hidden values more accurately.
      </P>
      {!imp.ok ? (
        <NotAvailable what="Imputation comparisons" file={imp.file} reason={imp.reason} />
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {Object.entries(imp.data.masks || {}).map(([mask, v]) => (
            <div key={mask} className="card">
              <h4 className="font-semibold text-ink">Mask: {mask}</h4>
              <ul className="mt-2 divide-y divide-line">
                {(v.comparisons || [])
                  .filter((c) => c.stratum === "in_complex" && (c.prior === "corum" || c.prior === "complexportal"))
                  .map((c, i) => {
                    const vd = cmpVerdict(c);
                    return (
                      <li key={i} className="py-2 text-sm">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <span className="text-ink">
                            {label(c.prior)} vs {label(c.vs)}
                          </span>
                          <Verdict kind={vd.kind}>{vd.text}</Verdict>
                        </div>
                        <div className="mt-1 font-mono text-xs text-muted">
                          ΔRMSE {signed(c.delta_rmse)} · 95% CI [{range(c.ci95).replace(" – ", ", ")}] · RMSE {f(c.rmse_prior)} vs {f(c.rmse_ref)}
                        </div>
                      </li>
                    );
                  })}
              </ul>
            </div>
          ))}
        </div>
      )}

      <h2 className="h2">How it works, in three steps</h2>
      <StepDiagram />
      <P>
        The full story, from protein machines to the model, is on the Mechanism page. Every row of every result, including
        the losses, is on the Results page.
      </P>
    </div>
  );
}
