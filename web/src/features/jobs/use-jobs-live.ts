"use client";

import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api, type Job } from "@/shared/lib/api";
import { useAuthStore } from "@/shared/store/auth";

interface Frame {
  job_id: string; status: string; progress: number;
  stage?: string | null; similarity?: number | null; error?: string | null;
}

const TERMINAL = new Set(["completed", "failed", "cancelled"]);

/**
 * Opens a backend WebSocket (`/api/v1/ws/jobs/{id}`) for each active job and patches the
 * ["jobs"] query cache with each progress frame — the live channel. REST polling in the
 * dashboard remains as a fallback for environments where the WS can't connect.
 */
export function useJobsLive(activeIds: string[]) {
  const qc = useQueryClient();
  const sockets = useRef<Map<string, WebSocket>>(new Map());

  useEffect(() => {
    const token = useAuthStore.getState().accessToken;
    if (!token) return;
    const live = sockets.current;

    // Open sockets for newly-active jobs.
    for (const id of activeIds) {
      if (live.has(id)) continue;
      let ws: WebSocket;
      try {
        ws = new WebSocket(api.wsUrl(id, token));
      } catch {
        continue; // WS unavailable — polling fallback covers it.
      }
      live.set(id, ws);

      ws.onmessage = (ev) => {
        let frame: Frame;
        try { frame = JSON.parse(ev.data); } catch { return; }
        if (!frame.job_id) return;
        qc.setQueryData<Job[]>(["jobs"], (prev) =>
          prev?.map((j) =>
            j.id === frame.job_id
              ? { ...j, status: frame.status, progress: frame.progress,
                  stage: frame.stage ?? undefined, similarity: frame.similarity ?? j.similarity,
                  error: frame.error ?? undefined }
              : j
          )
        );
        if (TERMINAL.has(frame.status)) {
          // Refetch the full record (result_key, timestamps) and usage counters.
          qc.invalidateQueries({ queryKey: ["jobs"] });
          qc.invalidateQueries({ queryKey: ["usage"] });
        }
      };
      ws.onclose = () => { live.delete(id); };
      ws.onerror = () => { try { ws.close(); } catch { /* noop */ } };
    }

    // Close sockets for jobs that are no longer active.
    for (const [id, ws] of live) {
      if (!activeIds.includes(id)) { try { ws.close(); } catch { /* noop */ } live.delete(id); }
    }
  }, [activeIds.join(","), qc]); // eslint-disable-line react-hooks/exhaustive-deps

  // Close everything on unmount.
  useEffect(() => {
    const live = sockets.current;
    return () => { for (const ws of live.values()) { try { ws.close(); } catch { /* noop */ } } live.clear(); };
  }, []);
}
