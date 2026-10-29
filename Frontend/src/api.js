const configuredBase = import.meta.env.VITE_API_URL ?? "";
const API_BASE = configuredBase.replace(/\/$/, "");

export async function apiRequest(path, { token, onUnauthorized, ...options } = {}) {
  const headers = new Headers(options.headers ?? {});
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  // A 401 on an authenticated call means the token expired; a 401 on sign-in is just a wrong password.
  if (response.status === 401 && token) {
    onUnauthorized?.();
    throw new Error("Your session has expired. Please sign in again.");
  }
  const contentType = response.headers.get("content-type") ?? "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const message = typeof payload === "object" ? payload.detail ?? payload.message : payload;
    throw new Error(message || `Request failed (${response.status})`);
  }
  return payload;
}

export async function loginRequest(email, password, role) {
  const form = new URLSearchParams({ username: email, password, scope: role });
  return apiRequest("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form,
  });
}
