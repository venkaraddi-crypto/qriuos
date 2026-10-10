"use client";
import { useCallback, useEffect, useState } from "react";
import { get, post, put } from "@/lib/api";
import { IconSpeaker } from "@/components/icons";

interface Q { key: string; type: "text" | "scale" | "choice"; prompt: string; options: string[]; target: string }
interface Batch { category: string; questions: Q[]; remaining: number; complete: boolean }

export default function AdaptiveHistory({ appointmentId, onDone }: { appointmentId: number; onDone: () => void }) {
  const [batch, setBatch] = useState<Batch | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [voiceNote, setVoiceNote] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(() => get<Batch>(`/intake/${appointmentId}/adaptive-questions`).then((b) => { setBatch(b); setAnswers({}); if (b.complete) onDone(); }).catch((e) => setErr(e.message)), [appointmentId, onDone]);
  useEffect(() => { void load(); }, [load]);

  const save = async () => {
    const filled = Object.fromEntries(Object.entries(answers).filter(([, v]) => v.trim()));
    if (Object.keys(filled).length === 0) { setErr("Answer at least one question or skip."); return; }
    setErr(null);
    try { await put(`/intake/${appointmentId}/hpi`, { answers: filled }); await load(); } catch (e) { setErr((e as Error).message); }
  };
  const skip = async () => {
    const skipped = Object.fromEntries((batch?.questions || []).map((q) => [q.key, answers[q.key]?.trim() || "not answered"]));
    try { await put(`/intake/${appointmentId}/hpi`, { answers: skipped }); await load(); } catch (e) { setErr((e as Error).message); }
  };
  const speak = async (text: string) => {
    setVoiceNote(null);
    try {
      const r = await post<{ audio_base64: string | null; mocked: boolean }>("/voice/tts", { text, language: "en-IN" });
      if (r.audio_base64) void new Audio(`data:audio/wav;base64,${r.audio_base64}`).play();
      else setVoiceNote("Voice unavailable (mock)");
    } catch (e) { setVoiceNote((e as Error).message); }
  };

  if (!batch) return <p className="muted">Loading questions…</p>;
  if (batch.complete) return <section className="card"><p className="text-sm" style={{ color: "#4A6B3A" }}>History complete.</p></section>;
  return (
    <section className="card space-y-4">
      <p className="text-xs muted">Category <span className="badge">{batch.category}</span> · {batch.remaining} question(s) left</p>
      {batch.questions.map((q) => (
        <div key={q.key} className="space-y-1">
          <p className="flex items-center gap-2 text-sm font-medium">{q.prompt}
            <button className="btn-ghost px-1 py-0.5" onClick={() => speak(q.prompt)} aria-label="Read aloud"><IconSpeaker size={14} /></button></p>
          {q.type === "text" && <input className="input" value={answers[q.key] || ""} onChange={(e) => setAnswers({ ...answers, [q.key]: e.target.value })} />}
          {q.type === "scale" && <div className="flex flex-wrap gap-1">{q.options.map((o) => <button key={o} className={`badge mono ${answers[q.key] === o ? "badge-amber" : ""}`} onClick={() => setAnswers({ ...answers, [q.key]: o })}>{o}</button>)}</div>}
          {q.type === "choice" && <div className="flex flex-wrap gap-1">{q.options.map((o) => <button key={o} className={`badge ${answers[q.key] === o ? "badge-amber" : ""}`} onClick={() => setAnswers({ ...answers, [q.key]: o })}>{o}</button>)}</div>}
        </div>
      ))}
      {voiceNote && <p className="text-xs muted">{voiceNote}</p>}
      {err && <p className="text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
      <div className="flex gap-2"><button className="btn-primary" onClick={save}>Save & continue</button><button className="btn-ghost" onClick={skip}>Skip these</button></div>
    </section>
  );
}
