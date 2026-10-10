"use client";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { del, get, patch, post, upload } from "@/lib/api";
import { LANGUAGES, LangCode, useI18n } from "@/lib/i18n";
import { Theme, useTheme } from "@/components/ThemeProvider";
import { IconLock, IconUser } from "@/components/icons";

interface Me { id: number; name: string; email: string; role: string; preferred_language: string; theme_preference: string; notification_preferences: Record<string, boolean>; photo_url: string | null }
interface Session { id: number; created_at: string; expires_at: string; revoked_at: string | null; user_agent: string | null; active: boolean }
const NOTIF_KEYS = ["turn_alerts", "lab_ready", "bills"];

export default function SettingsPage() {
  const { setLang } = useI18n();
  const { setTheme } = useTheme();
  const [me, setMe] = useState<Me | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [pw, setPw] = useState({ current_password: "", new_password: "" });
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [portal, setPortal] = useState<"patient" | "staff">("staff");

  const load = () => { get<Me>("/settings/me").then(setMe).catch((e) => setErr(e.message)); get<Session[]>("/settings/sessions").then(setSessions).catch(() => {}); };
  useEffect(() => { setPortal(localStorage.getItem("arogya_role") === "PATIENT" ? "patient" : "staff"); load(); }, []);

  const save = async () => {
    if (!me) return;
    setErr(null);
    try {
      const r = await patch<Me>("/settings/me", { name: me.name, preferred_language: me.preferred_language, theme_preference: me.theme_preference, notification_preferences: me.notification_preferences });
      setMe(r); setLang(r.preferred_language as LangCode); setTheme(r.theme_preference as Theme); localStorage.setItem("arogya_name", r.name); setMsg("Saved");
    } catch (e) { setErr((e as Error).message); }
  };
  const changePw = async () => {
    setErr(null);
    try { const r = await post<{ sessions_revoked: number }>("/settings/change-password", pw); setMsg(`Password changed; ${r.sessions_revoked} session(s) revoked`); setPw({ current_password: "", new_password: "" }); load(); } catch (e) { setErr((e as Error).message); }
  };
  const photo = async (f: File | undefined) => {
    if (!f) return;
    try { setMe(await upload<Me>("/profile/photo", { file: f })); setMsg("Photo updated"); } catch (e) { setErr((e as Error).message); }
  };

  return (
    <Shell portal={portal} title="Settings">
      {err && <p className="mb-3 text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
      {msg && <p className="mb-3 text-xs muted">{msg}</p>}
      {me && (
        <div className="grid gap-4 md:grid-cols-2">
          <section className="card space-y-3">
            <h2 className="serif text-lg flex items-center gap-2"><IconUser size={18} /> Profile</h2>
            <label className="block text-sm"><span className="label">Name</span><input className="input" value={me.name} onChange={(e) => setMe({ ...me, name: e.target.value })} /></label>
            <p className="text-sm muted">{me.email} · {me.role}</p>
            <label className="block text-sm"><span className="label">Preferred language</span>
              <select className="input" value={me.preferred_language} onChange={(e) => setMe({ ...me, preferred_language: e.target.value })}>{LANGUAGES.map((l) => <option key={l.code} value={l.code}>{l.native}</option>)}</select></label>
            <label className="block text-sm"><span className="label">Theme</span>
              <select className="input" value={me.theme_preference} onChange={(e) => setMe({ ...me, theme_preference: e.target.value })}><option value="system">System</option><option value="light">Light</option><option value="dark">Dark</option></select></label>
            <div className="text-sm"><span className="label">Notifications</span>
              {NOTIF_KEYS.map((k) => (
                <label key={k} className="mr-3 inline-flex items-center gap-1"><input type="checkbox" checked={me.notification_preferences?.[k] ?? true} onChange={(e) => setMe({ ...me, notification_preferences: { ...me.notification_preferences, [k]: e.target.checked } })} /> {k.replace("_", " ")}</label>
              ))}
            </div>
            <label className="block text-sm"><span className="label">Profile photo</span><input className="input" type="file" accept="image/*" onChange={(e) => photo(e.target.files?.[0])} /></label>
            <button className="btn-primary" onClick={save}>Save</button>
          </section>
          <section className="card space-y-3">
            <h2 className="serif text-lg flex items-center gap-2"><IconLock size={18} /> Security</h2>
            <label className="block text-sm"><span className="label">Current password</span><input className="input" type="password" value={pw.current_password} onChange={(e) => setPw({ ...pw, current_password: e.target.value })} /></label>
            <label className="block text-sm"><span className="label">New password (min 8)</span><input className="input" type="password" value={pw.new_password} onChange={(e) => setPw({ ...pw, new_password: e.target.value })} /></label>
            <button className="btn-ghost" onClick={changePw}>Change password</button>
            <h3 className="serif pt-2">Sessions</h3>
            <ul className="space-y-1 text-xs">
              {sessions.map((s) => (
                <li key={s.id} className="flex items-center justify-between gap-2">
                  <span><span className={`badge ${s.active ? "badge-green" : ""}`}>{s.active ? "active" : "ended"}</span> <span className="mono">{s.created_at.slice(0, 16).replace("T", " ")}</span> <span className="muted">{(s.user_agent || "").slice(0, 40)}</span></span>
                  {s.active && <button className="btn-ghost px-2 py-0.5" onClick={() => del(`/settings/sessions/${s.id}`).then(load)}>Revoke</button>}
                </li>
              ))}
            </ul>
          </section>
        </div>
      )}
    </Shell>
  );
}
