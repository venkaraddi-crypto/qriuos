"use client";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import Shell from "@/components/Shell";
import HistorySummaryPanel from "@/components/HistorySummaryPanel";
import { get, post } from "@/lib/api";
import PatientHeader from "@/components/consultation/PatientHeader";
import IntakeSummaryCard from "@/components/consultation/IntakeSummaryCard";
import VoiceIntakePanel from "@/components/consultation/VoiceIntakePanel";
import SocratesCard from "@/components/consultation/SocratesCard";
import VitalsTrendCard from "@/components/consultation/VitalsTrendCard";
import AyurvedaAssessmentCard from "@/components/consultation/AyurvedaAssessmentCard";
import AmbientScribeCard from "@/components/consultation/AmbientScribeCard";
import DiagnosisCard from "@/components/consultation/DiagnosisCard";
import PrescriptionCard from "@/components/consultation/PrescriptionCard";
import LabOrdersCard from "@/components/consultation/LabOrdersCard";
import DispatchCard from "@/components/consultation/DispatchCard";
import SummaryNotesCard from "@/components/consultation/SummaryNotesCard";
import { useFlash } from "@/components/consultation/useFlash";
import type { Encounter, IntakeSummary, SocratesEntities, SttStatus, VitalsRow } from "@/components/consultation/types";

export default function ConsultationPage() {
  const { id } = useParams<{ id: string }>();
  const encId = Number(id);
  const [encounter, setEncounter] = useState<Encounter | null>(null);
  const [entities, setEntities] = useState<SocratesEntities | null>(null);
  const [intakeText, setIntakeText] = useState("");
  const [summary, setSummary] = useState("");
  const [notes, setNotes] = useState("");
  const [ashtavidha, setAshtavidha] = useState<Record<string, string>>({});
  const [intakeSummary, setIntakeSummary] = useState<IntakeSummary | null>(null);
  const [sttStatus, setSttStatus] = useState<SttStatus | null>(null);
  const [vitalsHistory, setVitalsHistory] = useState<VitalsRow[]>([]);
  const [dispatchVersion, setDispatchVersion] = useState(0);
  const [err, setErr] = useState<string | null>(null);
  const { message, flash } = useFlash();

  const reload = useCallback(async () => {
    const e = await get<Encounter>(`/encounters/${encId}`);
    setEncounter(e);
    setEntities(e.extracted_entities);
    setIntakeText((t) => t || e.chief_complaint_raw || "");
    setSummary(e.summary || "");
    setNotes(e.clinical_notes || "");
    setAshtavidha(e.ayush?.ashtavidha_data || {});
    return e;
  }, [encId]);

  useEffect(() => {
    if (!encId) return;
    reload()
      .then((e) => {
        get<SttStatus>("/voice/stt-status").then(setSttStatus).catch(() => {});
        get<IntakeSummary>(`/encounters/${encId}/intake-summary`).then(setIntakeSummary).catch(() => {});
        get<VitalsRow[]>(`/patients/${e.patient.id}/vitals-history`).then(setVitalsHistory).catch(() => {});
      })
      .catch((e) => setErr((e as Error).message));
  }, [encId, reload]);

  const extract = async () => {
    try {
      const ents = await post<SocratesEntities>("/nlp/extract-entities", { text: intakeText, encounter_id: encId });
      setEntities(ents);
      flash(ents.red_flags.length ? `Red flags: ${ents.red_flags.join(", ")}` : "Entities extracted", 3000);
      await reload();
    } catch (e) { setErr((e as Error).message); }
  };

  const scheduleFollowUp = async (weeks: number) => {
    if (!encounter) return;
    const d = new Date();
    d.setDate(d.getDate() + weeks * 7);
    try {
      await post("/followup/schedule", { patient_id: encounter.patient.id, doctor_id: encounter.doctor_id, date: d.toISOString().slice(0, 10), note: "Follow-up from SOAP plan" });
      flash(`Follow-up booked for ${d.toISOString().slice(0, 10)}`, 3000);
    } catch (e) { setErr((e as Error).message); }
  };

  const isAyu = encounter?.system === "AYURVEDA";
  const bump = () => setDispatchVersion((v) => v + 1);

  return (
    <Shell portal="staff" title="Consultation" tint={isAyu ? "ayu" : "allo"}>
      {err && <p className="mb-3 text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
      {!encounter ? <p className="muted">Loading encounter…</p> : (
        <div className="space-y-4">
          <PatientHeader encounter={encounter} redFlags={entities?.red_flags || []} />
          <HistorySummaryPanel encId={encId} onInsert={(n) => { setNotes((cur) => (cur ? `${cur}\n\n${n}` : n)); flash("Narrative inserted into notes"); }} />
          <IntakeSummaryCard summary={intakeSummary} />
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="space-y-4">
              <VoiceIntakePanel sttStatus={sttStatus} text={intakeText} onTextChange={setIntakeText} onExtract={extract} />
              <SocratesCard entities={entities} />
              <VitalsTrendCard history={vitalsHistory} />
              {isAyu && <AyurvedaAssessmentCard encounter={encounter} entities={entities} ashtavidha={ashtavidha} onAshtavidhaChange={setAshtavidha} onSaved={(m) => flash(m, 3000)} />}
              <AmbientScribeCard encounterId={encId} onApproved={() => void reload()} onScheduleFollowUp={scheduleFollowUp} />
            </div>
            <div className="space-y-4">
              <DiagnosisCard encounterId={encId} isAyurveda={Boolean(isAyu)} diagnoses={encounter.diagnoses} onChanged={(rows) => setEncounter({ ...encounter, diagnoses: rows })} />
              <PrescriptionCard encounterId={encId} patientId={encounter.patient.id} onSigned={() => { void reload(); bump(); }} />
              <LabOrdersCard encounterId={encId} orders={encounter.lab_orders} onChanged={(rows) => { setEncounter({ ...encounter, lab_orders: rows }); bump(); }} />
              <DispatchCard encounterId={encId} refreshKey={dispatchVersion} onReferred={() => flash("Referral created", 3000)} />
              <SummaryNotesCard encounterId={encId} summary={summary} notes={notes} onSummaryChange={setSummary} onNotesChange={setNotes}
                hasPrescription={encounter.prescriptions.length > 0} statusMessage={message} onSaved={(m) => flash(m, 3000)} />
            </div>
          </div>
        </div>
      )}
    </Shell>
  );
}
