"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type JobMode } from "@/shared/lib/api";
import { useJobsLive } from "@/features/jobs/use-jobs-live";
import { UploadDropzone } from "@/features/upload/upload-dropzone";
import { JobCard } from "@/features/jobs/job-card";
import { Card } from "@/shared/ui/card";
import { Button } from "@/shared/ui/button";
import { toast } from "@/shared/store/toast";

const MODES: { value: JobMode; label: string; hint: string }[] = [
  { value: "translate", label: "Translate", hint: "Phase 1 · synthetic voice" },
  { value: "preserve", label: "Preserve voice", hint: "Phase 2 · keep speaker timbre" },
  { value: "clone", label: "Clone voice", hint: "Phase 3 · clone identity" },
  { value: "localize", label: "Full localize (lip-sync)", hint: "Phase 4 · clone + Wav2Lip" },
];

export default function Dashboard() {
  const qc = useQueryClient();
  const [target, setTarget] = useState("ne");
  const [mode, setMode] = useState<JobMode>("localize");
  const [videoId, setVideoId] = useState<string | null>(null);

  const jobs = useQuery({
    queryKey: ["jobs"],
    queryFn: api.listJobs,
    // Polling is the fallback channel; the WebSocket below drives fast live updates.
    refetchInterval: (q) =>
      (q.state.data ?? []).some((j) => ["queued", "running"].includes(j.status)) ? 4000 : false,
  });
  const usage = useQuery({ queryKey: ["usage"], queryFn: api.usage });

  const activeIds = useMemo(
    () => (jobs.data ?? []).filter((j) => ["queued", "running"].includes(j.status)).map((j) => j.id),
    [jobs.data]
  );
  useJobsLive(activeIds);

  const createJob = useMutation({
    mutationFn: () => api.createJob(videoId!, target, mode),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["jobs"] });
      qc.invalidateQueries({ queryKey: ["usage"] });
      setVideoId(null);
      toast.success("Job started — track progress below");
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const stats = usage.data;

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <header>
        <h1 className="font-heading text-h2">Dashboard</h1>
        <p className="text-body text-text-secondary">Upload, localize and download your videos.</p>
      </header>

      {stats && (
        <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
          {([
            ["Videos", stats.videos],
            ["Total jobs", stats.jobs_total],
            ["Completed", stats.jobs_completed],
            ["Running", stats.jobs_running],
          ] as const).map(([k, v]) => (
            <Card key={k} className="text-center">
              <div className="text-h2 font-bold gradient-text">{v}</div>
              <div className="text-small text-text-secondary">{k}</div>
            </Card>
          ))}
        </div>
      )}

      <section className="mt-10">
        <h2 className="font-heading text-h3">New localization</h2>
        <div className="mt-4"><UploadDropzone onUploaded={setVideoId} /></div>
        {videoId && (
          <Card className="mt-4">
            <p className="text-body">Video uploaded. Configure the job:</p>
            <div className="mt-4 flex flex-wrap items-end gap-4">
              <label className="space-y-1.5">
                <span className="block text-small text-text-secondary">Target language</span>
                <select value={target} onChange={(e) => setTarget(e.target.value)} className="rounded-xl border border-border bg-surface px-4 py-2 text-text-primary">
                  <option value="ne">→ Nepali</option>
                  <option value="en">→ English</option>
                </select>
              </label>
              <label className="space-y-1.5">
                <span className="block text-small text-text-secondary">Mode</span>
                <select value={mode} onChange={(e) => setMode(e.target.value as JobMode)} className="rounded-xl border border-border bg-surface px-4 py-2 text-text-primary">
                  {MODES.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
                </select>
              </label>
              <Button onClick={() => createJob.mutate()} disabled={createJob.isPending}>
                {createJob.isPending ? "Starting…" : "Start localization"}
              </Button>
            </div>
            <p className="mt-3 text-small text-text-secondary">{MODES.find((m) => m.value === mode)?.hint}</p>
          </Card>
        )}
      </section>

      <section className="mt-12">
        <h2 className="font-heading text-h3">Your jobs</h2>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          {jobs.isLoading && <p className="text-text-secondary">Loading…</p>}
          {jobs.error && <p className="text-danger">{(jobs.error as Error).message}</p>}
          {jobs.data?.length === 0 && <p className="text-text-secondary">No jobs yet — upload a video to begin.</p>}
          {jobs.data?.map((j) => <JobCard key={j.id} job={j} />)}
        </div>
      </section>
    </main>
  );
}
