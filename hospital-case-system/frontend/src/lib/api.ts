const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API = `${BASE}/api/v1`;

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("arogya_token");
}

async function refreshToken(): Promise<string | null> {
  try {
    const r = await fetch(`${API}/auth/refresh`, { method: "POST", credentials: "include" });
    if (!r.ok) return null;
    const j = await r.json();
    localStorage.setItem("arogya_token", j.access_token);
    localStorage.setItem("arogya_role", j.role);
    localStorage.setItem("arogya_name", j.name);
    return j.access_token as string;
  } catch {
    return null;
  }
}

async function withRefresh(run: (token: string | null) => Promise<Response>): Promise<Response> {
  let res = await run(getToken());
  if (res.status === 401) {
    const t = await refreshToken();
    if (t) res = await run(t);
  }
  return res;
}

async function parseError(res: Response): Promise<never> {
  let detail = `${res.status} ${res.statusText}`;
  try {
    const j = await res.json();
    if (typeof j.detail === "string") detail = j.detail;
    else if (Array.isArray(j.detail)) detail = j.detail.map((d: { msg: string }) => d.msg).join("; ");
  } catch {
    /* ignore */
  }
  throw new Error(detail);
}

export async function api<T = unknown>(path: string, opts: RequestInit = {}): Promise<T> {
  const res = await withRefresh((token) =>
    fetch(`${API}${path}`, {
      ...opts,
      credentials: "include",
      headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(opts.headers || {}) },
    }),
  );
  if (!res.ok) await parseError(res);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const get = <T = unknown>(p: string) => api<T>(p);
export const post = <T = unknown>(p: string, body?: unknown) => api<T>(p, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });
export const patch = <T = unknown>(p: string, body?: unknown) => api<T>(p, { method: "PATCH", body: JSON.stringify(body ?? {}) });
export const put = <T = unknown>(p: string, body?: unknown) => api<T>(p, { method: "PUT", body: JSON.stringify(body ?? {}) });
export const del = <T = unknown>(p: string) => api<T>(p, { method: "DELETE" });

export async function upload<T = unknown>(path: string, fields: Record<string, string | Blob | undefined>): Promise<T> {
  const fd = new FormData();
  Object.entries(fields).forEach(([k, v]) => {
    if (v !== undefined && v !== null) fd.append(k, v as string | Blob);
  });
  const res = await withRefresh((token) =>
    fetch(`${API}${path}`, { method: "POST", credentials: "include", body: fd, headers: token ? { Authorization: `Bearer ${token}` } : {} }),
  );
  if (!res.ok) await parseError(res);
  return (await res.json()) as T;
}

export async function downloadFile(path: string, filename: string): Promise<void> {
  const res = await withRefresh((token) =>
    fetch(`${API}${path}`, { credentials: "include", headers: token ? { Authorization: `Bearer ${token}` } : {} }),
  );
  if (!res.ok) await parseError(res);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export { API, BASE };
