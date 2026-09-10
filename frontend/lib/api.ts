const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("campusops_token");
}

export function setToken(token: string) {
  localStorage.setItem("campusops_token", token);
}

export function clearToken() {
  localStorage.removeItem("campusops_token");
}

export async function api<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    ...(opts.headers as Record<string, string> | undefined),
  };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (opts.body && typeof opts.body === "string" && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  const resp = await fetch(`${BASE}${path}`, { ...opts, headers });
  if (resp.status === 401 && typeof window !== "undefined") {
    clearToken();
    window.location.href = "/login";
    throw new Error("Session expired");
  }
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(text || `Request failed (${resp.status})`);
  }
  const text = await resp.text();
  return (text ? JSON.parse(text) : null) as T;
}

export async function upload(path: string, file: File): Promise<any> {
  const token = getToken();
  const form = new FormData();
  form.append("file", file);
  const resp = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  });
  if (!resp.ok) throw new Error(await resp.text());
  return resp.json();
}
