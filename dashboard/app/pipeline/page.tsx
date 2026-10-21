import { P } from "@/lib/glossary-server";
import { resultJson } from "@/lib/data";
import { StepPicker, type Step } from "@/components/StepPicker";
import { NotAvailable, Provenance } from "@/components/ui";
import { f, int, label } from "@/lib/format";

export const metadata = { title: "Pipeline · Complex priors" };

type Coverage = Record<string, any>;

export default function Pipeline() {
  const cov = resultJson<Coverage>("coverage.json");
  const ds = cov.ok ? cov.data._dataset : null;
  const priors = cov.ok ? Object.entries(cov.data).filter(([k]) => !k.startsWith("_")) : [];

  const steps: Step[] = [
    {
      id: "ms",
      title: "Mass spectrometry",
      short: "measure proteins cell by cell",
      body: (
        <>
          <P>
            Single cells are sorted into wells, their proteins are cut into peptides, and a mass spectrometer identifies and
            counts the peptides. Peptide signals are rolled up into protein groups. Each cell holds so little protein that many
            proteins fall below the detection limit in some cells, which leaves missing values.
          </P>
          <P>Low-abundance proteins go missing more often, so the missing values are not random. The benchmark tests both a random (MCAR) and an intensity-dependent (MNAR) mask.</P>
        </>
      ),
    },
    {
      id: "anndata",
      title: "AnnData matrix",
      short: "cells × proteins, NaN = missing",
      body: (
        <>
          <P>
            Measurements are stored as an AnnData object: one row per cell, one column per protein, values as log2 intensity,
            and NaN where a protein was not detected. Missing values are never filled with zero, because zero would mean
            &quot;measured and absent&quot;, which is a different statement.
          </P>
          {ds ? (
            <p className="mt-2 text-sm text-ink2">
              This run&apos;s dataset (from <code className="font-mono">coverage.json</code>): {int(ds.n_cells)} cells ×{" "}
              {int(ds.n_proteins)} proteins, missing fraction {f(ds.missing_fraction, 3)}, {int(ds.n_in_complex)} proteins in at
              least one curated complex.
            </p>
          ) : (
            <NotAvailable what="Dataset summary" file={cov.file} reason={cov.ok ? "no _dataset key" : cov.reason} />
          )}
        </>
      ),
    },
    {
      id: "prior",
      title: "Prior graph",
      short: "proteins = nodes, shared complexes = edges",
      body: (
        <>
          <P>
            Each prior becomes a graph over the measured proteins. For CORUM and Complex Portal, two proteins are joined if they
            share a curated complex, weighted by how many complexes they share. For STRING, edges come from the interaction
            score. Every graph also gets degree-preserving shuffled copies, used as nulls.
          </P>
          {priors.length > 0 ? (
            <div className="tbl-wrap mt-2">
              <table className="tbl">
                <thead>
                  <tr>
                    <th>prior</th>
                    <th className="num">proteins with edges</th>
                    <th className="num">edges</th>
                    <th className="num">unmapped</th>
                  </tr>
                </thead>
                <tbody>
                  {priors.map(([k, v]) => (
                    <tr key={k}>
                      <td>{label(k)}</td>
                      <td className="num">{int(v?.n_with_edges)}</td>
                      <td className="num">{int(v?.n_edges)}</td>
                      <td className="num">{f(v?.unmapped_fraction, 3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <NotAvailable what="Prior coverage" file={cov.file} reason={cov.ok ? undefined : cov.reason} />
          )}
        </>
      ),
    },
    {
      id: "propagation",
      title: "Propagation",
      short: "spread information along edges",
      body: (
        <>
          <P>
            For imputation, each missing value is predicted from the z-scores of the protein&apos;s observed partners in the same
            cell, averaged with edge weights and scaled by one fitted factor β per graph. β is fitted only on entries that were
            not hidden.
          </P>
          <P>
            For panel design, a random walk with restart spreads each protein&apos;s variance score along the graph, so proteins
            that sit in well-connected, variable complexes rise in the ranking.
          </P>
        </>
      ),
    },
    {
      id: "tasks",
      title: "Imputation & panel",
      short: "fill gaps; pick k proteins",
      body: (
        <>
          <P>
            Imputation: hide a share of the observed values, reconstruct them with each method (mean, kNN, each prior and its
            nulls) and compare to the hidden truth.
          </P>
          <P>
            Panel design: choose k proteins (k = 25, 50, 100) to measure, then predict all the others from them with ridge
            regression. A good prior should pick panels that predict the rest well.
          </P>
        </>
      ),
    },
    {
      id: "eval",
      title: "Evaluation",
      short: "preregistered tests, every row reported",
      body: (
        <>
          <P>
            Scores are RMSE for imputation and held-out R² for panels, with a paired bootstrap 95% confidence interval for
            imputation differences. Pass rules were written down in the preregistration before the benchmark ran. Losses are
            reported next to wins.
          </P>
        </>
      ),
    },
  ];

  return (
    <div>
      <h1 className="h1">Pipeline</h1>
      <P>Tap a step to see what happens there. The steps run in order, from the instrument to the scorecard.</P>
      <Provenance files={["coverage.json", "run_meta.json"]} />
      <div className="mt-4">
        <StepPicker steps={steps} />
      </div>
    </div>
  );
}
