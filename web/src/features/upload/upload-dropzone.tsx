"use client";

import { useCallback, useRef, useState } from "react";
import { motion } from "framer-motion";
import { UploadCloud, FileVideo } from "lucide-react";
import { api } from "@/shared/lib/api";
import { cn } from "@/shared/lib/cn";

const ALLOWED = [".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"];

export function UploadDropzone({ onUploaded }: { onUploaded: (videoId: string) => void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  const handleFile = useCallback(async (file: File) => {
    setError(null);
    const ext = "." + (file.name.split(".").pop() ?? "").toLowerCase();
    if (!ALLOWED.includes(ext)) { setError(`Unsupported type ${ext}`); return; }
    setFileName(file.name);
    setBusy(true);
    try {
      const video = await api.uploadVideo(file);
      onUploaded(video.id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }, [onUploaded]);

  return (
    <div>
      <motion.div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); const f = e.dataTransfer.files?.[0]; if (f) handleFile(f); }}
        onClick={() => inputRef.current?.click()}
        animate={{ scale: dragging ? 1.01 : 1 }}
        className={cn(
          "glass flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed p-12 text-center transition-colors",
          dragging ? "border-primary" : "border-border"
        )}
      >
        {busy ? (
          <>
            <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: "linear" }}>
              <UploadCloud className="text-primary" size={40} />
            </motion.div>
            <p className="mt-4 text-body">Uploading {fileName}…</p>
          </>
        ) : (
          <>
            {fileName ? <FileVideo className="text-accent" size={40} /> : <UploadCloud className="text-text-secondary" size={40} />}
            <p className="mt-4 text-body-lg">Drag & drop a video, or click to browse</p>
            <p className="mt-1 text-small text-text-secondary">{ALLOWED.join(" · ")} · up to 500 MB</p>
          </>
        )}
        <input ref={inputRef} type="file" accept="video/*" className="hidden"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }} />
      </motion.div>
      {error && <p className="mt-2 text-small text-danger">{error}</p>}
    </div>
  );
}
