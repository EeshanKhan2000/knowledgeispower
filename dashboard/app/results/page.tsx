import React from "react";
import { P } from "@/lib/glossary-server";
import { resultJson, resultCsv } from "@/lib/data";
import { NotAvailable, Provenance, Section, Verdict } from "@/components/ui";
import { f, int, isNum, label, range, signed } from "@/lib/format";
import {
  BASELINES,
  cmpVerdict,
  collapseImputation,
  scoreRows,
  STRATA,
  STRATUM_LABEL,
  type Comparison,
  type Imputation,
  type ScoreRow,
} from "@/lib/results";
import { LineChart, colorFor, type Series } from "@/components/LineChart";

export const metadata = { title: "Results · Complex priors" };

const TOC = [
  ["imputation", "Imputation RMSE"],
  ["comparisons", "Paired comparisons"],
  ["panel", "Panel R²"],
  ["stability", "Stability"],
  ["classification", "Classification"],
  ["cross-context", "Cross-context"],
  ["discordant", "Discordant subunits"],
];

function nullVerdict(r: ScoreRow): React.ReactNode {
  if (!isNum(r.value) || !r.nullRange) return <span className="text-muted">—</span>;
  if (r.value > r.nullRange[1]) return <Verdict kind="good">above all nulls</Verdict>;
  if (r.value < r.nullRange[0]) return <Verdict kind="bad">below all nulls</Verdict>;
  return <Verdict kind="neutral">within null range</Verdict>;
}

