"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Film, Trash2, Loader2 } from "lucide-react";
import { api, humanSize, type Video } from "@/shared/lib/api";
import { Card } from "@/shared/ui/card";
import { Button } from "@/shared/ui/button";
import { toast } from "@/shared/store/toast";

function VideoRow({ video }: { video: Video }) {
  const qc = useQueryClient();
  const del = useMutation({
    mutationFn: () => api.deleteVideo(video.id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["videos"] }); qc.invalidateQueries({ queryKey: ["usage"] }); toast.success("Video deleted"); },
    onError: (e) => toast.error((e as Error).message),
  });
  return (
    <Card className="flex items-center justify-between gap-4">
      <div className="flex min-w-0 items-center gap-3">
        <Film className="shrink-0 text-accent" size={20} />
        <div className="min-w-0">
          <p className="truncate font-medium">{video.filename}</p>
          <p className="text-small text-text-secondary">
            {humanSize(video.size_bytes)}
            {video.duration_s ? ` · ${video.duration_s.toFixed(1)}s` : ""}
            {` · ${new Date(video.created_at).toLocaleDateString()}`}
            {` · ${video.status}`}
          </p>
        </div>
      </div>
      <Button variant="ghost" size="sm" onClick={() => del.mutate()} disabled={del.isPending} aria-label="Delete video">
        {del.isPending ? <Loader2 className="animate-spin" size={16} /> : <Trash2 size={16} className="text-danger" />}
      </Button>
    </Card>
  );
}

export default function VideosPage() {
  const videos = useQuery({ queryKey: ["videos"], queryFn: api.listVideos });
  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <header>
        <h1 className="font-heading text-h2">Your videos</h1>
        <p className="text-body text-text-secondary">Source videos you’ve uploaded. Deleting one removes it from storage.</p>
      </header>
      <div className="mt-8 space-y-3">
        {videos.isLoading && <p className="text-text-secondary">Loading…</p>}
        {videos.error && <p className="text-danger">{(videos.error as Error).message}</p>}
        {videos.data?.length === 0 && <p className="text-text-secondary">No videos yet — upload one from the dashboard.</p>}
        {videos.data?.map((v) => <VideoRow key={v.id} video={v} />)}
      </div>
    </main>
  );
}
