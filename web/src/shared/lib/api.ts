/**
 * Typed API client for the Voice_backend platform API. Reads the access token from the
 * auth store and attaches it as a Bearer header. Base URL defaults to same-origin
 * (Next rewrites proxy /api/* to the backend in dev).
 */
import { useAuthStore } from "@/shared/store/auth";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export interface Tokens { access_token: string; refresh_token: string; token_type: string; }
export interface UserPublic { id: string; email: string; full_name?: string; avatar_url?: string; is_active: boolean; is_verified: boolean; }
export interface Video { id: string; filename: string; size_bytes: number; duration_s?: number; status: string; created_at: string; }
export type JobMode = "translate" | "preserve" | "clone" | "localize";
export interface Job {
  id: string; video_id: string; target_language: string; source_language?: string;
  mode: string; status: string; progress: number; stage?: string; similarity?: number;
  result_key?: string; error?: string; created_at: string;
}

async function req<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = useAuthStore.getState().accessToken;
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Request failed (${res.status})`);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export const api = {
  register: (email: string, password: string, full_name?: string) =>
    req<Tokens>("/api/v1/auth/register", { method: "POST", body: JSON.stringify({ email, password, full_name }) }),
  login: (email: string, password: string) =>
    req<Tokens>("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  me: () => req<UserPublic>("/api/v1/users/me"),
  usage: () => req<Record<string, number>>("/api/v1/users/me/usage"),
  listVideos: () => req<Video[]>("/api/v1/videos"),
  uploadVideo: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return req<Video>("/api/v1/videos/upload", { method: "POST", body: fd });
  },
  listJobs: () => req<Job[]>("/api/v1/jobs"),
  getJob: (id: string) => req<Job>(`/api/v1/jobs/${id}`),
  createJob: (video_id: string, target_language: string, mode: JobMode, source_language?: string) =>
    req<Job>("/api/v1/jobs", { method: "POST", body: JSON.stringify({ video_id, target_language, mode, source_language }) }),
  resultUrl: (id: string) => `${BASE}/api/v1/jobs/${id}/result`,
  wsUrl: (id: string, token: string) =>
    `${(process.env.NEXT_PUBLIC_WS_URL ?? BASE).replace(/^http/, "ws")}/api/v1/ws/jobs/${id}?token=${token}`,
};
