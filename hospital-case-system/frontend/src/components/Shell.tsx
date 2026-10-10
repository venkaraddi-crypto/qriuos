"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ROLE_HOME, Role, useAuth } from "@/store/auth";
import { useI18n } from "@/lib/i18n";
import { IconLeaf, IconLogout } from "@/components/icons";
import LanguageSwitcher from "@/components/LanguageSwitcher";
import FontSizeControl from "@/components/FontSizeControl";

type NavItem = { href: string; key: string; label: string };

export const PATIENT_NAV: NavItem[] = [
  { href: "/patient/home", key: "home", label: "Home" },
  { href: "/patient/book-appointment", key: "book_appointment", label: "Book Appointment" },
  { href: "/patient/my-appointments", key: "my_appointments", label: "My Appointments" },
  { href: "/patient/my-case-file", key: "my_case_file", label: "My Case File" },
  { href: "/patient/my-records", key: "my_records", label: "My Records" },
  { href: "/patient/documents", key: "digitize", label: "Digitize Records" },
  { href: "/patient/drive", key: "drive", label: "Medical Drive" },
  { href: "/patient/family", key: "family", label: "My Family" },
  { href: "/patient/notifications", key: "notifications", label: "Notifications" },
  { href: "/settings", key: "settings", label: "Settings" },
];

export const STAFF_NAV: Record<Exclude<Role, "PATIENT">, NavItem[]> = {
  RECEPTION: [
    { href: "/reception/checkin", key: "checkin", label: "Scan Check-in" },
    { href: "/reception/walkin", key: "walkin", label: "Walk-in" },
    { href: "/reception/board", key: "board", label: "Board" },
  ],
  DOCTOR: [{ href: "/doctor/queue", key: "queue", label: "Queue" }],
  NURSE: [{ href: "/nurse/vitals", key: "vitals", label: "Vitals & Therapy" }],
  LAB: [{ href: "/lab/orders", key: "lab", label: "Lab Orders" }],
  PHARMACY: [{ href: "/pharmacy/dispense", key: "pharmacy", label: "Dispense & Stock" }],
  BILLING: [{ href: "/billing/bills", key: "billing", label: "Bills" }],
  ADMIN: [
    { href: "/admin/analytics", key: "analytics", label: "Analytics" },
    { href: "/admin/staff", key: "staff", label: "Staff" },
    { href: "/admin/manage", key: "manage", label: "Departments & Slots" },
    { href: "/admin/security", key: "security", label: "Security & Audit" },
    { href: "/admin/ai-settings", key: "ai", label: "AI Settings" },
    { href: "/admin/about", key: "about", label: "About" },
  ],
};

interface Props {
  children: React.ReactNode;
  tint?: "allo" | "ayu";
  portal: "patient" | "staff";
  title?: string;
}

export default function Shell({ children, tint, portal, title }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const { t } = useI18n();
  const { logout } = useAuth();
  const [role, setRole] = useState<Role | null>(null);
  const [name, setName] = useState<string>("");
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("arogya_token");
    const r = localStorage.getItem("arogya_role") as Role | null;
    if (!token || !r) {
      router.replace(portal === "staff" ? "/staff/login" : "/login");
      return;
    }
    if ((portal === "staff" && r === "PATIENT") || (portal === "patient" && r !== "PATIENT")) {
      router.replace(ROLE_HOME[r]);
      return;
    }
    setRole(r);
    setName(localStorage.getItem("arogya_name") || "");
    setReady(true);
  }, [portal, router]);

  if (!ready || !role) return <div className="p-8 muted">{t("loading")}</div>;

  const nav: NavItem[] = role === "PATIENT" ? PATIENT_NAV : [...STAFF_NAV[role], { href: "/settings", key: "settings", label: "Settings" }];

  return (
    <div className="flex min-h-screen">
      <nav className="hidden w-56 shrink-0 border-r p-4 md:block hr" aria-label="Primary">
        <div className="mb-6 flex items-center gap-2 serif text-lg">
          <IconLeaf size={22} /> ArogyaSetu
        </div>
        <ul className="space-y-1">
          {nav.map((n) => (
            <li key={n.href}>
              <Link
                href={n.href}
                className={`block rounded-sm px-2 py-1.5 text-sm ${pathname.startsWith(n.href) ? "bg-clay text-white" : "hover:underline"}`}
              >
                {t(n.key) === n.key ? n.label : t(n.key)}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3 hr">
          <div className="flex items-center gap-3">
            <span className="md:hidden serif"><IconLeaf size={20} /></span>
            <h1 className="serif text-xl">{title || ""}</h1>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <span className="muted">{name}</span>
            <span className="badge">{role}</span>
            <LanguageSwitcher />
            <FontSizeControl />
            <button className="btn-ghost" onClick={() => void logout()} aria-label="Logout">
              <IconLogout size={16} /> {t("logout")}
            </button>
          </div>
        </header>
        <main id="main-content" className={`flex-1 p-4 md:p-6 ${tint === "allo" ? "tint-allo" : tint === "ayu" ? "tint-ayu" : ""}`}>
          {children}
        </main>
        <nav className="flex overflow-x-auto border-t md:hidden hr" aria-label="Mobile">
          {nav.map((n) => (
            <Link key={n.href} href={n.href} className={`whitespace-nowrap px-3 py-2 text-xs ${pathname.startsWith(n.href) ? "tab-active" : ""}`}>
              {n.label}
            </Link>
          ))}
        </nav>
      </div>
    </div>
  );
}
