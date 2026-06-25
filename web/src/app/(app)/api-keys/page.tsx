"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { KeyRound, Copy, Check, Loader2, Ban } from "lucide-react";
import { api, type ApiKeyCreated, type ApiKeyPublic } from "@/shared/lib/api";
import { Card } from "@/shared/ui/card";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { toast } from "@/shared/store/toast";

/** Banner shown once after creation — the raw key is never retrievable again. */
function NewKeyBanner({ created, onDismiss }: { created: ApiKeyCreated; onDismiss: () => void }) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    try { await navigator.clipboard.writeText(created.key); setCopied(true); setTimeout(() => setCopied(false), 2000); }
    catch { toast.error("Couldn’t copy to clipboard"); }
  }
  return (
    <Card className="border-accent/50">
      <p className="text-small text-text-secondary">Copy your new key now — it won’t be shown again.</p>
      <div className="mt-3 flex items-center gap-2">
        <code className="flex-1 truncate rounded-lg bg-surface px-3 py-2 font-mono text-small">{created.key}</code>
        <Button size="sm" variant="outline" onClick={copy}>{copied ? <Check size={16} /> : <Copy size={16} />}</Button>
      </div>
      <Button size="sm" variant="ghost" className="mt-3" onClick={onDismiss}>Done</Button>
    </Card>
  );
}

function KeyRow({ k }: { k: ApiKeyPublic }) {
  const qc = useQueryClient();
  const revoke = useMutation({
    mutationFn: () => api.revokeApiKey(k.id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["api-keys"] }); toast.success("Key revoked"); },
    onError: (e) => toast.error((e as Error).message),
  });
  return (
    <Card className="flex items-center justify-between gap-4">
      <div className="flex min-w-0 items-center gap-3">
        <KeyRound className="shrink-0 text-accent" size={18} />
        <div className="min-w-0">
          <p className="truncate font-medium">{k.name} {!k.is_active && <span className="text-small text-text-secondary">(revoked)</span>}</p>
          <p className="font-mono text-small text-text-secondary">{k.prefix}… · {new Date(k.created_at).toLocaleDateString()}</p>
        </div>
      </div>
      {k.is_active && (
        <Button variant="ghost" size="sm" onClick={() => revoke.mutate()} disabled={revoke.isPending}>
          {revoke.isPending ? <Loader2 className="animate-spin" size={16} /> : <><Ban size={14} className="text-danger" /> Revoke</>}
        </Button>
      )}
    </Card>
  );
}

export default function ApiKeysPage() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [created, setCreated] = useState<ApiKeyCreated | null>(null);
  const keys = useQuery({ queryKey: ["api-keys"], queryFn: api.listApiKeys });

  const create = useMutation({
    mutationFn: () => api.createApiKey(name.trim()),
    onSuccess: (k) => { setCreated(k); setName(""); qc.invalidateQueries({ queryKey: ["api-keys"] }); },
    onError: (e) => toast.error((e as Error).message),
  });

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <header>
        <h1 className="font-heading text-h2">API keys</h1>
        <p className="text-body text-text-secondary">Programmatic access tokens for the platform API.</p>
      </header>

      <Card className="mt-8">
        <form
          onSubmit={(e) => { e.preventDefault(); if (name.trim()) create.mutate(); }}
          className="flex flex-wrap items-end gap-3"
        >
          <div className="flex-1 min-w-[200px]">
            <Input label="Key name" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. CI pipeline" maxLength={120} />
          </div>
          <Button type="submit" disabled={!name.trim() || create.isPending}>
            {create.isPending ? "Creating…" : "Create key"}
          </Button>
        </form>
      </Card>

      {created && <div className="mt-4"><NewKeyBanner created={created} onDismiss={() => setCreated(null)} /></div>}

      <div className="mt-6 space-y-3">
        {keys.isLoading && <p className="text-text-secondary">Loading…</p>}
        {keys.error && <p className="text-danger">{(keys.error as Error).message}</p>}
        {keys.data?.length === 0 && <p className="text-text-secondary">No API keys yet.</p>}
        {keys.data?.map((k) => <KeyRow key={k.id} k={k} />)}
      </div>
    </main>
  );
}
