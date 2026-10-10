"use client";
import { useEffect, useRef, useState } from "react";
import { API, getToken, patch, post } from "@/lib/api";
import { IconMic } from "@/components/icons";
import { formatClock } from "./types";

interface Turn { speaker: string; text: string }
interface Draft { id: number; soap_subjective: string; soap_objective: string; soap_assessment: string; soap_plan: string; follow_up_weeks?: number; llm_mocked?: boolean; provider?: string; approved_at?: string | null }
interface Props { encounterId: number; onApproved: () => void; onScheduleFollowUp: (weeks: number) => void }

export default function AmbientScribeCard({ encounterId, onApproved, onScheduleFollowUp }: Props) {
  const [consent, setConsent] = useState(false);
  const [ack, setAck] = useState(false);
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [provider, setProvider] = useState<string | null>(null);
  const [mocked, setMocked] = useState(false);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const recRef = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => () => { if (timer.current) clearInterval(timer.current); }, []);

  const stopUpload = async (blob: Blob) => {
    try {
      const fd = new FormData();
      fd.append("audio_file", blob, "consult.webm");
      const token = getToken();
      const r = await fetch(`${API}/consultation/${encounterId}/stop-recording`, { method: "POST", body: fd, credentials: "include", headers: token ? { Authorization: `Bearer ${token}` } : {} });
      if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
      const j = await r.json();
      setTurns(j.diarized_transcript || []); setProvider(j.provider); setMocked(Boolean(j.mocked));
      if (j.error) setMsg(`Engine note: ${j.error}`);
    } catch (e) { setErr((e as Error).message); }
  };

  const start = async () => {
    setErr(null);
    try {
      await post(`/consultation/${encounterId}/start-recording`, { consent_given: consent, consent_acknowledged_by_patient: ack });
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream);
      chunks.current = [];
      rec.ondataavailable = (e) => chunks.current.push(e.data);
      rec.onstop = () => { stream.getTracks().forEach((t) => t.stop()); void stopUpload(new Blob(chunks.current, { type: rec.mimeType || "audio/webm" })); };
      rec.start();
      recRef.current = rec;
      setRecording(true); setSeconds(0);
      timer.current = setInterval(() => setSeconds((s) => s + 1), 1000);
    } catch (e) { setErr((e as Error).message); }
  };

  const stop = () => { recRef.current?.stop(); setRecording(false); if (timer.current) clearInterval(timer.current); };

  const generate = async () => {
    setErr(null);
    try { setDraft(await post<Draft>(`/consultation/${encounterId}/generate-soap-draft`)); } catch (e) { setErr((e as Error).message); }
  };
  const approve = async () => {
    if (!draft) return;
    try {
      await patch(`/note-drafts/${draft.id}`, { soap_subjective: draft.soap_subjective, soap_objective: draft.soap_objective, soap_assessment: draft.soap_assessment, soap_plan: draft.soap_plan });
      const a = await post<Draft>(`/note-drafts/${draft.id}/approve`);
      setDraft({ ...draft, approved_at: a.approved_at }); setMsg("SOAP note approved and copied to clinical notes."); onApproved();
    } catch (e) { setErr((e as Error).message); }
  };

  const field = (k: "soap_subjective" | "soap_objective" | "soap_assessment" | "soap_plan", label: string) => draft && (
    <label className="block text-sm"><span className="label">{label}</span>
      <textarea className="input" rows={2} value={draft[k] ?? ""} onChange={(e) => setDraft({ ...draft, [k]: e.target.value })} /></label>
  );

  return (
    <section className="card space-y-3">
      <h3 className="serif text-lg flex items-center gap-2"><IconMic size={18} /> Ambient scribe</h3>
      {!recording && turns.length === 0 && (
        <div className="space-y-1 text-sm">
          <label className="flex items-center gap-2"><input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} /> I have explained that this consultation will be recorded and transcribed.</label>
          <label className="flex items-center gap-2"><input type="checkbox" checked={ack} onChange={(e) => setAck(e.target.checked)} /> The patient verbally consented.</label>
          <button className="btn-primary" disabled={!consent || !ack} onClick={start}>Start recording</button>
        </div>
      )}
      {recording && (
        <div className="flex items-center gap-3 text-sm">
          <span className="inline-block h-3 w-3 rounded-full" style={{ background: "#A03A2A", animation: "pulsebar 1s infinite" }} />
          <span className="mono">{formatClock(seconds)}</span>
          <button className="btn-ghost" onClick={stop}>Stop & transcribe</button>
        </div>
      )}
      {turns.length > 0 && (
        <div className="space-y-1 text-sm">
          <p className="text-xs muted">Transcript via {provider}{mocked && <span className="badge badge-amber ml-2">MOCKED</span>}</p>
          <ul className="max-h-48 overflow-y-auto border p-2 hr">{turns.map((t, i) => <li key={i}><strong>{t.speaker}:</strong> {t.text}</li>)}</ul>
          {!draft && <button className="btn-primary" onClick={generate}>Generate SOAP draft</button>}
        </div>
      )}
      {draft && (
        <div className="space-y-2">
          <p className="text-xs muted">Draft via {draft.provider}{draft.llm_mocked && <span className="badge badge-amber ml-2">rule-based</span>}</p>
          {field("soap_subjective", "Subjective")}{field("soap_objective", "Objective")}{field("soap_assessment", "Assessment")}{field("soap_plan", "Plan")}
          <div className="flex flex-wrap gap-2">
            <button className="btn-primary" onClick={approve} disabled={Boolean(draft.approved_at)}>{draft.approved_at ? "Approved" : "Approve & sign"}</button>
            {draft.follow_up_weeks && <button className="btn-ghost" onClick={() => onScheduleFollowUp(draft.follow_up_weeks || 2)}>Schedule follow-up in {draft.follow_up_weeks} wk</button>}
          </div>
        </div>
      )}
      {msg && <p className="text-xs muted">{msg}</p>}
      {err && <p className="text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
    </section>
  );
}
