import { P } from "@/lib/glossary-server";

export const metadata = { title: "Mechanism · Complex priors" };

function Fig({ children, caption }: { children: React.ReactNode; caption: string }) {
  return (
    <figure className="card my-4">
      <div className="flex justify-center overflow-hidden">{children}</div>
      <figcaption className="mt-2 text-center text-xs text-muted">{caption}</figcaption>
    </figure>
  );
}

function Machine() {
  // A stylised proteasome: stacked rings of subunits plus a lid.
  const ring = (y: number, color: string) =>
    Array.from({ length: 7 }, (_, i) => <rect key={`${y}-${i}`} x={60 + i * 26} y={y} width={22} height={18} rx={6} fill={color} />);
  return (
    <svg viewBox="0 0 300 150" className="w-full max-w-sm" role="img" aria-label="A protein machine drawn as stacked rings of subunits">
      <rect x={70} y={8} width={160} height={22} rx={10} fill="var(--s7)" />
      <text x={150} y={23} textAnchor="middle" fontSize={11} fill="#fff">lid / cap</text>
      {ring(36, "var(--s3)")}
      {ring(58, "var(--s1)")}
      {ring(80, "var(--s1)")}
      {ring(102, "var(--s3)")}
      <text x={12} y={50} fontSize={10} fill="var(--muted)">α ring</text>
      <text x={12} y={80} fontSize={10} fill="var(--muted)">β rings</text>
      <text x={12} y={116} fontSize={10} fill="var(--muted)">α ring</text>
      <text x={150} y={142} textAnchor="middle" fontSize={11} fill="var(--ink-2)">each block is a separate protein (subunit)</text>
    </svg>
  );
}

function Stoich() {
  const part = (x: number, y: number, c: string, k: string) => <rect key={k} x={x} y={y} width={22} height={22} rx={6} fill={c} />;
  return (
    <svg viewBox="0 0 320 120" className="w-full max-w-md" role="img" aria-label="Parts A, B and C combine one-to-one-to-one into a complete complex; an extra A is left over">
      {[0, 1, 2].map((i) => part(10, 10 + i * 28, "var(--s1)", "a" + i))}
      {part(10, 94, "var(--s1)", "a3")}
      {[0, 1, 2].map((i) => part(40, 10 + i * 28, "var(--s2)", "b" + i))}
      {[0, 1, 2].map((i) => part(70, 10 + i * 28, "var(--s3)", "c" + i))}
      <text x={20} y={118} fontSize={9} fill="var(--muted)">A</text>
      <text x={50} y={118} fontSize={9} fill="var(--muted)">B</text>
      <text x={80} y={118} fontSize={9} fill="var(--muted)">C</text>
      <path d="M110 50 h40" stroke="var(--muted)" strokeWidth={2} markerEnd="url(#arr)" />
      <defs>
        <marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
          <path d="M0 0 L10 5 L0 10z" fill="var(--muted)" />
        </marker>
      </defs>
      {[0, 1, 2].map((i) => (
        <g key={i} transform={`translate(${165 + i * 50} 30)`}>
          {part(0, 0, "var(--s1)", "x")}
          {part(22, 0, "var(--s2)", "y")}
          {part(11, 22, "var(--s3)", "z")}
        </g>
      ))}
      <text x={240} y={95} textAnchor="middle" fontSize={10} fill="var(--ink-2)">3 complete machines (1 : 1 : 1)</text>
    </svg>
  );
}