/** Table for {hvp, random_mean, prior, prior__null_mean, prior__null_range} objects; higher = better. */
function ScoreTable({ o, metric, refKey = "hvp" }: { o: Record<string, unknown>; metric: string; refKey?: string }) {
  const { rows } = scoreRows(o);
  const ref = rows.find((r) => r.method === refKey)?.value;
  const max = Math.max(0, ...rows.flatMap((r) => [r.value, r.nullMean, r.nullRange?.[1]]).filter(isNum));
  return (
    <div className="tbl-wrap">
      <table className="tbl">
        <thead>
          <tr>
            <th>method</th>
            <th className="num">{metric}</th>
            <th className="hidden sm:table-cell" aria-hidden="true" />
            <th className="num">vs {label(refKey)}</th>
            <th className="num">null mean</th>
            <th className="num">null range</th>
            <th>vs own nulls</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const d = isNum(r.value) && isNum(ref) && r.method !== refKey ? r.value - ref : null;
            return (
              <tr key={r.method}>
                <td className={"min-w-[8rem] " + (BASELINES.has(r.method) ? "italic" : "font-medium text-ink")}>{label(r.method)}</td>
                <td className="num">{f(r.value)}</td>
                <td className="hidden w-24 sm:table-cell">
                  {isNum(r.value) && max > 0 && (
                    <svg viewBox="0 0 100 10" className="h-2.5 w-24" aria-hidden="true">
                      <rect x="0" y="1" width={Math.max(0, (r.value / max) * 100)} height="8" rx="2" fill={colorFor(r.method)} />
                      {isNum(r.nullMean) && <line x1={(r.nullMean / max) * 100} x2={(r.nullMean / max) * 100} y1="0" y2="10" stroke="var(--ink)" strokeWidth="1.5" />}
                    </svg>
                  )}
                </td>
                <td className={"num " + (d === null ? "" : d > 0 ? "text-good" : d < 0 ? "text-bad" : "")}>{d === null ? "—" : signed(d)}</td>
                <td className="num">{f(r.nullMean)}</td>
                <td className="num">{range(r.nullRange)}</td>
                <td>{nullVerdict(r)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function Extra({ o }: { o: Record<string, unknown> }) {
  const { extra } = scoreRows(o);
  if (!extra.length) return null;
  return (
    <p className="mt-2 break-words text-xs text-muted">
      {extra
        .filter(([, v]) => v === null || typeof v !== "object" || Array.isArray(v)) // nested objects are rendered as tables
        .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(", ") : String(v)}`)
        .join(" · ")}
    </p>
  );
}

function ImputationTables({ imp }: { imp: Imputation }) {
  return (
    <>
      {isNum(imp.eligible_proteins) && <p className="text-sm text-ink2">Eligible proteins: {int(imp.eligible_proteins)}.</p>}
      {Object.entries(imp.masks || {}).map(([mask, v]) => {
        const rows = collapseImputation(v.rows || []);
        const strata = [...new Set([...STRATA.filter((s) => rows.some((r) => r.byStratum[s])), ...rows.flatMap((r) => Object.keys(r.byStratum))])];
        const best: Record<string, number> = {};
        for (const s of strata) {
          const vals = rows.filter((r) => !r.isNull).map((r) => r.byStratum[s]?.rmse).filter(isNum);
          if (vals.length) best[s] = Math.min(...vals);
        }
        return (
          <div key={mask} className="mt-4">
            <h3 className="h3">Mask: {mask}</h3>
            <div className="tbl-wrap">
              <table className="tbl">
                <thead>
                  <tr>
                    <th>method</th>
                    {strata.map((s) => (
                      <th key={s} className="num">
                        RMSE · {STRATUM_LABEL[s] ?? s}
                      </th>
                    ))}
                    <th className="num">mean r (all)</th>
                    <th className="num">entries (all)</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr key={r.method + (r.isNull ? "__null" : "")} className={r.isNull ? "bg-surface2/60" : ""}>
                      <td className={"min-w-[9.5rem] " + (r.isNull ? "pl-5 text-muted" : BASELINES.has(r.method) ? "italic" : "font-medium text-ink")}>
                        {r.isNull ? `↳ ${label(r.method)} shuffled nulls (×${r.nReplicates})` : label(r.method)}
                      </td>
                      {strata.map((s) => {
                        const c = r.byStratum[s];
                        return (
                          <td key={s} className={"num " + (c && !r.isNull && c.rmse === best[s] ? "font-semibold text-ink" : "")}>
                            {c ? f(c.rmse) : "—"}
                            {c && !r.isNull && c.rmse === best[s] && <span className="sr-only"> (lowest)</span>}
                            {c?.range && <div className="text-[10px] text-muted">{range(c.range)}</div>}
                          </td>
                        );
                      })}
                      <td className="num">{f(r.byStratum.all?.r)}</td>
                      <td className="num">{int(r.byStratum.all?.n)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-1 text-xs text-muted">Bold = lowest RMSE among non-null methods in that column. Null rows show mean RMSE over replicates with min – max below.</p>
          </div>
        );
      })}
    </>
  );
}

function ComparisonTables({ imp }: { imp: Imputation }) {
  return (
    <>
      {Object.entries(imp.masks || {}).map(([mask, v]) => {
        const cs: Comparison[] = v.comparisons || [];
        const counts = { good: 0, bad: 0, neutral: 0 };
        cs.forEach((c) => counts[cmpVerdict(c).kind]++);
        return (
          <div key={mask} className="mt-4">
            <h3 className="h3">Mask: {mask}</h3>
            <p className="text-xs text-muted">
              {cs.length} comparisons: {counts.good} with lower error for the prior, {counts.bad} with higher error, {counts.neutral} unclear. &quot;Share by prior&quot; is the fraction of hidden entries the prior could fill from observed partners; the rest fell back to kNN.
            </p>
            <ul className="mt-2 space-y-2 md:hidden">
              {cs.map((c, i) => {
                const vd = cmpVerdict(c);
                return (
                  <li key={i} className={"rounded-xl border border-line p-3 " + (vd.kind === "good" ? "bg-goodbg/50" : vd.kind === "bad" ? "bg-badbg/50" : "bg-surface")}>
                    <div className="text-sm font-medium text-ink">
                      {label(c.prior)} vs {label(c.vs)}
                    </div>
                    <div className="text-xs text-muted">{STRATUM_LABEL[c.stratum] ?? c.stratum}</div>
                    <div className="mt-1">
                      <Verdict kind={vd.kind}>{vd.text}</Verdict>
                    </div>
                    <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 font-mono text-xs text-ink2">
                      <dt className="text-muted">ΔRMSE</dt>
                      <dd className={vd.kind === "good" ? "text-good" : vd.kind === "bad" ? "text-bad" : ""}>{signed(c.delta_rmse)}</dd>
                      <dt className="text-muted">95% CI</dt>
                      <dd>[{range(c.ci95).replace(" – ", ", ")}]</dd>
                      <dt className="text-muted">dz</dt>
                      <dd>{signed(c.effect_size_dz_sqerr)}</dd>
                      <dt className="text-muted">RMSE prior / ref</dt>
                      <dd>
                        {f(c.rmse_prior)} / {f(c.rmse_ref)}
                      </dd>
                      <dt className="text-muted">null RMSE range</dt>
                      <dd>{range(c.null_rmse_range)}</dd>
                      <dt className="text-muted">share by prior</dt>
                      <dd>{f(c.frac_entries_imputed_by_prior, 2)}</dd>
                      <dt className="text-muted">entries</dt>
                      <dd>{int(c.n_entries)}</dd>
                    </dl>
                  </li>
                );
              })}
            </ul>
            <div className="tbl-wrap mt-2 hidden md:block">
              <table className="tbl">
                <thead>
                  <tr>
                    <th>prior</th>
                    <th>vs</th>
                    <th>stratum</th>
                    <th className="num">ΔRMSE</th>
                    <th className="num">95% CI</th>
                    <th className="num">dz</th>
                    <th className="num">RMSE prior / ref</th>
                    <th className="num">null RMSE range</th>
                    <th className="num">share by prior</th>
                    <th className="num">entries</th>
                    <th>result</th>
                  </tr>
                </thead>
                <tbody>
                  {cs.map((c, i) => {
                    const vd = cmpVerdict(c);
                    return (
                      <tr key={i} className={vd.kind === "good" ? "bg-goodbg/50" : vd.kind === "bad" ? "bg-badbg/50" : ""}>
                        <td className="font-medium text-ink">{label(c.prior)}</td>
                        <td>{label(c.vs)}</td>
                        <td>{STRATUM_LABEL[c.stratum] ?? c.stratum}</td>
                        <td className={"num " + (vd.kind === "good" ? "text-good" : vd.kind === "bad" ? "text-bad" : "")}>{signed(c.delta_rmse)}</td>
                        <td className="num">[{range(c.ci95).replace(" – ", ", ")}]</td>
                        <td className="num">{signed(c.effect_size_dz_sqerr)}</td>
                        <td className="num">
                          {f(c.rmse_prior)} / {f(c.rmse_ref)}
                        </td>
                        <td className="num">{range(c.null_rmse_range)}</td>
                        <td className="num">{f(c.frac_entries_imputed_by_prior, 2)}</td>
                        <td className="num">{int(c.n_entries)}</td>
                        <td>
                          <Verdict kind={vd.kind}>{vd.text}</Verdict>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        );
      })}
    </>
  );
}

function PanelCharts({ panel, ks, stratum }: { panel: Record<string, any>; ks: string[]; stratum: string }) {
  const rowsAt = (k: string) => scoreRows(panel[k]?.[stratum] || {}).rows;
  const methods = [...new Set(ks.flatMap((k) => rowsAt(k).map((r) => r.method)))];
  const priors = methods.filter((mth) => !BASELINES.has(mth) && ks.some((k) => isNum(rowsAt(k).find((r) => r.method === mth)?.nullMean)));
  const baselines = methods.filter((mth) => BASELINES.has(mth));
  const all = ks.flatMap((k) => rowsAt(k).flatMap((r) => [r.value, r.nullMean, ...(r.nullRange || [])])).filter(isNum);
  const domain: [number, number] = [Math.min(0, ...all), Math.max(...all)];
  const pts = (mth: string, f: (r: ScoreRow) => number | null) =>
    ks.map((k) => {
      const r = rowsAt(k).find((x) => x.method === mth);
      return { x: +k, y: r ? f(r) : null };
    });
  const baseSeries: Series[] = baselines.map((b, i) => ({
    key: b,
    name: label(b),
    color: i === 0 ? "var(--ink-2)" : "var(--muted)",
    dotted: i > 0,
    points: pts(b, (r) => r.value),
  }));
  return (
    <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
      {priors.map((p) => (
        <LineChart
          key={p}
          title={label(p)}
          xs={ks.map(Number)}
          yLabel={`mean held-out R², ${STRATUM_LABEL[stratum] ?? stratum}`}
          domain={domain}
          series={[
            ...baseSeries,
            {
              key: p + "__null",
              name: "its shuffled nulls (mean, range)",
              color: colorFor(p),
              dashed: true,
              points: pts(p, (r) => r.nullMean),
              band: ks.map((k) => rowsAt(k).find((x) => x.method === p)?.nullRange ?? null),
            },
            { key: p, name: label(p), color: colorFor(p), points: pts(p, (r) => r.value) },
          ]}
        />
      ))}
    </div>
  );
}

function PanelSection({ panel }: { panel: Record<string, any> }) {
  const ks = Object.keys(panel)
    .filter((k) => /^\d+$/.test(k))
    .sort((a, b) => +a - +b);
  const strata = [...new Set(ks.flatMap((k) => Object.keys(panel[k]).filter((s) => s !== "panels")))];
  const first = strata.includes("in_complex") ? "in_complex" : strata[0];
  return (
    <>
      <h3 className="h3">Proteins {STRATUM_LABEL[first] ?? first}: one small chart per prior</h3>
      <p className="text-xs text-muted">
        Solid coloured line: the prior. Dashed line and shaded band: the mean and range of that prior&apos;s shuffled nulls. Dark
        grey: HVP; dotted grey: random panels. All four charts share one y-axis. Hover a point for its value.
      </p>
      <PanelCharts panel={panel} ks={ks} stratum={first} />
      {strata
        .filter((s) => s !== first)
        .map((s) => (
          <details key={s} className="mt-3">
            <summary className="cursor-pointer text-sm font-semibold text-ink">Charts: {STRATUM_LABEL[s] ?? s}</summary>
            <PanelCharts panel={panel} ks={ks} stratum={s} />
          </details>
        ))}
      {ks.map((k) => (
        <details key={k} className="card mt-3" open={k === ks[0]}>
          <summary className="cursor-pointer font-semibold text-ink">Table: k = {k}</summary>
          {strata.map((s) => (
            <div key={s} className="mt-3">
              <h4 className="text-sm font-semibold text-ink2">{STRATUM_LABEL[s] ?? s}</h4>
              <ScoreTable o={panel[k][s] || {}} metric="R²" />
            </div>
          ))}
        </details>
      ))}
    </>
  );
}

export default function Results() {
  const imp = resultJson<Imputation>("imputation.json");
  const panel = resultJson<Record<string, any>>("panel.json");
  const stab = resultJson<Record<string, unknown>>("stability.json");
  const cls = resultJson<Record<string, unknown>>("classification.json");
  const cross = resultJson<Record<string, any>>("cross_context.json");
  const disc = resultCsv("discordant_subunits.csv");

  return (
    <div>
      <h1 className="h1">Results</h1>
      <P>
        Every row the benchmark wrote is shown here, including the ones where the complex prior did worse. Losses are tinted red
        and marked ✗; wins are tinted green and marked ✓.
      </P>
      <Provenance files={["imputation.json", "panel.json", "stability.json", "classification.json", "cross_context.json", "discordant_subunits.csv", "run_meta.json"]} />
      <nav aria-label="On this page" className="mt-4 flex flex-wrap gap-2">
        {TOC.map(([id, t]) => (
          <a key={id} href={`#${id}`} className="chip no-underline">
            {t}
          </a>
        ))}
      </nav>

      <Section id="imputation" title="Imputation: error on hidden values (RMSE)">
        <P>
          Observed values were hidden on purpose and then reconstructed; RMSE is the typical size of the error in log2 units, so
          lower is better.
        </P>
        {imp.ok ? <ImputationTables imp={imp.data} /> : <NotAvailable what="Imputation results" file={imp.file} reason={imp.reason} />}
      </Section>

      <Section id="comparisons" title="Paired comparisons with confidence intervals">
        <P>
          Each prior is compared with kNN and with the mean of its own shuffled nulls on exactly the same hidden entries: ΔRMSE is
          prior minus reference (negative favours the prior), the 95% CI comes from a paired bootstrap, and dz is the paired effect
          size on squared errors.
        </P>
        {imp.ok ? <ComparisonTables imp={imp.data} /> : <NotAvailable what="Imputation comparisons" file={imp.file} reason={imp.reason} />}
      </Section>

      <Section id="panel" title="Panel design: how well k proteins predict the rest (R²)">
        <P>
          A panel of k proteins is chosen by each method, and ridge regression predicts every other protein from it; the score is
          mean R² on held-out cells, so higher is better. Dashed lines are the shuffled-null means for the same prior.
        </P>
        {panel.ok ? <PanelSection panel={panel.data} /> : <NotAvailable what="Panel results" file={panel.file} reason={panel.reason} />}
      </Section>

      <Section id="stability" title="Stability of the chosen panel">
        <P>
          The panel is re-chosen on bootstrap resamples of cells; the score is the mean Jaccard overlap between those panels, where
          1 means the same proteins every time.
        </P>
        {stab.ok ? (
          <>
            <ScoreTable o={stab.data} metric="Jaccard" />
            <Extra o={stab.data} />
          </>
        ) : (
          <NotAvailable what="Stability results" file={stab.file} reason={stab.reason} />
        )}
      </Section>

      <Section id="classification" title="Classification (sanity check only)">
        <P>
          A classifier predicts each cell&apos;s sorted population from its panel, scored by macro-F1; this checks the panels carry
          signal and is not evidence for the claim.
        </P>
        {cls.ok ? (
          <>
            <div className="my-2 flex flex-wrap items-center gap-2 text-sm">
              <span className="text-ink2">Ceiling flag:</span>
              {cls.data.ceiling_flag === true ? (
                <Verdict kind="bad">ceiling reached: random panels already score high, comparisons uninformative</Verdict>
              ) : cls.data.ceiling_flag === false ? (
                <Verdict kind="neutral">not at ceiling</Verdict>
              ) : (
                <Verdict kind="neutral">not reported</Verdict>
              )}
            </div>
            {typeof cls.data.note === "string" && <p className="text-sm italic text-muted">Note from file: {cls.data.note}</p>}
            <ScoreTable o={cls.data} metric="macro-F1" />
            <Extra o={cls.data} />
          </>
        ) : (
          <NotAvailable what="Classification results" file={cls.file} reason={cls.reason} />
        )}
      </Section>

      <Section id="cross-context" title="Cross-context: choose on some cell types, test on others">
        <P>
          The panel is chosen using one group of cell populations and scored (held-out R²) on a different group, to see whether a
          prior-guided panel transfers.
        </P>
        {cross.ok ? (
          <>
            <Extra o={cross.data} />
            {Object.entries(cross.data)
              .filter(([, v]) => v && typeof v === "object" && !Array.isArray(v))
              .map(([s, v]) => (
                <div key={s} className="mt-3">
                  <h3 className="text-sm font-semibold text-ink2">{STRATUM_LABEL[s] ?? s}</h3>
                  <ScoreTable o={v} metric="R²" />
                </div>
              ))}
          </>
        ) : (
          <NotAvailable what="Cross-context results" file={cross.file} reason={cross.reason} />
        )}
      </Section>

      <Section id="discordant" title="Discordant subunits: hypotheses, not findings">
        <P>
          These complex members track their curated partners much less than expected from shuffled graphs; each is a hypothesis
          to check (a database error, or a protein with a second job outside the complex), not a finding.
        </P>
        {disc.ok ? (
          <DiscTable rows={disc.data} />
        ) : (
          <NotAvailable what="Discordant subunit list" file={disc.file} reason={disc.reason} />
        )}
      </Section>
    </div>
  );
}

function DiscTable({ rows }: { rows: Record<string, string>[] }) {
  const sorted = [...rows].sort((a, b) => (parseFloat(b.discordance_z) || -Infinity) - (parseFloat(a.discordance_z) || -Infinity)).slice(0, 25);
  const n = (s: string, d = 3) => (s === "" || isNaN(+s) ? s || "—" : (+s).toFixed(d));
  return (
    <>
      <p className="text-xs text-muted">
        Top {sorted.length} of {rows.length} rows by discordance z. Label column copied from the file.
      </p>
      <div className="tbl-wrap mt-2">
        <table className="tbl">
          <thead>
            <tr>
              <th>#</th>
              <th>protein</th>
              <th>example complexes</th>
              <th className="num">complexes</th>
              <th className="num">partners measured</th>
              <th className="num">detection</th>
              <th className="num">r with partners</th>
              <th className="num">null r (mean ± sd)</th>
              <th className="num">z</th>
              <th>label</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((r, i) => (
              <tr key={r.protein + i}>
                <td className="num">{i + 1}</td>
                <td>
                  <div className="font-medium text-ink">{r.symbols || "—"}</div>
                  <div className="font-mono text-[11px] text-muted">{r.protein}</div>
                </td>
                <td className="min-w-[14rem] text-xs">{r.example_complexes}</td>
                <td className="num">{r.n_complexes}</td>
                <td className="num">{r.n_partners_in_dataset}</td>
                <td className="num">{n(r.detection, 2)}</td>
                <td className="num">{n(r.r_with_partners)}</td>
                <td className="num">
                  {n(r.null_mean_r)} ± {n(r.null_sd_r)}
                </td>
                <td className="num">{n(r.discordance_z, 1)}</td>
                <td className="min-w-[12rem] text-xs italic">{r.label}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
