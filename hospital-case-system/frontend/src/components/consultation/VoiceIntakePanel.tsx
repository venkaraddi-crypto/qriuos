"use client";
import { useEffect, useRef, useState } from "react";
import { API, getToken } from "@/lib/api";
import { IconMic } from "@/components/icons";
import { formatClock, languageLabel, type SttStatus } from "./types";

interface Props {
  sttStatus: SttStatus | null;
  text: string;
  onTextChange: (t: string) => void;
  onExtract: () => void;
}
interface TranscribeResult { provider: string; text: string; language_detected: string | null; key_source: string | null; error?: string; sarvam_error?: string }

const BARS = 24;

export default function VoiceIntakePanel({ sttStatus, text, onTextChange, onExtract }: Props) {
  const [lang, setLang] = useState("unknown");
  const [mode, setMode] = useState("transcribe");
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [levels, setLevels] = useState<number[]>(Array(BARS).fill(0.1));
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const recRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const rafRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => { if (sttStatus?.default_language) setLang(sttStatus.default_language); }, [sttStatus]);
  useEffect(() => () => { cancelAnimationFrame(rafRef.current); if (timerRef.current) clearInterval(timerRef.current); streamRef.current?.getTracks().forEach((t) => t.stop()); }, []);

  const upload = async (blob: Blob) => {
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("audio_file", blob, "intake.webm");
      const token = getToken();
      const r = await fetch(`${API}/voice/transcribe-audio?language_code=${encodeURIComponent(lang)}&mode=${mode}`, { method: "POST", body: fd, credentials: "include", headers: token ? { Authorization: `Bearer ${token}` } : {} });
      if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
      const j = (await r.json()) as TranscribeResult;
      if (j.provider === "none") { setError(j.error || "No speech engine available."); if (j.sarvam_error) setNotice(`Sarvam: ${j.sarvam_error}`); }
      else { onTextChange(text ? `${text}\n${j.text}` : j.text); setNotice(`Transcribed by ${j.provider}${j.language_detected ? ` · ${languageLabel(j.language_detected)}` : ""}${j.key_source ? ` · key: ${j.key_source}` : ""}`); }
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };

  const start = async () => {
    setError(null); setNotice(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const ctx = new AudioContext();
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 64;
      ctx.createMediaStreamSource(stream).connect(analyser);
      const data = new Uint8Array(analyser.frequencyBinCount);
      const loop = () => { analyser.getByteFrequencyData(data); setLevels(Array.from({ length: BARS }, (_, i) => Math.max(0.1, data[i % data.length] / 255))); rafRef.current = requestAnimationFrame(loop); };
      loop();
      const rec = new MediaRecorder(stream);
      chunksRef.current = [];
      rec.ondataavailable = (e) => chunksRef.current.push(e.data);
      rec.onstop = () => { void upload(new Blob(chunksRef.current, { type: rec.mimeType || "audio/webm" })); cancelAnimationFrame(rafRef.current); stream.getTracks().forEach((t) => t.stop()); void ctx.close(); };
      rec.start();
      recRef.current = rec;
      setRecording(true); setSeconds(0);
      timerRef.current = setInterval(() => setSeconds((s) => s + 1), 1000);
    } catch (e) { setError(`Microphone unavailable: ${(e as Error).message}`); }
  };

  const stop = () => { recRef.current?.stop(); setRecording(false); if (timerRef.current) clearInterval(timerRef.current); };

  return (
    <section className="card space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="serif text-lg flex items-center gap-2"><IconMic size={18} /> Voice intake</h3>
        <p className="text-xs muted">{sttStatus ? `${sttStatus.provider} · ${sttStatus.sarvam_model}` : "…"}</p>
      </div>
      {sttStatus && <p className="text-xs muted">{sttStatus.hint}</p>}
      <div className="flex flex-wrap gap-2">
        <select className="input w-auto" value={lang} onChange={(e) => setLang(e.target.value)} aria-label="Language">
          {(sttStatus?.languages || ["unknown", "en-IN", "hi-IN"]).map((l) => <option key={l} value={l}>{languageLabel(l)}</option>)}
        </select>
        <select className="input w-auto" value={mode} onChange={(e) => setMode(e.target.value)} aria-label="Mode">
          {(sttStatus?.modes || ["transcribe", "translate", "codemix"]).map((m) => <option key={m} value={m}>{m}</option>)}
        </select>
        {recording ? <button className="btn-primary" onClick={stop}>Stop · <span className="mono">{formatClock(seconds)}</span></button>
          : <button className="btn-ghost" onClick={start} disabled={busy}><IconMic size={16} /> {busy ? "Transcribing…" : "Record"}</button>}
      </div>
      {recording && <div className="flex h-8 items-end" aria-hidden>{levels.map((l, i) => <span key={i} className="wavebar" style={{ height: `${Math.round(l * 100)}%`, animationDelay: `${i * 30}ms` }} />)}</div>}
      {notice && <p className="text-xs muted">{notice}</p>}
      {error && <p className="text-sm" style={{ color: "#A03A2A" }}>{error}</p>}
      <textarea className="input" rows={4} value={text} onChange={(e) => onTextChange(e.target.value)} placeholder="Transcript appears here — or type the complaint." />
      <button className="btn-primary" onClick={onExtract} disabled={!text.trim()}>Extract SOCRATES entities</button>
    </section>
  );
}