function Orphan() {
  return (
    <svg viewBox="0 0 320 100" className="w-full max-w-md" role="img" aria-label="An unpartnered subunit is tagged and broken down into fragments">
      <rect x={10} y={40} width={22} height={22} rx={6} fill="var(--s1)" />
      <text x={21} y={80} textAnchor="middle" fontSize={9} fill="var(--muted)">orphan A</text>
      {[0, 1, 2].map((i) => (
        <circle key={i} cx={40 + i * 8} cy={36} r={3} fill="var(--s4)" />
      ))}
      <text x={52} y={26} fontSize={9} fill="var(--muted)">tags</text>
      <path d="M80 51 h40" stroke="var(--muted)" strokeWidth={2} markerEnd="url(#arr2)" />
      <defs>
        <marker id="arr2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
          <path d="M0 0 L10 5 L0 10z" fill="var(--muted)" />
        </marker>
      </defs>
      <rect x={130} y={30} width={70} height={42} rx={12} fill="var(--s7)" />
      <text x={165} y={55} textAnchor="middle" fontSize={10} fill="#fff">proteasome</text>
      <path d="M210 51 h30" stroke="var(--muted)" strokeWidth={2} markerEnd="url(#arr2)" />
      {[0, 1, 2, 3, 4].map((i) => (
        <rect key={i} x={250 + (i % 3) * 18} y={38 + Math.floor(i / 3) * 16} width={10} height={6} rx={2} fill="var(--s1)" opacity={0.6} />
      ))}
      <text x={275} y={85} textAnchor="middle" fontSize={9} fill="var(--muted)">fragments</text>
    </svg>
  );
}

function CoVary() {
  // Illustration only (not data): two partner proteins rising and falling together across six cells.
  const a = [30, 52, 40, 70, 46, 60];
  const b = [26, 50, 44, 66, 40, 62];
  const c = [50, 30, 64, 38, 58, 34];
  const bar = (v: number, i: number, off: number, col: string) => (
    <rect key={`${col}-${i}`} x={20 + i * 48 + off} y={90 - v} width={10} height={v} rx={2} fill={col} />
  );
  return (
    <svg viewBox="0 0 320 120" className="w-full max-w-md" role="img" aria-label="Illustration: two partner proteins go up and down together across cells; an unrelated protein does not">
      <line x1={14} y1={90} x2={310} y2={90} stroke="var(--line)" />
      {a.map((v, i) => bar(v, i, 0, "var(--s1)"))}
      {b.map((v, i) => bar(v, i, 12, "var(--s2)"))}
      {c.map((v, i) => bar(v, i, 24, "var(--muted)"))}
      {a.map((_, i) => (
        <text key={i} x={36 + i * 48} y={104} textAnchor="middle" fontSize={9} fill="var(--muted)">cell {i + 1}</text>
      ))}
      <rect x={20} y={110} width={8} height={8} fill="var(--s1)" />
      <text x={32} y={117} fontSize={9} fill="var(--ink-2)">subunit A</text>
      <rect x={90} y={110} width={8} height={8} fill="var(--s2)" />
      <text x={102} y={117} fontSize={9} fill="var(--ink-2)">partner B</text>
      <rect x={160} y={110} width={8} height={8} fill="var(--muted)" />
      <text x={172} y={117} fontSize={9} fill="var(--ink-2)">unrelated protein</text>
    </svg>
  );
}

function Infer() {
  return (
    <svg viewBox="0 0 320 130" className="w-full max-w-md" role="img" aria-label="Inside one cell, a missing subunit's value is estimated from its measured partners">
      <rect x={4} y={4} width={312} height={122} rx={40} fill="none" stroke="var(--line)" strokeWidth={2} />
      <text x={30} y={26} fontSize={10} fill="var(--muted)">one cell</text>
      {[
        [90, 50, "high"],
        [150, 30, "high"],
        [210, 50, "high"],
        [150, 95, "?"],
      ].map(([x, y, t], i) => (
        <g key={i}>
          {i < 3 && <line x1={x as number} y1={y as number} x2={150} y2={95} stroke="var(--muted)" strokeWidth={2} />}
          <circle cx={x as number} cy={y as number} r={16} fill={t === "?" ? "var(--surface)" : "var(--s1)"} stroke={t === "?" ? "var(--s2)" : "var(--surface)"} strokeWidth={2} strokeDasharray={t === "?" ? "4 3" : undefined} />
          <text x={x as number} y={(y as number) + 4} textAnchor="middle" fontSize={10} fill={t === "?" ? "var(--ink)" : "#fff"}>{t as string}</text>
        </g>
      ))}
      <text x={230} y={108} fontSize={10} fill="var(--ink-2)">guess: probably high too</text>
    </svg>
  );
}

