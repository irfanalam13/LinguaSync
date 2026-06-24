"use client";

import { motion } from "framer-motion";
import { Download, Loader2, CheckCircle2, XCircle, Clock } from "lucide-react";
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

/** Job monitoring card: live status, progress bar, similarity, result download + preview. */
export function JobCard({ job }: { job: Job }) {
  const done = job.status === "completed";
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

      {done && (
        <div className="mt-4 space-y-3">
          <video src={api.resultUrl(job.id)} controls className="w-full rounded-xl border border-border" />
          <a href={api.resultUrl(job.id)} download>
            <Button className="w-full"><Download size={16} /> Download localized video</Button>
          </a>
        </div>
      )}
    </Card>
  );
}
