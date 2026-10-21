export const isNum = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);

export function f(v: unknown, d = 3): string {
  if (!isNum(v)) return v === null || v === undefined ? "—" : String(v);
  return v.toFixed(d);
}

export function signed(v: unknown, d = 3): string {
  if (!isNum(v)) return "—";
  return (v > 0 ? "+" : v < 0 ? "−" : "") + Math.abs(v).toFixed(d);
}

export function range(r: unknown, d = 3): string {
  if (Array.isArray(r) && r.length === 2 && isNum(r[0]) && isNum(r[1])) return `${r[0].toFixed(d)} – ${r[1].toFixed(d)}`;
  return "—";
}

export function mean(xs: number[]): number | null {
  const v = xs.filter(isNum);
  return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null;
}

export function int(v: unknown): string {
  return isNum(v) ? Math.round(v).toLocaleString("en-US") : "—";
}

export const PRIOR_LABEL: Record<string, string> = {
  corum: "CORUM",
  complexportal: "Complex Portal",
  string_exp: "STRING (experimental)",
  string: "STRING (combined)",
  knn: "kNN",
  mean: "mean",
  hvp: "HVP (top variance)",
  random_mean: "random (mean)",
  random: "random",
  own_null_mean: "own shuffled nulls (mean)",
};
export const label = (k: string) => PRIOR_LABEL[k] ?? k;
