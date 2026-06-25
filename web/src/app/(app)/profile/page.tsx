"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BadgeCheck, AlertCircle } from "lucide-react";
import { api } from "@/shared/lib/api";
import { Card } from "@/shared/ui/card";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { toast } from "@/shared/store/toast";

export default function ProfilePage() {
  const qc = useQueryClient();
  const me = useQuery({ queryKey: ["me"], queryFn: api.me });
  const [fullName, setFullName] = useState("");
  const [avatarUrl, setAvatarUrl] = useState("");

  useEffect(() => {
    if (me.data) {
      setFullName(me.data.full_name ?? "");
      setAvatarUrl(me.data.avatar_url ?? "");
    }
  }, [me.data]);

  const save = useMutation({
    mutationFn: () => api.updateProfile(fullName, avatarUrl),
    onSuccess: (u) => { qc.setQueryData(["me"], u); toast.success("Profile updated"); },
    onError: (e) => toast.error((e as Error).message),
  });

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <header>
        <h1 className="font-heading text-h2">Profile</h1>
        <p className="text-body text-text-secondary">Manage your account details.</p>
      </header>

      {me.isLoading && <p className="mt-8 text-text-secondary">Loading…</p>}
      {me.error && <p className="mt-8 text-danger">{(me.error as Error).message}</p>}

      {me.data && (
        <Card className="mt-8 space-y-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-small text-text-secondary">Email</p>
              <p className="font-medium">{me.data.email}</p>
            </div>
            <span className={`flex items-center gap-1.5 text-small ${me.data.is_verified ? "text-success" : "text-text-secondary"}`}>
              {me.data.is_verified ? <BadgeCheck size={16} /> : <AlertCircle size={16} />}
              {me.data.is_verified ? "Verified" : "Unverified"}
            </span>
          </div>

          <form
            onSubmit={(e) => { e.preventDefault(); save.mutate(); }}
            className="space-y-4"
          >
            <Input label="Full name" value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Your name" maxLength={120} />
            <Input label="Avatar URL" value={avatarUrl} onChange={(e) => setAvatarUrl(e.target.value)} placeholder="https://…" maxLength={512} />
            <Button type="submit" disabled={save.isPending}>{save.isPending ? "Saving…" : "Save changes"}</Button>
          </form>
        </Card>
      )}
    </main>
  );
}
