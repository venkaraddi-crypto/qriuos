"use client";
import { useState } from "react";
import { post } from "@/lib/api";
import DashavidhaPanel from "@/components/DashavidhaPanel";
import { ASHTAVIDHA_FIELDS, type Encounter, type PrakritiResult, type SocratesEntities } from "./types";

const TRAITS: { dosha: string; items: { key: string; label: string }[] }[] = [
  { dosha: "Vata", items: [["thin_build", "Thin build"], ["dry_skin", "Dry skin"], ["cold_intolerance", "Cold intolerance"], ["irregular_appetite", "Irregular appetite"], ["light_sleep", "Light sleep"], ["quick_mind", "Quick, restless mind"]].map(([key, label]) => ({ key, label })) },
  { dosha: "Pitta", items: [["medium_build", "Medium build"], ["warm_body", "Warm body"], ["sharp_appetite", "Sharp appetite"], ["early_greying", "Early greying"], ["irritability", "Irritability"], ["sweats_easily", "Sweats easily"]].map(([key, label]) => ({ key, label })) },
  { dosha: "Kapha", items: [["heavy_build", "Heavy build"], ["oily_skin", "Oily skin"], ["slow_digestion", "Slow digestion"], ["deep_sleep", "Deep sleep"], ["calm_nature", "Calm nature"], ["weight_gain", "Gains weight easily"]].map(([key, label]) => ({ key, label })) },
];

interface Props {
  encounter: Encounter;
  entities: SocratesEntities | null;
  ashtavidha: Record<string, string>;
  onAshtavidhaChange: (v: Record<string, string>) => void;
  onSaved: (msg: string) => void;
}

export default function AyurvedaAssessmentCard({ encounter, entities, ashtavidha, onAshtavidhaChange, onSaved }: Props) {
  const a = encounter.ayush;
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [prakriti, setPrakriti] = useState<PrakritiResult | null>(a?.prakriti_vata != null ? { vata: a.prakriti_vata, pitta: a.prakriti_pitta || 0, kapha: a.prakriti_kapha || 0, dominant: "" } : null);
  const [vikriti, setVikriti] = useState<string | null>(a?.vikriti_dosha || null);
  const [err, setErr] = useState<string | null>(null);

  const score = async () => {
    setErr(null);
    try {
      const symptoms = entities ? [entities.chief_complaint, ...entities.character, ...entities.associations].join(" ") : encounter.chief_complaint_raw || "";
      const r = await post<{ prakriti: PrakritiResult; vikriti: { aggravated_dosha: string; rationale: string } }>("/ayush/prakriti-score", { answers, encounter_id: encounter.id, current_symptoms: symptoms });
      setPrakriti(r.prakriti); setVikriti(r.vikriti.aggravated_dosha); onSaved(`Prakriti: ${r.prakriti.dominant} dominant · Vikriti: ${r.vikriti.aggravated_dosha}`);
    } catch (e) { setErr((e as Error).message); }
  };
  const saveAshtavidha = async () => {
    try { await post("/ayush/ashtavidha", { encounter_id: encounter.id, data: ashtavidha }); onSaved("Ashtavidha saved"); } catch (e) { setErr((e as Error).message); }
  };

  return (
    <section className="card tint-ayu space-y-4">
      <h3 className="serif text-lg">Ayurveda assessment</h3>
      <div>
        <p className="label">Prakriti questionnaire (0 = no, 1 = partly, 2 = yes)</p>
        <div className="grid gap-3 md:grid-cols-3">
          {TRAITS.map((g) => (
            <div key={g.dosha}>
              <p className="text-sm font-medium">{g.dosha}</p>
              {g.items.map((it) => (
                <div key={it.key} className="flex items-center justify-between py-0.5 text-sm">
                  <span>{it.label}</span>
                  <span className="flex gap-1">{[0, 1, 2].map((v) => <button key={v} className={`badge ${answers[it.key] === v ? "badge-amber" : ""}`} onClick={() => setAnswers({ ...answers, [it.key]: v })}>{v}</button>)}</span>
                </div>
              ))}
            </div>
          ))}
        </div>
        <button className="btn-primary mt-2" onClick={score}>Score Prakriti & Vikriti</button>
        {prakriti && (
          <div className="mt-2">
            <div className="flex h-3 w-full overflow-hidden rounded-sm" role="img" aria-label="Dosha distribution">
              <span style={{ width: `${prakriti.vata}%`, background: "#3E5C76" }} /><span style={{ width: `${prakriti.pitta}%`, background: "#B4552D" }} /><span style={{ width: `${prakriti.kapha}%`, background: "#7A6A21" }} />
            </div>
            <p className="mono mt-1 text-xs">V {prakriti.vata}% · P {prakriti.pitta}% · K {prakriti.kapha}%{vikriti && ` · Vikriti: ${vikriti}`}</p>
          </div>
        )}
      </div>
      <div>
        <p className="label">Ashtavidha Pariksha</p>
        <div className="grid gap-2 md:grid-cols-2">
          {ASHTAVIDHA_FIELDS.map((f) => (
            <label key={f.key} className="text-sm"><span className="muted">{f.label}</span>
              <input className="input" placeholder={f.hint} value={ashtavidha[f.key] || ""} onChange={(e) => onAshtavidhaChange({ ...ashtavidha, [f.key]: e.target.value })} /></label>
          ))}
        </div>
        <button className="btn-ghost mt-2" onClick={saveAshtavidha}>Save Ashtavidha</button>
      </div>
      <DashavidhaPanel encId={encounter.id} initial={a?.dashavidha_data} aharaInitial={a?.ahara_vihara} prakriti={prakriti ? `V${prakriti.vata}/P${prakriti.pitta}/K${prakriti.kapha}` : null} vikriti={vikriti} />
      {err && <p className="text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
    </section>
  );
}