export default function Mechanism() {
  return (
    <article className="max-w-3xl">
      <h1 className="h1">Mechanism: from molecule to model</h1>
      <P>
        This page explains why a list of protein complexes could help fill in missing measurements. Each step is a piece of
        biology; together they give a reason to expect the method to work. Whether it actually works on real data is a separate
        question, answered on the Results page.
      </P>

      <h2 className="h2">1. Cells run on protein machines</h2>
      <P>
        Many proteins do not work alone. They lock together into a protein complex, a machine with a fixed set of parts. The
        proteasome, which shreds proteins the cell no longer needs, is built from dozens of different subunits arranged in
        stacked rings. The ribosome, which builds new proteins, is made of around eighty proteins plus RNA.
      </P>
      <Fig caption="Stylised proteasome: every block is a separate protein chain.">
        <Machine />
      </Fig>

      <h2 className="h2">2. Machines are built in fixed ratios</h2>
      <P>
        A bicycle needs two wheels per frame; a complex needs its subunits in a set ratio. This ratio is called stoichiometry.
        If a cell makes extra copies of one subunit, the extras have nothing to bind to.
      </P>
      <Fig caption="Parts A, B and C combine 1 : 1 : 1. A fourth copy of A has no partners.">
        <Stoich />
      </Fig>

      <h2 className="h2">3. Leftover parts are destroyed</h2>
      <P>
        An unpartnered subunit is often unstable. The cell tags it and sends it to the proteasome. This is called orphan-subunit
        degradation. The result is that the amount of each subunit that survives tends to track the amount of the finished
        machine.
      </P>
      <Fig caption="An orphan subunit is tagged, then broken down by the proteasome.">
        <Orphan />
      </Fig>

      <h2 className="h2">4. Partners rise and fall together</h2>
      <P>
        Because of fixed ratios and orphan degradation, subunits of the same complex should co-vary at the protein level: a cell
        with more of one subunit usually has more of its partners. This can hold even when the RNA messages for those subunits
        do not track each other well, which is why the project works with protein measurements, not RNA.
      </P>
      <Fig caption="Illustration, not data: A and B move together across cells; the unrelated protein does not.">
        <CoVary />
      </Fig>

      <h2 className="h2">5. A missing value can be estimated from partners</h2>
      <P>
        Single-cell proteomics measures proteins in one cell at a time using mass spectrometry. Each cell holds very little
        material, so many values are missing. If a subunit is missing in one cell but its partners were measured in that same
        cell, the partners carry information about it. The imputation method used here converts each partner to a z-score,
        averages them, and scales the average by a single fitted factor.
      </P>
      <Fig caption="Inside one cell: measured partners are high, so the missing partner is probably high too.">
        <Infer />
      </Fig>

      <h2 className="h2">6. The complex list is a prior, and it must beat a fake one</h2>
      <P>
        The list of complexes comes from curated databases (CORUM and the EBI Complex Portal), assembled by experts from many
        earlier experiments. It is not learned from the dataset being reconstructed, so it acts as a prior: knowledge brought in
        from outside. Turned into a graph, each protein is a node and an edge joins two proteins that share a curated complex.
      </P>
      <P>
        A fair test compares this graph against three things: methods that use the data alone (such as kNN), a generic
        protein-interaction network (STRING), and a degree-preserving shuffle of the same graph, which keeps how many partners
        each protein has but scrambles who they are. If the real graph does no better than its shuffled null, the benefit
        cannot come from the biology of the complexes.
      </P>
    </article>
  );
}
