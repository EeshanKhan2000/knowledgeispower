// Typed views over the results JSON (schemas as written by benchmarks/run.py).
import { isNum, mean } from "./format";

export type ImpRow = { method: string; stratum: string; rmse: number; pearson_r_by_seed?: number[]; n_entries?: number };
export type Comparison = {
  prior: string;
  vs: string;
  stratum: string;
  delta_rmse: number;
  ci95: [number, number];
  effect_size_dz_sqerr: number;
  n_entries: number;
  rmse_prior: number;
  rmse_ref: number;
  null_rmse_range: [number, number] | null;
  frac_entries_imputed_by_prior: number;
  significant_improvement: boolean;
};
export type Imputation = {
  eligible_proteins?: number;
  masks: Record<string, { rows: ImpRow[]; comparisons: Comparison[] }>;
};

export const STRATA = ["all", "in_complex", "not_in_complex"];
export const STRATUM_LABEL: Record<string, string> = { all: "all proteins", in_complex: "in a complex", not_in_complex: "not in a complex" };

/** Verdict on a paired comparison: delta = prior RMSE − reference RMSE, so negative = prior better. */
export function cmpVerdict(c: Comparison): { kind: "good" | "bad" | "neutral"; text: string } {
  const lo = c.ci95?.[0];
  const hi = c.ci95?.[1];
  if (isNum(hi) && hi < -1e-9) return { kind: "good", text: "prior lower error (CI excludes 0)" };
  if (isNum(lo) && lo > 1e-9) return { kind: "bad", text: "prior higher error (CI excludes 0)" };
  return { kind: "neutral", text: "no clear difference (CI includes 0)" };
}

export type CollapsedImp = {
  method: string;
  isNull: boolean;
  nReplicates: number;
  byStratum: Record<string, { rmse: number | null; range: [number, number] | null; r: number | null; n: number | null }>;
};

/** Collapse '<prior>__null<i>' replicates into mean + range; keep every other method as its own row. */
export function collapseImputation(rows: ImpRow[]): CollapsedImp[] {
  const groups = new Map<string, ImpRow[]>();
  const order: string[] = [];
  for (const r of rows) {
    const m = /^(.*)__null\d+$/.exec(r.method);
    const key = m ? `${m[1]}__null` : r.method;
    if (!groups.has(key)) {
      groups.set(key, []);
      order.push(key);
    }
    groups.get(key)!.push(r);
  }
  // Put each null group right after its prior.
  const base = order.filter((k) => !k.endsWith("__null"));
  const nulls = order.filter((k) => k.endsWith("__null"));
  const final: string[] = [];
  for (const b of base) {
    final.push(b);
    if (nulls.includes(`${b}__null`)) final.push(`${b}__null`);
  }
  for (const n of nulls) if (!final.includes(n)) final.push(n);

  return final.map((key) => {
    const rs = groups.get(key)!;
    const isNull = key.endsWith("__null");
    const strata = [...new Set([...STRATA, ...rs.map((r) => r.stratum)])];
    const byStratum: CollapsedImp["byStratum"] = {};
    let nRep = 0;
    for (const s of strata) {
      const sub = rs.filter((r) => r.stratum === s);
      if (!sub.length) continue;
      nRep = Math.max(nRep, sub.length);
      const vals = sub.map((r) => r.rmse).filter(isNum);
      const rs2 = sub.flatMap((r) => (r.pearson_r_by_seed || []).filter(isNum));
      byStratum[s] = {
        rmse: mean(vals),
        range: isNull && vals.length ? [Math.min(...vals), Math.max(...vals)] : null,
        r: mean(rs2),
        n: isNum(sub[0].n_entries) ? sub[0].n_entries! : null,
      };
    }
    return { method: isNull ? key.replace(/__null$/, "") : key, isNull, nReplicates: nRep, byStratum };
  });
}

const META_KEYS = new Set(["k", "n_bootstraps", "n_cells_select", "n_cells_eval", "select_on", "evaluate_on", "note", "ceiling_flag"]);

export type ScoreRow = { method: string; value: number | null; nullMean: number | null; nullRange: [number, number] | null };

/** For objects shaped {hvp, random_mean, <prior>, <prior>__null_mean, <prior>__null_range, ...}. */
export function scoreRows(o: Record<string, unknown>): { rows: ScoreRow[]; extra: [string, unknown][] } {
  const rows: ScoreRow[] = [];
  const extra: [string, unknown][] = [];
  const keys = Object.keys(o);
  for (const k of keys) {
    if (/__null_(mean|range)$/.test(k)) continue;
    const v = o[k];
    if (META_KEYS.has(k)) {
      extra.push([k, v]);
      continue;
    }
    if (isNum(v) || v === null) {
      const nm = o[`${k}__null_mean`];
      const nr = o[`${k}__null_range`];
      rows.push({
        method: k,
        value: isNum(v) ? v : null,
        nullMean: isNum(nm) ? nm : null,
        nullRange: Array.isArray(nr) && nr.length === 2 && isNum(nr[0]) && isNum(nr[1]) ? [nr[0], nr[1]] : null,
      });
    } else extra.push([k, v]);
  }
  // orphan null keys (prior missing) still shown
  for (const k of keys) {
    const m = /^(.*)__null_mean$/.exec(k);
    if (m && !(m[1] in o)) rows.push({ method: m[1], value: null, nullMean: isNum(o[k]) ? (o[k] as number) : null, nullRange: null });
  }
  return { rows, extra };
}

export const BASELINES = new Set(["hvp", "random_mean", "random", "knn", "mean"]);
