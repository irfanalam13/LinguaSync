"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion } from "framer-motion";
import { api } from "@/shared/lib/api";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { Input } from "@/shared/ui/input";

const schema = z.object({ new_password: z.string().min(8, "At least 8 characters") });
type Form = z.infer<typeof schema>;

function ResetForm() {
  const params = useSearchParams();
  const token = params.get("token") ?? "";
  const { register, handleSubmit, formState } = useForm<Form>({ resolver: zodResolver(schema) });
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(data: Form) {
    setError(null);
    try {
      await api.confirmPasswordReset(token, data.new_password);
      setDone(true);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  if (!token) {
    return (
      <>
        <h1 className="font-heading text-h2">Reset password</h1>
        <p className="mt-2 text-body text-danger">Missing or invalid reset token. Request a new link.</p>
        <Link href="/forgot-password" className="mt-4 inline-block text-small text-text-secondary hover:text-text-primary">Request reset link</Link>
      </>
    );
  }

  if (done) {
    return (
      <>
        <h1 className="font-heading text-h2">Password updated</h1>
        <p className="mt-2 text-body text-success">Your password has been reset.</p>
        <Link href="/login"><Button className="mt-6 w-full">Sign in</Button></Link>
      </>
    );
  }

  return (
    <>
      <h1 className="font-heading text-h2">Choose a new password</h1>
      <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-4">
        <Input {...register("new_password")} type="password" placeholder="New password" />
        {formState.errors.new_password && <p className="text-small text-danger">{formState.errors.new_password.message}</p>}
        {error && <p className="text-small text-danger">{error}</p>}
        <Button type="submit" className="w-full" disabled={formState.isSubmitting}>
          {formState.isSubmitting ? "Updating…" : "Update password"}
        </Button>
      </form>
    </>
  );
}

export default function ResetPasswordPage() {
  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }} className="w-full max-w-md">
        <Card>
          <Suspense fallback={<p className="text-text-secondary">Loading…</p>}>
            <ResetForm />
          </Suspense>
        </Card>
      </motion.div>
    </main>
  );
}
