"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { Loader2, BadgeCheck, XCircle } from "lucide-react";
import { api } from "@/shared/lib/api";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";

function VerifyInner() {
  const params = useSearchParams();
  const token = params.get("token") ?? "";
  const [state, setState] = useState<"loading" | "ok" | "error" | "missing">(token ? "loading" : "missing");
  const [error, setError] = useState<string | null>(null);
  const ran = useRef(false);

  useEffect(() => {
    if (!token || ran.current) return;
    ran.current = true; // guard React 18/19 StrictMode double-invoke
    api.verifyEmail(token).then(() => setState("ok")).catch((e) => { setError((e as Error).message); setState("error"); });
  }, [token]);

  if (state === "loading") {
    return <div className="flex items-center gap-2 text-body text-text-secondary"><Loader2 className="animate-spin" size={18} /> Verifying your email…</div>;
  }
  if (state === "ok") {
    return (
      <>
        <div className="flex items-center gap-2 text-success"><BadgeCheck size={22} /><h1 className="font-heading text-h2">Email verified</h1></div>
        <p className="mt-2 text-body text-text-secondary">Your account is now verified.</p>
        <Link href="/dashboard"><Button className="mt-6 w-full">Go to dashboard</Button></Link>
      </>
    );
  }
  return (
    <>
      <div className="flex items-center gap-2 text-danger"><XCircle size={22} /><h1 className="font-heading text-h2">Verification failed</h1></div>
      <p className="mt-2 text-body text-text-secondary">{state === "missing" ? "No verification token provided." : error}</p>
      <Link href="/login" className="mt-4 inline-block text-small text-text-secondary hover:text-text-primary">Back to sign in</Link>
    </>
  );
}

export default function VerifyEmailPage() {
  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }} className="w-full max-w-md">
        <Card>
          <Suspense fallback={<p className="text-text-secondary">Loading…</p>}>
            <VerifyInner />
          </Suspense>
        </Card>
      </motion.div>
    </main>
  );
}
