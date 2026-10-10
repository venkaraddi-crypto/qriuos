"use client";
import type { SocratesEntities } from "./types";

const ROWS: { key: keyof SocratesEntities; label: string }[] = [
  { key: "chief_complaint", label: "Chief complaint" },
  { key: "site", label: "Site" },
  { key: "onset", label: "Onset" },
  { key: "character", label: "Character" },
  { key: "radiation", label: "Radiation" },
  { key: "associations", label: "Associations" },
  { key: "timing", label: "Timing" },
  { key: "exacerbating_factors", label: "Exacerbating" },
  { key: "relieving_factors", label: "Relieving" },
  { key: "severity", label: "Severity" },
];

function show(v: unknown): string {
  if (v === null || v === undefined || v === "") return "—";
  if (Array.isArray(v)) return v.length ? v.join(", ") : "—";
  return String(v);
}

export default function SocratesCard({ entities }: { entities: SocratesEntities | null }) {
  if (!entities) return null;
  return (
    <section className="card">
      <div className="flex items-center justify-between">
        <h3 className="serif text-lg">SOCRATES</h3>
        {entities.mocked && <span className="badge badge-amber">rule-based extractor</span>}
      </div>
      <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
        {ROWS.map((r) => (
          <div key={r.key} className="contents">
            <dt className="muted">{r.label}</dt>
            <dd className={r.key === "severity" ? "mono" : ""}>{r.key === "severity" && entities.severity != null ? `${entities.severity}/10` : show(entities[r.key])}</dd>
          </div>
        ))}
        {entities.duration && (<div className="contents"><dt className="muted">Duration</dt><dd>{entities.duration}</dd></div>)}
      </dl>
      {entities.red_flags.length > 0 && (
        <p className="mt-2 text-sm"><span className="badge badge-red">RED FLAGS</span> {entities.red_flags.join(", ")}</p>
      )}
    </section>
  );
}
