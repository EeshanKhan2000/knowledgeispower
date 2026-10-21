import { L } from "@/lib/glossary-server";

function Grid({ gaps, fill }: { gaps: boolean; fill?: boolean }) {
  const cells = [];
  const missing = new Set(["0-2", "1-0", "1-3", "2-1", "3-2", "3-4", "0-4", "2-3"]);
  for (let r = 0; r < 4; r++)
    for (let c = 0; c < 5; c++) {
      const k = `${r}-${c}`;
      const isMiss = missing.has(k);
      cells.push(
        <rect
          key={k}
          x={c * 18 + 2}
          y={r * 18 + 2}
          width={14}
          height={14}
          rx={3}
          fill={isMiss && gaps ? "none" : isMiss && fill ? "var(--s2)" : "var(--s1)"}
          stroke={isMiss && gaps ? "var(--muted)" : "none"}
          strokeDasharray={isMiss && gaps ? "2 2" : undefined}
          opacity={isMiss || !fill ? 1 : 0.55}
        />,
      );
    }
  return (
    <svg viewBox="0 0 94 76" className="h-20 w-24" aria-hidden="true">
      {cells}
    </svg>
  );
}

function GraphIcon() {
  const nodes = [
    [15, 15], [45, 10], [30, 40], [70, 30], [80, 62], [50, 64], [15, 62],
  ];
  const edges = [[0, 1], [1, 2], [0, 2], [3, 4], [4, 5], [3, 5], [2, 6]];
  return (
    <svg viewBox="0 0 94 76" className="h-20 w-24" aria-hidden="true">
      {edges.map(([a, b], i) => (
        <line key={i} x1={nodes[a][0]} y1={nodes[a][1]} x2={nodes[b][0]} y2={nodes[b][1]} stroke="var(--muted)" strokeWidth={2} />
      ))}
      {nodes.map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r={7} fill={i < 3 ? "var(--s1)" : i < 6 ? "var(--s3)" : "var(--s7)"} stroke="var(--surface)" strokeWidth={2} />
      ))}
    </svg>
  );
}

const STEPS = [
  { title: "1. Measure", icon: <Grid gaps />, text: "Mass spectrometry measures thousands of proteins in each single cell, but many values come back missing." },
  { title: "2. Prior graph", icon: <GraphIcon />, text: "Curated complex databases (CORUM, Complex Portal) say which proteins are built into the same machine. That becomes a graph." },
  { title: "3. Reconstruct", icon: <Grid gaps={false} fill />, text: "A missing protein is estimated from its observed partners in the same cell, then checked against values we hid on purpose." },
];

export function StepDiagram() {
  return (
    <ol className="mt-3 flex flex-col items-stretch gap-2 md:flex-row md:items-center">
      {STEPS.map((s, i) => (
        <li key={s.title} className="contents">
          <div className="card flex flex-1 items-start gap-3 md:flex-col md:items-center md:text-center">
            <div className="shrink-0">{s.icon}</div>
            <div>
              <div className="font-semibold text-ink">{s.title}</div>
              <p className="mt-1 text-sm text-ink2">
                <L>{s.text}</L>
              </p>
            </div>
          </div>
          {i < STEPS.length - 1 && (
            <div aria-hidden="true" className="self-center text-2xl text-muted md:rotate-0">
              <span className="md:hidden">↓</span>
              <span className="hidden md:inline">→</span>
            </div>
          )}
        </li>
      ))}
    </ol>
  );
}
