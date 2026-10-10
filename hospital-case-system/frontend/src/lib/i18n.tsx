"use client";
import { createContext, useContext, useEffect, useState } from "react";

export type LangCode = "en-IN" | "hi-IN" | "te-IN" | "mr-IN" | "bn-IN" | "ta-IN";

export const LANGUAGES: { code: LangCode; label: string; native: string }[] = [
  { code: "en-IN", label: "English", native: "English" },
  { code: "hi-IN", label: "Hindi", native: "हिन्दी" },
  { code: "te-IN", label: "Telugu", native: "తెలుగు" },
  { code: "mr-IN", label: "Marathi", native: "मराठी" },
  { code: "bn-IN", label: "Bengali", native: "বাংলা" },
  { code: "ta-IN", label: "Tamil", native: "தமிழ்" },
];

type Dict = Record<string, Partial<Record<LangCode, string>>>;

const DICT: Dict = {
  home: { "en-IN": "Home", "hi-IN": "होम", "te-IN": "హోమ్", "mr-IN": "मुख्यपृष्ठ", "bn-IN": "হোম", "ta-IN": "முகப்பு" },
  book_appointment: { "en-IN": "Book Appointment", "hi-IN": "अपॉइंटमेंट बुक करें", "te-IN": "అపాయింట్‌మెంట్ బుక్", "mr-IN": "अपॉइंटमेंट बुक करा", "bn-IN": "অ্যাপয়েন্টমেন্ট বুক", "ta-IN": "சந்திப்பு பதிவு" },
  my_appointments: { "en-IN": "My Appointments", "hi-IN": "मेरी अपॉइंटमेंट", "te-IN": "నా అపాయింట్‌మెంట్లు", "mr-IN": "माझ्या अपॉइंटमेंट", "bn-IN": "আমার অ্যাপয়েন্টমেন্ট", "ta-IN": "என் சந்திப்புகள்" },
  my_case_file: { "en-IN": "My Case File", "hi-IN": "मेरी केस फाइल", "te-IN": "నా కేస్ ఫైల్", "mr-IN": "माझी केस फाईल", "bn-IN": "আমার কেস ফাইল", "ta-IN": "என் வழக்கு கோப்பு" },
  my_records: { "en-IN": "My Records", "hi-IN": "मेरे रिकॉर्ड", "te-IN": "నా రికార్డులు", "mr-IN": "माझे रेकॉर्ड", "bn-IN": "আমার রেকর্ড", "ta-IN": "என் பதிவுகள்" },
  digitize: { "en-IN": "Digitize Records", "hi-IN": "रिकॉर्ड डिजिटल करें", "te-IN": "రికార్డులు డిజిటైజ్", "mr-IN": "रेकॉर्ड डिजिटल करा", "bn-IN": "রেকর্ড ডিজিটাল করুন", "ta-IN": "பதிவுகளை டிஜிட்டலாக்கு" },
  drive: { "en-IN": "Medical Drive", "hi-IN": "मेडिकल ड्राइव", "te-IN": "మెడికల్ డ్రైవ్", "mr-IN": "मेडिकल ड्राइव्ह", "bn-IN": "মেডিকেল ড্রাইভ", "ta-IN": "மருத்துவ டிரைவ்" },
  family: { "en-IN": "My Family", "hi-IN": "मेरा परिवार", "te-IN": "నా కుటుంబం", "mr-IN": "माझे कुटुंब", "bn-IN": "আমার পরিবার", "ta-IN": "என் குடும்பம்" },
  notifications: { "en-IN": "Notifications", "hi-IN": "सूचनाएँ", "te-IN": "నోటిఫికేషన్లు", "mr-IN": "सूचना", "bn-IN": "বিজ্ঞপ্তি", "ta-IN": "அறிவிப்புகள்" },
  settings: { "en-IN": "Settings", "hi-IN": "सेटिंग्स", "te-IN": "సెట్టింగ్లు", "mr-IN": "सेटिंग्ज", "bn-IN": "সেটিংস", "ta-IN": "அமைப்புகள்" },
  logout: { "en-IN": "Logout", "hi-IN": "लॉग आउट", "te-IN": "లాగ్అవుట్", "mr-IN": "लॉग आउट", "bn-IN": "লগ আউট", "ta-IN": "வெளியேறு" },
  login: { "en-IN": "Login", "hi-IN": "लॉगिन", "te-IN": "లాగిన్", "mr-IN": "लॉगिन", "bn-IN": "লগইন", "ta-IN": "உள்நுழை" },
  email: { "en-IN": "Email", "hi-IN": "ईमेल", "te-IN": "ఇమెయిల్", "mr-IN": "ईमेल", "bn-IN": "ইমেইল", "ta-IN": "மின்னஞ்சல்" },
  password: { "en-IN": "Password", "hi-IN": "पासवर्ड", "te-IN": "పాస్వర్డ్", "mr-IN": "पासवर्ड", "bn-IN": "পাসওয়ার্ড", "ta-IN": "கடவுச்சொல்" },
  next_appointment: { "en-IN": "Next appointment", "hi-IN": "अगली अपॉइंटमेंट", "te-IN": "తదుపరి అపాయింట్‌మెంట్", "mr-IN": "पुढील अपॉइंटमेंट", "bn-IN": "পরবর্তী অ্যাপয়েন্টমেন্ট", "ta-IN": "அடுத்த சந்திப்பு" },
  token: { "en-IN": "Token", "hi-IN": "टोकन", "te-IN": "టోకెన్", "mr-IN": "टोकन", "bn-IN": "টোকেন", "ta-IN": "டோக்கன்" },
  your_turn: { "en-IN": "It is your turn", "hi-IN": "आपकी बारी है", "te-IN": "మీ వంతు వచ్చింది", "mr-IN": "तुमची पाळी आहे", "bn-IN": "আপনার পালা", "ta-IN": "உங்கள் முறை" },
  save: { "en-IN": "Save", "hi-IN": "सहेजें", "te-IN": "సేవ్", "mr-IN": "जतन करा", "bn-IN": "সংরক্ষণ", "ta-IN": "சேமி" },
  cancel: { "en-IN": "Cancel", "hi-IN": "रद्द करें", "te-IN": "రద్దు", "mr-IN": "रद्द करा", "bn-IN": "বাতিল", "ta-IN": "ரத்து" },
  loading: { "en-IN": "Loading…", "hi-IN": "लोड हो रहा है…", "te-IN": "లోడ్ అవుతోంది…", "mr-IN": "लोड होत आहे…", "bn-IN": "লোড হচ্ছে…", "ta-IN": "ஏற்றுகிறது…" },
  welcome: { "en-IN": "Welcome", "hi-IN": "स्वागत है", "te-IN": "స్వాగతం", "mr-IN": "स्वागत", "bn-IN": "স্বাগতম", "ta-IN": "வரவேற்கிறோம்" },
};

interface Ctx {
  lang: LangCode;
  setLang: (l: LangCode) => void;
  t: (key: string) => string;
}

const I18nContext = createContext<Ctx>({ lang: "en-IN", setLang: () => {}, t: (k) => k });

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<LangCode>("en-IN");
  useEffect(() => {
    const saved = localStorage.getItem("arogya_lang") as LangCode | null;
    if (saved && LANGUAGES.some((l) => l.code === saved)) setLangState(saved);
  }, []);
  const setLang = (l: LangCode) => {
    setLangState(l);
    localStorage.setItem("arogya_lang", l);
  };
  const t = (key: string) => DICT[key]?.[lang] ?? DICT[key]?.["en-IN"] ?? key;
  return <I18nContext.Provider value={{ lang, setLang, t }}>{children}</I18nContext.Provider>;
}

export const useI18n = () => useContext(I18nContext);
