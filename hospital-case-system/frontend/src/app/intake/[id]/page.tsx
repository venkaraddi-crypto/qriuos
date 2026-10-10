"use client";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { get, post } from "@/lib/api";
import ConsentGate from "@/components/ConsentGate";
import AdaptiveHistory from "@/components/AdaptiveHistory";
import { IconLeaf } from "@/components/icons";
import { Complaint, ComplaintsStep, RosStep } from "./IntakeSteps";
import BackgroundStep from "./BackgroundStep";

interface IntakeInfo { intake: { status: string; consent_recorded: boolean; consent_revoked_at: string | null; duration_sec: number | null } | null; appointment: { id: number; date: string; status: string }; chief_complaints: Complaint[] }
const STEPS = ["Consent", "Complaints", "History", "Background", "Review of systems", "Submit"];

export default function IntakePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const aid = Number(id);
  const [info, setInfo] = useState<IntakeInfo | null>(null);
  const [step, setStep] = useState(0);
  const [done, setDone] = useState<{ duration_sec: number | null } | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!localStorage.getItem("arogya_token")) { router.replace("/login"); return; }
    get<IntakeInfo>(`/intake/${aid}`).then((i) => {
      setInfo(i);
      if (i.intake?.status === "SUBMITTED" || i.intake?.status === "REVIEWED") { setDone({ duration_sec: i.intake.duration_sec }); setStep(5); }
      else if (i.intake?.consent_recorded && !i.intake.consent_revoked_at) setStep(1);
    }).catch((e) => setErr(e.message));
  }, [aid, router]);

  const submit = async () => {
    setErr(null);
    try { const r = await post<{ duration_sec: number | null }>(`/intake/${aid}/submit`); setDone(r); } catch (e) { setErr((e as Error).message); }
  };
  const onHistoryDone = useCallback(() => setStep((s) => (s === 2 ? 3 : s)), []);

  return (
    <main id="main-content" className="mx-auto max-w-2xl p-4 md:p-6">
      <header className="mb-4 flex items-center justify-between">
        <h1 className="serif flex items-center gap-2 text-2xl"><IconLeaf size={24} /> Pre-consultation assistant</h1>
        <Link className="text-sm underline muted" href="/patient/home">Back to home</Link>
      </header>
      <ol className="mb-4 flex flex-wrap gap-1 text-xs">{STEPS.map((s, i) => <li key={s} className={`badge ${i === step ? "badge-amber" : i < step ? "badge-green" : ""}`}>{i + 1}. {s}</li>)}</ol>
      {err && <p className="mb-2 text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
      {!info && !err && <p className="muted">Loading…</p>}
      {info && step === 0 && <ConsentGate appointmentId={aid} onStarted={() => setStep(1)} />}
      {info && step === 1 && <ComplaintsStep aid={aid} initial={info.chief_complaints} onNext={() => setStep(2)} />}
      {info && step === 2 && (
        <div className="space-y-2">
          <AdaptiveHistory appointmentId={aid} onDone={onHistoryDone} />
          <button className="btn-ghost" onClick={() => setStep(3)}>Skip remaining history questions</button>
        </div>
      )}
      {info && step === 3 && <BackgroundStep aid={aid} onNext={() => setStep(4)} />}
      {info && step === 4 && <RosStep aid={aid} onNext={() => setStep(5)} />}
      {info && step === 5 && (
        <section className="card space-y-3 text-center">
          {done ? (
            <>
              <h2 className="serif text-2xl">Submitted — thank you</h2>
              <p className="text-sm muted">Your doctor will see this summary before calling you in.{done.duration_sec != null && ` Took ${Math.max(1, Math.round(done.duration_sec / 60))} min.`}</p>
              <Link className="btn-primary justify-center" href="/patient/home">Back to home</Link>
            </>
          ) : (
            <>
              <h2 className="serif text-2xl">Ready to submit?</h2>
              <p className="text-sm muted">You can still revoke consent later from this page.</p>
              <div className="flex justify-center gap-2"><button className="btn-ghost" onClick={() => setStep(1)}>Review answers</button><button className="btn-primary" onClick={submit}>Submit to doctor</button></div>
            </>
          )}
        </section>
      )}
    </main>
  );
}
