"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { get, post } from "@/lib/api";
import { IconPrint } from "@/components/icons";
import type { Encounter } from "@/components/consultation/types";

interface Discharge { id: number; summary_text: string | null; instructions: string | null; follow_up_date: string | null; fhir_bundle_id: string | null }

export default function DischargePage() {
  const { id } = useParams<{ id: string }>();
  const [enc, setEnc] = useState<Encounter | null>(null);
  const [existing, setExisting] = useState<Discharge | null>(null);
  const [instructions, setInstructions] = useState("");
  const [followUp, setFollowUp] = useState("");
  const [summaryText, setSummaryText] = useState("");
  const [abha, setAbha] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    get<Encounter>(`/encounters/${id}`).then((e) => { setEnc(e); setSummaryText(e.summary || ""); setAbha(e.abha_care_context_ref); }).catch((e) => setErr(e.message));
    get<Discharge>(`/discharge/${id}`).then(setExisting).catch(() => {});
  }, [id]);

  const discharge = async () => {
    setErr(null);
    try {
      const d = await post<Discharge>(`/discharge/${id}`, { instructions, follow_up_date: followUp || null, summary_text: summaryText || null });
      setExisting(d);
    } catch (e) { setErr((e as Error).message); }
  };
  const linkAbha = async () => {
    try { const r = await post<{ care_context_ref: string }>("/abha/link-care-context", { encounter_id: Number(id) }); setAbha(r.care_context_ref); } catch (e) { setErr((e as Error).message); }
  };

  return (
    <Shell portal="staff" title="Discharge summary" tint={enc?.system === "AYURVEDA" ? "ayu" : "allo"}>
      {err && <p className="mb-3 text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
      {enc && (
        <div className="mx-auto max-w-2xl space-y-4">
          <section className="card">
            <h2 className="serif text-xl">{enc.patient.name} <span className="mono text-sm muted">{enc.patient.uhid}</span></h2>
            <p className="text-sm muted">Encounter #{enc.id} · {enc.timestamp.slice(0, 10)} · Token {enc.token_number}</p>
            {enc.diagnoses.length > 0 && <p className="mt-1 text-sm">{enc.diagnoses.map((d) => `${d.display_term} [${d.code}]`).join("; ")}</p>}
          </section>
          {!existing ? (
            <section className="card space-y-3">
              <label className="block text-sm"><span className="label">Summary</span><textarea className="input" rows={3} value={summaryText} onChange={(e) => setSummaryText(e.target.value)} /></label>
              <label className="block text-sm"><span className="label">Instructions (Pathya–Apathya, diet, activity)</span><textarea className="input" rows={4} value={instructions} onChange={(e) => setInstructions(e.target.value)} /></label>
              <label className="block text-sm"><span className="label">Follow-up date</span><input className="input w-auto" type="date" value={followUp} onChange={(e) => setFollowUp(e.target.value)} /></label>
              <button className="btn-primary" onClick={discharge}>Complete consultation & generate FHIR</button>
            </section>
          ) : (
            <section className="card space-y-2">
              <div className="flex items-center justify-between no-print">
                <span className="badge badge-green">Discharged</span>
                <div className="flex gap-2">
                  <button className="btn-ghost" onClick={() => window.print()}><IconPrint size={14} /> Print</button>
                  <Link className="btn-ghost" href="/doctor/queue">Back to queue</Link>
                </div>
              </div>
              <h3 className="serif text-lg">Summary</h3><p className="text-sm">{existing.summary_text || "—"}</p>
              <h3 className="serif text-lg">Instructions</h3><p className="text-sm whitespace-pre-wrap">{existing.instructions || "—"}</p>
              <p className="text-sm">Follow-up: <span className="mono">{existing.follow_up_date || "—"}</span></p>
              <p className="mono text-xs muted">FHIR bundle {existing.fhir_bundle_id}</p>
              <div className="flex items-center gap-2 text-sm no-print">
                {abha ? <span className="badge badge-green">ABHA care context {abha}</span> : <button className="btn-ghost" onClick={linkAbha}>Link ABHA care context (mock)</button>}
              </div>
            </section>
          )}
        </div>
      )}
    </Shell>
  );
}
