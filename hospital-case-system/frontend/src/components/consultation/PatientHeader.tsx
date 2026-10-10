"use client";
import Link from "next/link";
import { useState } from "react";
import { get } from "@/lib/api";
import { IconAlert } from "@/components/icons";
import type { Encounter, TimelineEntry } from "./types";

export default function PatientHeader({ encounter, redFlags }: { encounter: Encounter; redFlags: string[] }) {
  const [timeline, setTimeline] = useState<TimelineEntry[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const p = encounter.patient;
  const isAyu = encounter.system === "AYURVEDA";

  const loadPrior = async () => {
    try {
      setTimeline(await get<TimelineEntry[]>(`/patients/${p.id}/timeline`));
    } catch (e) {
      setErr((e as Error).message);
    }
  };

  return (
    <section className={`card ${isAyu ? "tint-ayu" : "tint-allo"} space-y-2`}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="serif text-2xl">{p.name}</h2>
          <p className="text-sm muted">
            <span className="mono">{p.uhid}</span> · {p.gender || "—"} · {p.age != null ? `${p.age} y` : "age —"}
            {p.abha_id && <> · ABHA <span className="mono">{p.abha_id}</span></>}
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <span className="badge">{encounter.system || "—"}</span>
          <span>Token <span className="mono text-xl">{encounter.token_number ?? "—"}</span></span>
          <button className="btn-ghost" onClick={loadPrior}>Prior visits</button>
          <Link className="btn-ghost" href={`/case-file/${p.id}`}>Open case file</Link>
        </div>
      </div>
      {(encounter.red_flag || redFlags.length > 0) && (
        <div className="flex items-center gap-2 rounded-sm border px-3 py-2 text-sm" style={{ borderColor: "#A03A2A", background: "#F9E9E4", color: "#A03A2A" }}>
          <IconAlert size={18} /> Red flag{redFlags.length > 0 ? `: ${redFlags.join(", ")}` : " raised at booking"}
        </div>
      )}
      {err && <p className="text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
      {timeline && (
        <div className="border-t pt-2 hr">
          <p className="label">Prior visits</p>
          {timeline.filter((t) => t.encounter_id !== encounter.id).length === 0 && <p className="text-sm muted">No earlier encounters.</p>}
          <ul className="space-y-1 text-sm">
            {timeline.filter((t) => t.encounter_id !== encounter.id).map((t) => (
              <li key={t.encounter_id} className="flex flex-wrap gap-2">
                <span className="mono">{t.date.slice(0, 10)}</span>
                <span className="badge">{t.system}</span>
                <span>{t.summary || t.chief_complaint || "—"}</span>
                {t.diagnoses.length > 0 && <span className="muted">({t.diagnoses.join(", ")})</span>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
