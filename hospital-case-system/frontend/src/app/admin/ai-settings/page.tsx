"use client";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { del, get, post } from "@/lib/api";

interface Provider { id: number; provider: string; capability: string; api_key_masked: string; is_active: boolean; added_at: string }
interface Status {
  capabilities: Record<string, { provider: string; key_source: string | null; model: string }>;
  local: { ollama_model: string | null; ollama_available: boolean; whisper_available: boolean; whisper_error: string | null };
  env_key_present: boolean; stt_language_default: string;
}
const CAPS = ["STT", "DIARIZED_STT", "TRANSLATE", "CHAT", "TTS", "OCR"];
const CAP_LABEL: Record<string, string> = { STT: "Speech-to-text (Saaras)", DIARIZED_STT: "Diarized STT (batch)", TRANSLATE: "Translation (Mayura)", CHAT: "SOAP drafting (Sarvam-M)", TTS: "Text-to-speech (Bulbul)", OCR: "Document OCR (Vision)" };

export default function AiSettings() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [status, setStatus] = useState<Status | null>(null);
  const [cap, setCap] = useState("STT");
  const [key, setKey] = useState("");
  const [test, setTest] = useState<Record<string, string>>({});
  const [err, setErr] = useState<string | null>(null);

  const load = () => {
    get<Provider[]>("/admin/ai-providers").then(setProviders).catch((e) => setErr(e.message));
    get<Status>("/admin/ai-status").then(setStatus).catch(() => {});
  };
  useEffect(load, []);

  const add = async (e: React.FormEvent) => {
    e.preventDefault(); setErr(null);
    try { await post("/admin/ai-providers", { provider: "sarvam", capability: cap, api_key: key }); setKey(""); load(); } catch (ex) { setErr((ex as Error).message); }
  };
  const runTest = async (c: string) => {
    const r = await post<{ ok: boolean; reason?: string; detail?: string; status_code?: number }>("/admin/ai-providers/test", { capability: c });
    setTest({ ...test, [c]: r.ok ? "Reachable" : r.reason || r.detail || `HTTP ${r.status_code}` });
  };

  return (
    <Shell portal="staff" title="AI settings">
      {err && <p className="mb-2 text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
      <div className="grid gap-4 md:grid-cols-[1fr_2fr]">
        <form onSubmit={add} className="card space-y-2">
          <h3 className="serif">Add Sarvam key</h3>
          <p className="text-xs muted">Keys are encrypted at rest and never returned in full. An admin key overrides the .env key per capability.</p>
          <select className="input" value={cap} onChange={(e) => setCap(e.target.value)}>{CAPS.map((c) => <option key={c} value={c}>{CAP_LABEL[c]}</option>)}</select>
          <input className="input mono" type="password" placeholder="API subscription key" value={key} onChange={(e) => setKey(e.target.value)} required minLength={8} />
          <button className="btn-primary">Save key</button>
          {status && (
            <div className="pt-2 text-xs muted">
              <p>.env SARVAM_API_KEY: {status.env_key_present ? "present" : "not set"}</p>
              <p>Ollama: {status.local.ollama_available ? status.local.ollama_model : "not running"}</p>
              <p>Whisper: {status.local.whisper_available ? "available" : status.local.whisper_error || "not installed"}</p>
            </div>
          )}
        </form>
        <section className="card">
          <h3 className="serif">Capability status</h3>
          <table className="mt-2 w-full text-sm">
            <thead><tr className="border-b hr text-left"><th className="py-1">Capability</th><th>Engine</th><th>Key source</th><th>Model</th><th></th></tr></thead>
            <tbody>
              {CAPS.map((c) => {
                const s = status?.capabilities[c];
                return (
                  <tr key={c} className="border-b hr">
                    <td className="py-1">{CAP_LABEL[c]}</td>
                    <td><span className={`badge ${s?.provider === "sarvam" ? "badge-green" : "badge-amber"}`}>{s?.provider || "…"}</span></td>
                    <td className="mono">{s?.key_source || "—"}</td>
                    <td className="mono muted">{s?.model}</td>
                    <td><button className="btn-ghost px-2 py-0.5 text-xs" onClick={() => runTest(c)}>Test</button> <span className="text-xs muted">{test[c]}</span></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <h3 className="serif mt-4">Stored keys</h3>
          <ul className="text-sm">
            {providers.length === 0 && <li className="muted">No admin keys stored.</li>}
            {providers.map((p) => (
              <li key={p.id} className="flex items-center justify-between border-b py-1 hr">
                <span>{p.capability} · <span className="mono">{p.api_key_masked}</span> <span className={`badge ${p.is_active ? "badge-green" : ""}`}>{p.is_active ? "active" : "disabled"}</span></span>
                {p.is_active && <button className="btn-ghost px-2 py-0.5 text-xs" onClick={() => del(`/admin/ai-providers/${p.id}`).then(load)}>Disable</button>}
              </li>
            ))}
          </ul>
        </section>
      </div>
    </Shell>
  );
}
