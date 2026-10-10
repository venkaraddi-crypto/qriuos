"use client";
import { useState } from "react";
import { post } from "@/lib/api";
import { LANGUAGES } from "@/lib/i18n";
import { IconLock } from "@/components/icons";

const ITEMS: { key: string; label: string; required: boolean }[] = [
  { key: "store_history", label: "Store my answers in my hospital case file", required: true },
  { key: "share_with_doctor", label: "Share them with the doctor I am seeing", required: true },
  { key: "voice_processing", label: "Process my voice (if I use the microphone) to transcribe my answers", required: true },
  { key: "research_anonymised", label: "Allow anonymised use for improving the service (optional)", required: false },
];

export default function ConsentGate({ appointmentId, onStarted }: { appointmentId: number; onStarted: () => void }) {
  const [checked, setChecked] = useState<Record<string, boolean>>({});
  const [lang, setLang] = useState("en-IN");
  const [err, setErr] = useState<string | null>(null);
  const ready = ITEMS.filter((i) => i.required).every((i) => checked[i.key]);

  const begin = async () => {
    setErr(null);
    try {
      const items: Record<string, boolean> = {};
      ITEMS.forEach((i) => { if (i.required || checked[i.key]) items[i.key] = Boolean(checked[i.key]); });
      await post(`/intake/${appointmentId}/start`, { language: lang, consent_items: items });
      onStarted();
    } catch (e) { setErr((e as Error).message); }
  };

  return (
    <section className="card space-y-3">
      <h2 className="serif flex items-center gap-2 text-xl"><IconLock size={20} /> Before we begin</h2>
      <p className="text-sm muted">This pre-consultation assistant collects your history so the doctor can spend more time with you. You can withdraw consent at any time.</p>
      <label className="block text-sm"><span className="label">Preferred language</span>
        <select className="input w-auto" value={lang} onChange={(e) => setLang(e.target.value)}>{LANGUAGES.map((l) => <option key={l.code} value={l.code}>{l.native}</option>)}</select></label>
      <ul className="space-y-1 text-sm">
        {ITEMS.map((i) => (
          <li key={i.key}><label className="flex items-start gap-2"><input type="checkbox" className="mt-1" checked={Boolean(checked[i.key])} onChange={(e) => setChecked({ ...checked, [i.key]: e.target.checked })} /> <span>{i.label}{i.required && <span className="muted"> *</span>}</span></label></li>
        ))}
      </ul>
      {err && <p className="text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
      <button className="btn-primary" disabled={!ready} onClick={begin}>Begin</button>
    </section>
  );
}
