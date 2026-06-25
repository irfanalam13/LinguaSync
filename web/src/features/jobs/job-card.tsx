"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Download, Loader2, CheckCircle2, XCircle, Clock, Ban } from "lucide-react";
import { api, type Job } from "@/shared/lib/api";
import { Card } from "@/shared/ui/card";
import { Button } from "@/shared/ui/button";

const STATUS_ICON: Record<string, React.ReactNode> = {
  queued: <Clock className="text-text-secondary" size={18} />,
  running: <Loader2 className="animate-spin text-accent" size={18} />,
  completed: <CheckCircle2 className="text-success" size={18} />,
  failed: <XCircle className="text-danger" size={18} />,
  cancelled: <XCircle className="text-text-secondary" size={18} />,
};

/** Job monitoring card: live status, progress bar, similarity, cancel, result download + preview. */
export function JobCard({ job }: { job: Job }) {
  const qc = useQueryClient();
  const done = job.status === "completed";
  const cancellable = job.status === "queued" || job.status === "running";

  // The result endpoint is authenticated, so we must fetch it with the Bearer header
  // and expose it as an object URL — a raw <video src>/<a href> would 401.
  const [resultUrl, setResultUrl] = useState<string | null>(null);
  const [resultError, setResultError] = useState<string | null>(null);

  useEffect(() => {
    if (!done) return;
    let revoked = false;
    let url: string | null = null;
    api
      .fetchResultBlobUrl(job.id)
      .then((u) => { if (!revoked) { url = u; setResultUrl(u); } else URL.revokeObjectURL(u); })
      .catch((e) => setResultError((e as Error).message));
    return () => { revoked = true; if (url) URL.revokeObjectURL(url); };
  }, [done, job.id]);

  const cancel = useMutation({
    mutationFn: () => api.cancelJob(job.id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["jobs"] }); qc.invalidateQueries({ queryKey: ["usage"] }); },
  });

  return (
    <Card>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {STATUS_ICON[job.status]}
          <span className="font-medium capitalize">{job.mode}</span>
          <span className="text-small text-text-secondary">→ {job.target_language.toUpperCase()}</span>
        </div>
        <span className="text-small text-text-secondary">{job.status}{job.stage ? ` · ${job.stage}` : ""}</span>
      </div>

      <div className="mt-4 h-2 overflow-hidden rounded-full bg-surface">
        <motion.div className="h-full bg-gradient-to-r from-primary to-accent"
          initial={{ width: 0 }} animate={{ width: `${job.progress}%` }} transition={{ duration: 0.4 }} />
      </div>

      <div className="mt-3 flex items-center justify-between text-small text-text-secondary">
        <span>{job.progress}%</span>
        {job.similarity != null && <span>speaker similarity {(job.similarity * 100).toFixed(0)}%</span>}
      </div>

      {job.error && <p className="mt-2 text-small text-danger">{job.error}</p>}

      {cancellable && (
        <div className="mt-4">
          <Button variant="outline" size="sm" onClick={() => cancel.mutate()} disabled={cancel.isPending}>
            <Ban size={14} /> {cancel.isPending ? "Cancelling…" : "Cancel job"}
          </Button>
        </div>
      )}

      {done && (
        <div className="mt-4 space-y-3">
          {resultUrl ? (
            <>
              <video src={resultUrl} controls className="w-full rounded-xl border border-border" />
              <a href={resultUrl} download={`localized_${job.id}.mp4`}>
                <Button className="w-full"><Download size={16} /> Download localized video</Button>
              </a>
            </>
          ) : resultError ? (
            <p className="text-small text-danger">Couldn’t load result: {resultError}</p>
          ) : (
            <div className="flex items-center gap-2 text-small text-text-secondary">
              <Loader2 className="animate-spin" size={16} /> Preparing result…
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
