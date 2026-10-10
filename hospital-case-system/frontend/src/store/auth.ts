"use client";
import { create } from "zustand";
import { post } from "@/lib/api";

export type Role = "PATIENT" | "RECEPTION" | "DOCTOR" | "NURSE" | "LAB" | "PHARMACY" | "BILLING" | "ADMIN";

export const ROLE_HOME: Record<Role, string> = {
  PATIENT: "/patient/home",
  RECEPTION: "/reception/checkin",
  DOCTOR: "/doctor/queue",
  NURSE: "/nurse/vitals",
  LAB: "/lab/orders",
  PHARMACY: "/pharmacy/dispense",
  BILLING: "/billing/bills",
  ADMIN: "/admin/analytics",
};

interface AuthState {
  token: string | null;
  role: Role | null;
  name: string | null;
  login: (email: string, password: string) => Promise<Role>;
  logout: () => Promise<void>;
  hydrate: () => void;
}

export const useAuth = create<AuthState>((set) => ({
  token: null,
  role: null,
  name: null,
  hydrate: () => {
    if (typeof window === "undefined") return;
    set({
      token: localStorage.getItem("arogya_token"),
      role: (localStorage.getItem("arogya_role") as Role | null) || null,
      name: localStorage.getItem("arogya_name"),
    });
  },
  login: async (email, password) => {
    const j = await post<{ access_token: string; role: Role; name: string }>("/auth/login", { email, password });
    localStorage.setItem("arogya_token", j.access_token);
    localStorage.setItem("arogya_role", j.role);
    localStorage.setItem("arogya_name", j.name);
    set({ token: j.access_token, role: j.role, name: j.name });
    return j.role;
  },
  logout: async () => {
    const role = localStorage.getItem("arogya_role");
    try {
      await post("/auth/logout");
    } catch {
      /* ignore */
    }
    localStorage.removeItem("arogya_token");
    localStorage.removeItem("arogya_role");
    localStorage.removeItem("arogya_name");
    set({ token: null, role: null, name: null });
    window.location.href = role && role !== "PATIENT" ? "/staff/login" : "/login";
  },
}));
