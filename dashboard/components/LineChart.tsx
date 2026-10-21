// Inline SVG line chart built from data at build time (no chart library).
import { label } from "@/lib/format";

export type Series = { key: string; points: { x: number; y: number | null }[]; dashed?: boolean; color: string; name: string };

const COLOR: Record<string, string> = {
  corum: "var(--s1)",
  complexportal: "var(--s2)",
  string_exp: "var(--s3)",
  string: "var(--s7)",
  hvp: "var(--ink-2)",
  random_mean: "var(--muted)",
  random: "var(--muted)",
};
let extraIdx = 0;
const EXTRA = ["var(--s5)", "var(--s6)", "var(--s8)", "var(--s4)"];
export function colorFor(k: string): string {
  if (!COLOR[k]) COLOR[k] = EXTRA[extraIdx++ % EXTRA.length];
  return COLOR[k];
}

export function LineChart({ title, series, xs, yLabel }: { title: string; series: Series[]; xs: number[]; yLabel: string }) {
  const W = 340;
  const H = 220;
  const m = { l: 40, r: 12, t: 14, b: 30 };
  const ys = series.flatMap((s) => s.points.map((p) => p.y)).filter((v): v is number => v !== null);
  if (!ys.length || !xs.length) return null;
  let lo = Math.min(0, ...ys);
  let hi = Math.max(...ys);
  const step = niceStep((hi - lo) / 4);
  lo = Math.floor(lo / step) * step;
  hi = Math.ceil(hi / step) * step;
  if (hi === lo) hi = lo + step;
  const sx = (i: number) => m.l + (xs.length === 1 ? (W - m.l - m.r) / 2 : (i * (W - m.l - m.r)) / (xs.length - 1));
  const sy = (v: number) => m.t + ((hi - v) * (H - m.t - m.b)) / (hi - lo);
  const ticks: number[] = [];
  for (let v = lo; v <= hi + step / 2; v += step) ticks.push(+v.toFixed(6));
  return (
    <figure className="card">
      <figcaption className="text-sm font-semibold text-ink">{title}</figcaption>
      <svg viewBox={`0 0 ${W} ${H}`} className="mt-2 w-full" role="img" aria-label={`${title}: ${yLabel} by k`}>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={m.l} x2={W - m.r} y1={sy(t)} y2={sy(t)} stroke="var(--grid)" strokeWidth={1} />
            <text x={m.l - 6} y={sy(t) + 3} textAnchor="end" fontSize={10} fill="var(--muted)">
              {t.toFixed(step < 0.1 ? 2 : 1)}
            </text>
          </g>
        ))}
        {xs.map((x, i) => (
          <text key={x} x={sx(i)} y={H - m.b + 16} textAnchor="middle" fontSize={10} fill="var(--muted)">
            k = {x}
          </text>
        ))}
        {series.map((s) => {
          const pts = s.points.map((p, i) => (p.y === null ? null : ([sx(i), sy(p.y)] as const)));
          const d = pts
            .map((p, i) => (p ? `${i === 0 || !pts[i - 1] ? "M" : "L"}${p[0].toFixed(1)},${p[1].toFixed(1)}` : ""))
            .join("");
          return (
            <g key={s.key}>
              <path d={d} fill="none" stroke={s.color} strokeWidth={2} strokeDasharray={s.dashed ? "5 4" : undefined} strokeLinejoin="round" />
              {pts.map((p, i) =>
                p ? (
                  <g key={i}>
                    <circle cx={p[0]} cy={p[1]} r={s.dashed ? 3 : 4} fill={s.dashed ? "var(--surface)" : s.color} stroke={s.dashed ? s.color : "var(--surface)"} strokeWidth={2} />
                    <circle cx={p[0]} cy={p[1]} r={10} fill="transparent">
                      <title>{`${s.name}, k = ${xs[i]}: ${s.points[i].y!.toFixed(3)}`}</title>
                    </circle>
                  </g>
                ) : null,
              )}
            </g>
          );
        })}
      </svg>
      <ul className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-ink2">
        {series.map((s) => (
          <li key={s.key} className="flex items-center gap-1">
            <svg width="20" height="8" aria-hidden="true">
              <line x1="0" x2="20" y1="4" y2="4" stroke={s.color} strokeWidth={2} strokeDasharray={s.dashed ? "4 3" : undefined} />
            </svg>
            {s.name}
          </li>
        ))}
      </ul>
    </figure>
  );
}

function niceStep(raw: number): number {
  if (!(raw > 0)) return 0.1;
  const p = Math.pow(10, Math.floor(Math.log10(raw)));
  const n = raw / p;
  return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * p;
}

export const seriesName = (k: string, isNull: boolean) => (isNull ? `${label(k)} nulls (mean)` : label(k));
