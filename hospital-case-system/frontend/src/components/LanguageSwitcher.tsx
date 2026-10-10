"use client";
import { LANGUAGES, LangCode, useI18n } from "@/lib/i18n";

export default function LanguageSwitcher() {
  const { lang, setLang } = useI18n();
  return (
    <select aria-label="Language" className="input w-auto py-1 text-xs" value={lang} onChange={(e) => setLang(e.target.value as LangCode)}>
      {LANGUAGES.map((l) => (
        <option key={l.code} value={l.code}>
          {l.native}
        </option>
      ))}
    </select>
  );
}
