/**
 * Typed API client for the Voice_backend platform API. Reads the access token from the
 * auth store and attaches it as a Bearer header. Base URL defaults to same-origin
 * (Next rewrites proxy /api/* to the backend in dev).
 *
 * On a 401 it transparently refreshes the access token using the stored refresh token
 * (single retry), and clears the session on hard auth failure.
 *
 * Mirrors the backend 1:1 — every authenticated route in Voice_backend has a method here.
 */
import { useAuthStore } from "@/shared/store/auth";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export interface Tokens { access_token: string; refresh_token: string; token_type: string; }
export interface UserPublic { id: string; email: string; full_name?: string; avatar_url?: string; is_active: boolean; is_verified: boolean; }
export interface Video { id: string; filename: string; content_type?: string; size_bytes: number; duration_s?: number; status: string; created_at: string; }
export type JobMode = "translate" | "preserve" | "clone" | "localize";
export interface Job {
  id: string; video_id: string; target_language: string; source_language?: string;
  mode: string; status: string; progress: number; stage?: string; similarity?: number;
  result_key?: string; error?: string; created_at: string;
}
export interface UsageStats {
  videos: number; jobs_total: number; jobs_completed: number;
  jobs_failed: number; jobs_running: number; jobs_queued: number;
}
export interface ApiKeyPublic { id: string; name: string; prefix: string; is_active: boolean; created_at: string; }
export interface ApiKeyCreated extends ApiKeyPublic { key: string; }

/** Refresh the access token using the stored refresh token. Returns the new access token or null. */
async function tryRefresh(): Promise<string | null> {
  const refresh_token = useAuthStore.getState().refreshToken;
  if (!refresh_token) return null;
  const res = await fetch(`${BASE}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token }),
  });
  if (!res.ok) {
    useAuthStore.getState().clear();
    return null;
  }
  const t: Tokens = await res.json();
  useAuthStore.getState().setTokens(t.access_token, t.refresh_token);
  return t.access_token;
}

async function rawFetch(path: string, init: RequestInit, token: string | null): Promise<Response> {
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  return fetch(`${BASE}${path}`, { ...init, headers });
}

async function req<T>(path: string, init: RequestInit = {}): Promise<T> {
  let token = useAuthStore.getState().accessToken;
  let res = await rawFetch(path, init, token);
  // Transparent single-shot refresh on expiry.
  if (res.status === 401 && token) {
    token = await tryRefresh();
    if (token) res = await rawFetch(path, init, token);
  }
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Request failed (${res.status})`);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export const api = {
  // ---- auth ----
  register: (email: string, password: string, full_name?: string) =>
    req<Tokens>("/api/v1/auth/register", { method: "POST", body: JSON.stringify({ email, password, full_name }) }),
  login: (email: string, password: string) =>
    req<Tokens>("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  logout: async () => {
    const refresh_token = useAuthStore.getState().refreshToken;
    if (refresh_token) {
      await req<void>("/api/v1/auth/logout", { method: "POST", body: JSON.stringify({ refresh_token }) }).catch(() => {});
    }
    useAuthStore.getState().clear();
  },
  requestPasswordReset: (email: string) =>
    req<{ message: string; reset_token?: string }>("/api/v1/auth/password-reset/request", {
      method: "POST", body: JSON.stringify({ email }),
    }),
  confirmPasswordReset: (token: string, new_password: string) =>
    req<void>("/api/v1/auth/password-reset/confirm", { method: "POST", body: JSON.stringify({ token, new_password }) }),
  verifyEmail: (token: string) =>
    req<UserPublic>("/api/v1/auth/verify-email", { method: "POST", body: JSON.stringify({ token }) }),

  // ---- users ----
  me: () => req<UserPublic>("/api/v1/users/me"),
  updateProfile: (full_name?: string, avatar_url?: string) =>
    req<UserPublic>("/api/v1/users/me", { method: "PATCH", body: JSON.stringify({ full_name, avatar_url }) }),
  usage: () => req<UsageStats>("/api/v1/users/me/usage"),
  listApiKeys: () => req<ApiKeyPublic[]>("/api/v1/users/me/api-keys"),
  createApiKey: (name: string) =>
    req<ApiKeyCreated>("/api/v1/users/me/api-keys", { method: "POST", body: JSON.stringify({ name }) }),
  revokeApiKey: (id: string) => req<void>(`/api/v1/users/me/api-keys/${id}`, { method: "DELETE" }),

  // ---- videos ----
  listVideos: () => req<Video[]>("/api/v1/videos"),
  getVideo: (id: string) => req<Video>(`/api/v1/videos/${id}`),
  uploadVideo: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return req<Video>("/api/v1/videos/upload", { method: "POST", body: fd });
  },
  deleteVideo: (id: string) => req<void>(`/api/v1/videos/${id}`, { method: "DELETE" }),

  // ---- jobs ----
  listJobs: () => req<Job[]>("/api/v1/jobs"),
  getJob: (id: string) => req<Job>(`/api/v1/jobs/${id}`),
  createJob: (video_id: string, target_language: string, mode: JobMode, source_language?: string) =>
    req<Job>("/api/v1/jobs", { method: "POST", body: JSON.stringify({ video_id, target_language, mode, source_language }) }),
  cancelJob: (id: string) => req<void>(`/api/v1/jobs/${id}`, { method: "DELETE" }),
  /**
   * Fetch the finished result video as an authenticated blob URL. The result endpoint
   * requires a Bearer header, so it cannot be loaded via a raw <video src>/<a href>.
   * Caller is responsible for URL.revokeObjectURL when done.
   */
  fetchResultBlobUrl: async (id: string): Promise<string> => {
    let token = useAuthStore.getState().accessToken;
    let res = await rawFetch(`/api/v1/jobs/${id}/result`, {}, token);
    if (res.status === 401 && token) {
      token = await tryRefresh();
      if (token) res = await rawFetch(`/api/v1/jobs/${id}/result`, {}, token);
    }
    if (!res.ok) throw new Error(`Result download failed (${res.status})`);
    return URL.createObjectURL(await res.blob());
  },

  // ---- websocket ----
  wsUrl: (id: string, token: string) =>
    `${(process.env.NEXT_PUBLIC_WS_URL ?? BASE).replace(/^http/, "ws")}/api/v1/ws/jobs/${id}?token=${token}`,
};

/** Human-readable file size. */
export function humanSize(bytes: number): string {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const i = Math.min(units.length - 1, Math.floor(Math.log(bytes) / Math.log(1024)));
  return `${(bytes / 1024 ** i).toFixed(i ? 1 : 0)} ${units[i]}`;
}
