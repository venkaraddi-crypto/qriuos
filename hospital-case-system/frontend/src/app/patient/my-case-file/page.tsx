"use client";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import CaseFile from "@/components/CaseFile";
import { get } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export default function MyCaseFile() {
  const { t } = useI18n();
  const [pid, setPid] = useState<number | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { get<{ patient: { id: number } }>("/patients/me/summary").then((s) => setPid(s.patient.id)).catch((e) => setErr(e.message)); }, []);
  return (
    <Shell portal="patient" title={t("my_case_file")}>
      {err && <p className="text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
      {pid != null && <CaseFile patientId={pid} />}
    </Shell>
  );
}
