"use client";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { get, patch } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

interface Note { id: number; message: string; created_at: string; read: boolean }

export default function Notifications() {
  const { t } = useI18n();
  const [rows, setRows] = useState<Note[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const load = () => get<Note[]>("/notifications/me").then(setRows).catch((e) => setErr(e.message));
  useEffect(() => { void load(); }, []);
  const read = async (id: number) => { try { await patch(`/notifications/${id}/read`); void load(); } catch (e) { setErr((e as Error).message); } };

  return (
    <Shell portal="patient" title={t("notifications")}>
      {err && <p className="mb-2 text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
      <ul className="space-y-1">
        {rows.length === 0 && <li className="muted">No notifications.</li>}
        {rows.map((n) => (
          <li key={n.id} className={`card flex items-center justify-between text-sm ${n.read ? "" : "font-medium"}`}>
            <span>{n.message}<br /><span className="mono text-xs muted">{n.created_at.slice(0, 16).replace("T", " ")}</span></span>
            {!n.read && <button className="btn-ghost px-2 py-0.5 text-xs" onClick={() => read(n.id)}>Mark read</button>}
          </li>
        ))}
      </ul>
    </Shell>
  );
}
