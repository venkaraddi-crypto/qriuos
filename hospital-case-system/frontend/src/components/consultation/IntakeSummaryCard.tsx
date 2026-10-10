"use client";
import type { IntakeSummary } from "./types";

const HPI_LABELS: Record<string, string> = {
  site: "Site", onset: "Onset", character: "Character", radiation: "Radiation", associations: "Associations",
  timing: "Timing", exacerbating_factors: "Worse with", relieving_factors: "Better with", severity: "Severity",
};

export default function IntakeSummaryCard({ summary }: { summary: IntakeSummary | null }) {
  if (!summary || (!summary.intake_status && summary.chief_complaints.length === 0)) {
    return (
      <section className="card text-sm muted">No pre-consult intake was submitted for this visit.</section>
    );
  }
  const hpi = Object.entries(summary.hpi);
  return (
    <section className="card space-y-3" style={{ borderColor: "#4A6B3A", background: "#EDF3E6" }}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="serif text-lg" style={{ color: "#4A6B3A" }}>Patient-reported intake</h3>
        <p className="text-xs muted">
          {summary.intake_status} · {summary.language_used || "—"} · {summary.duration_sec != null ? `${Math.round(summary.duration_sec / 60)} min` : ""}
        </p>
      </div>
      {summary.chief_complaints.length > 0 && (
        <ul className="list-disc pl-5 text-sm">
          {summary.chief_complaints.map((c, i) => (
            <li key={i}>
              {c.complaint_text}
              {c.duration_days != null && <span className="muted"> · {c.duration_days} d</span>}
              {c.severity != null && <span className="mono muted"> · {c.severity}/10</span>}
            </li>
          ))}
        </ul>
      )}
      {hpi.length > 0 && (
        <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm md:grid-cols-3">
          {hpi.map(([k, v]) => (
            <div key={k}><dt className="label">{HPI_LABELS[k] || k}</dt><dd>{v}</dd></div>
          ))}
        </dl>
      )}
      <div className="grid gap-3 text-sm md:grid-cols-3">
        <div>
          <p className="label">Allergies</p>
          {summary.allergies.length === 0 ? <p className="muted">None reported</p> : summary.allergies.map((a, i) => (
            <p key={i}><span className="badge badge-red">{a.substance}</span> {a.reaction || ""} {a.severity ? `(${a.severity})` : ""}</p>
          ))}
        </div>
        <div>
          <p className="label">Current medications</p>
          {summary.current_meds.length === 0 ? <p className="muted">None reported</p> : summary.current_meds.map((m, i) => (
            <p key={i}>{m.name} <span className="muted">{m.dose || ""} {m.frequency || ""}</span></p>
          ))}
        </div>
        <div>
          <p className="label">Past history</p>
          {summary.past.length === 0 ? <p className="muted">None reported</p> : summary.past.map((p, i) => (
            <p key={i}><span className="badge">{p.kind}</span> {p.text} {p.year ? <span className="mono muted">{p.year}</span> : null}</p>
          ))}
        </div>
      </div>
      {summary.ros.some((r) => r.positive) && (
        <div className="flex flex-wrap items-center gap-1 text-sm">
          <span className="label mb-0">Positive ROS</span>
          {summary.ros.filter((r) => r.positive).map((r) => (
            <span key={r.system} className="badge badge-amber">{r.system}{r.notes ? `: ${r.notes}` : ""}</span>
          ))}
        </div>
      )}
    </section>
  );
}
