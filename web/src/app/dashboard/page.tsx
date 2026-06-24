"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type JobMode } from "@/shared/lib/api";
import { useAuthStore } from "@/shared/store/auth";
import { UploadDropzone } from "@/features/upload/upload-dropzone";
import { JobCard } from "@/features/jobs/job-card";
import { Card } from "@/shared/ui/card";
import { Button } from "@/shared/ui/button";

const MODES: { value: JobMode; label: string }[] = [
  { value: "translate", label: "Translate" },
  { value: "preserve", label: "Preserve voice" },
  { value: "clone", label: "Clone voice" },
  { value: "localize", label: "Full localize (lip-sync)" },
];

export default function Dashboard() {
  const router = useRouter();
  const qc = useQueryClient();
  const isAuthed = useAuthStore((s) => s.isAuthenticated);
  const [target, setTarget] = useState("ne");
  const [mode, setMode] = useState<JobMode>("localize");
  const [videoId, setVideoId] = useState<string | null>(null);

  useEffect(() => { if (!isAuthed()) router.replace("/login"); }, [isAuthed, router]);

  const jobs = useQuery({
    queryKey: ["jobs"],
    queryFn: api.listJobs,
    refetchInterval: (q) =>
      (q.state.data ?? []).some((j) => ["queued", "running"].includes(j.status)) ? 1500 : false,
  });
  const usage = useQuery({ queryKey: ["usage"], queryFn: api.usage });

  const createJob = useMutation({
    mutationFn: () => api.createJob(videoId!, target, mode),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["jobs"] }); qc.invalidateQueries({ queryKey: ["usage"] }); setVideoId(null); },
  });

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="font-heading text-h2">Dashboard</h1>
          <p className="text-body text-text-secondary">Upload, localize and download your videos.</p>
        </div>
        <Button variant="ghost" onClick={() => { useAuthStore.getState().clear(); router.push("/login"); }}>Sign out</Button>
      </header>

      {usage.data && (
        <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[["Videos", usage.data.videos], ["Jobs", usage.data.jobs_total], ["Completed", usage.data.jobs_completed], ["Running", usage.data.jobs_running]].map(([k, v]) => (
            <Card key={k as string} className="text-center">
              <div className="text-h2 font-bold gradient-text">{v as number}</div>
              <div className="text-small text-text-secondary">{k as string}</div>
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
            <div className="mt-4 flex flex-wrap gap-4">
              <select value={target} onChange={(e) => setTarget(e.target.value)} className="rounded-xl border border-border bg-surface px-4 py-2">
                <option value="ne">→ Nepali</option>
                <option value="en">→ English</option>
              </select>
              <select value={mode} onChange={(e) => setMode(e.target.value as JobMode)} className="rounded-xl border border-border bg-surface px-4 py-2">
                {MODES.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
              </select>
              <Button onClick={() => createJob.mutate()} disabled={createJob.isPending}>
                {createJob.isPending ? "Starting…" : "Start localization"}
              </Button>
            </div>
            {createJob.error && <p className="mt-2 text-small text-danger">{(createJob.error as Error).message}</p>}
          </Card>
        )}
      </section>

      <section className="mt-12">
        <h2 className="font-heading text-h3">Your jobs</h2>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          {jobs.isLoading && <p className="text-text-secondary">Loading…</p>}
          {jobs.data?.length === 0 && <p className="text-text-secondary">No jobs yet — upload a video to begin.</p>}
          {jobs.data?.map((j) => <JobCard key={j.id} job={j} />)}
        </div>
      </section>
    </main>
  );
}
