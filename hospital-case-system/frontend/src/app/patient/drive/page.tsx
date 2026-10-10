"use client";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { del, downloadFile, get, post, upload } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { IconLock } from "@/components/icons";

interface Doc { id: number; category: string; original_filename: string; mime_type: string; size_bytes: number; sha256: string; document_date: string | null; created_at: string }
const CATS = ["LAB_REPORT", "PRESCRIPTION", "DISCHARGE", "IMAGING", "INSURANCE", "ID", "OTHER"];

export default function Drive() {
  const { t } = useI18n();
  const [docs, setDocs] = useState<Doc[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [cat, setCat] = useState("LAB_REPORT");
  const [date, setDate] = useState("");
  const [grantFor, setGrantFor] = useState<number | null>(null);
  const [grant, setGrant] = useState({ user_id: "", reason: "", expires_at: "" });
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const load = () => get<Doc[]>("/drive/documents").then(setDocs).catch((e) => setErr(e.message));
  useEffect(() => { void load(); }, []);

  const up = async (e: React.FormEvent) => {
    e.preventDefault(); if (!file) return; setErr(null);
    try { await upload("/drive/documents", { file, category: cat, document_date: date || undefined }); setFile(null); setMsg("Uploaded and encrypted"); void load(); } catch (ex) { setErr((ex as Error).message); }
  };
  const doGrant = async (e: React.FormEvent) => {
    e.preventDefault(); if (grantFor == null) return; setErr(null);
    try {
      await post(`/drive/documents/${grantFor}/grant-access`, { user_id: Number(grant.user_id), reason: grant.reason || null, expires_at: grant.expires_at ? new Date(grant.expires_at).toISOString() : null });
      setMsg("Access granted"); setGrantFor(null); setGrant({ user_id: "", reason: "", expires_at: "" });
    } catch (ex) { setErr((ex as Error).message); }
  };
  const remove = async (id: number) => { if (!confirm("Delete this document?")) return; try { await del(`/drive/documents/${id}`); void load(); } catch (e) { setErr((e as Error).message); } };

  return (
    <Shell portal="patient" title={t("drive")}>
      <p className="mb-3 flex items-center gap-2 text-xs muted"><IconLock size={14} /> Encrypted at rest; every download is audited. Only you, your treating doctors, and people you grant can open these.</p>
      {err && <p className="mb-2 text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
      {msg && <p className="mb-2 text-xs muted">{msg}</p>}
      <form onSubmit={up} className="card mb-4 flex flex-wrap items-end gap-2">
        <label className="text-sm"><span className="label">File (PDF / image / text, ≤15 MB)</span><input className="input" type="file" accept=".pdf,image/*,.txt" onChange={(e) => setFile(e.target.files?.[0] || null)} required /></label>
        <label className="text-sm"><span className="label">Category</span><select className="input" value={cat} onChange={(e) => setCat(e.target.value)}>{CATS.map((c) => <option key={c}>{c}</option>)}</select></label>
        <label className="text-sm"><span className="label">Document date</span><input className="input" type="date" value={date} onChange={(e) => setDate(e.target.value)} /></label>
        <button className="btn-primary" disabled={!file}>Upload</button>
      </form>
      <ul className="space-y-2">
        {docs.length === 0 && <li className="muted">Your drive is empty.</li>}
        {docs.map((d) => (
          <li key={d.id} className="card text-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span><strong>{d.original_filename}</strong> <span className="badge ml-1">{d.category}</span> <span className="muted">{(d.size_bytes / 1024).toFixed(1)} KB · {d.document_date || d.created_at.slice(0, 10)}</span><br /><span className="mono text-xs muted">sha256 {d.sha256.slice(0, 12)}…</span></span>
              <span className="flex gap-1">
                <button className="btn-ghost px-2 py-0.5 text-xs" onClick={() => downloadFile(`/drive/documents/${d.id}/download`, d.original_filename).catch((e) => setErr(e.message))}>Download</button>
                <button className="btn-ghost px-2 py-0.5 text-xs" onClick={() => setGrantFor(grantFor === d.id ? null : d.id)}>Grant access</button>
                <button className="btn-ghost px-2 py-0.5 text-xs" onClick={() => remove(d.id)}>Delete</button>
              </span>
            </div>
            {grantFor === d.id && (
              <form onSubmit={doGrant} className="mt-2 flex flex-wrap gap-1">
                <input className="input w-28" type="number" placeholder="User ID" value={grant.user_id} onChange={(e) => setGrant({ ...grant, user_id: e.target.value })} required />
                <input className="input w-48" placeholder="Reason" value={grant.reason} onChange={(e) => setGrant({ ...grant, reason: e.target.value })} />
                <input className="input w-auto" type="datetime-local" value={grant.expires_at} onChange={(e) => setGrant({ ...grant, expires_at: e.target.value })} />
                <button className="btn-primary">Grant</button>
              </form>
            )}
          </li>
        ))}
      </ul>
    </Shell>
  );
}
