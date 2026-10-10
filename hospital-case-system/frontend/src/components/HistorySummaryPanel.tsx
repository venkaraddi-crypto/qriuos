"use client";
import { useEffect, useState } from "react";
import { get } from "@/lib/api";

interface Summary { problem_representation: string; hpi_lines: string[]; ros_positive: string[]; investigations: string[]; narrative: string }

export default function HistorySummaryPanel({ encId, onInsert }: { encId: number; onInsert: (narrative: string) => void }) {
  const [s, setS] = useState<Summary | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [open, setOpen] = useState(true);

  useEffect(() => { get<Summary>(`/encounters/${encId}/history-summary`).then(setS).catch((e) => setErr(e.message)); }, [encId]);

  if (err) return <p className="text-sm" style={{ color: "#A03A2A" }}>{err}</p>;
  if (!s) return null;
  return (
    <section className="card space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="serif text-lg">Problem representation</h3>
        <div className="flex gap-2">
          <button className="btn-ghost" onClick={() => onInsert(s.narrative)}>Insert into notes</button>
          <button className="btn-ghost" onClick={() => setOpen((o) => !o)}>{open ? "Collapse" : "Expand"}</button>
        </div>
      </div>
      <p className="text-sm">{s.problem_representation}</p>
      {open && (
        <div className="grid gap-2 text-sm md:grid-cols-3">
          <div><p className="label">HPI</p>{s.hpi_lines.length ? <ul className="list-disc pl-4">{s.hpi_lines.map((l) => <li key={l}>{l}</li>)}</ul> : <p className="muted">—</p>}</div>
          <div><p className="label">Positive ROS</p>{s.ros_positive.length ? <p>{s.ros_positive.join(", ")}</p> : <p className="muted">—</p>}</div>
          <div><p className="label">Investigations</p>{s.investigations.length ? <ul className="list-disc pl-4">{s.investigations.map((l) => <li key={l}>{l}</li>)}</ul> : <p className="muted">—</p>}</div>
        </div>
      )}
    </section>
  );
}
