"use client";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import DocumentDigitizer from "@/components/DocumentDigitizer";
import { get } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export default function Documents() {
  const { t } = useI18n();
  const [pid, setPid] = useState<number | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { get<{ patient: { id: number } }>("/patients/me/summary").then((s) => setPid(s.patient.id)).catch((e) => setErr(e.message)); }, []);
  return (
    <Shell portal="patient" title={t("digitize")}>
      {err && <p className="text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
      <p className="mb-3 text-sm muted">Upload an old lab report, prescription or discharge summary. We read it (Sarvam OCR, PDF text layer, or a labelled sample when neither is available), let you correct the values, then add them to your case file.</p>
      {pid != null && <DocumentDigitizer patientId={pid} title="Digitize my old records" />}
    </Shell>
  );
}
