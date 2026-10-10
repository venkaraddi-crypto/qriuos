"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ROLE_HOME, useAuth } from "@/store/auth";
import { useI18n } from "@/lib/i18n";
import { IconLeaf } from "@/components/icons";
import LanguageSwitcher from "@/components/LanguageSwitcher";

export default function PatientLogin() {
  const router = useRouter();
  const { login } = useAuth();
  const { t } = useI18n();
  const [email, setEmail] = useState("patient@demo.in");
  const [password, setPassword] = useState("password123");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const role = localStorage.getItem("arogya_role");
    if (localStorage.getItem("arogya_token") && role) router.replace(ROLE_HOME[role as keyof typeof ROLE_HOME]);
  }, [router]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      const role = await login(email, password);
      router.replace(ROLE_HOME[role]);
    } catch (ex) {
      setErr((ex as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <main id="main-content" className="mx-auto flex min-h-screen max-w-md flex-col justify-center p-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="serif flex items-center gap-2 text-3xl"><IconLeaf size={28} /> ArogyaSetu</h1>
        <LanguageSwitcher />
      </div>
      <p className="mb-6 muted">Patient portal — All India Institute of Ayurveda OPD.</p>
      <form onSubmit={submit} className="card space-y-4">
        <label className="block">
          <span className="label">{t("email")}</span>
          <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="username" />
        </label>
        <label className="block">
          <span className="label">{t("password")}</span>
          <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" />
        </label>
        {err && <p className="text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
        <button className="btn-primary w-full justify-center" disabled={busy}>{busy ? t("loading") : t("login")}</button>
      </form>
      <div className="mt-4 flex justify-between text-sm">
        <Link href="/register" className="underline">New patient? Register</Link>
        <Link href="/staff/login" className="underline muted">Staff login</Link>
      </div>
      <p className="mt-6 text-xs muted">Demo: patient@demo.in / password123</p>
    </main>
  );
}
