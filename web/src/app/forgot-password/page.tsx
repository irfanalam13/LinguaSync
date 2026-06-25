"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion } from "framer-motion";
import { api } from "@/shared/lib/api";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { Input } from "@/shared/ui/input";

const schema = z.object({ email: z.string().email() });
type Form = z.infer<typeof schema>;

export default function ForgotPasswordPage() {
  const { register, handleSubmit, formState } = useForm<Form>({ resolver: zodResolver(schema) });
  const [message, setMessage] = useState<string | null>(null);
  const [resetToken, setResetToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(data: Form) {
    setError(null);
    try {
      const res = await api.requestPasswordReset(data.email);
      setMessage(res.message);
      // The backend returns the token directly while email delivery is a stub (dev).
      if (res.reset_token) setResetToken(res.reset_token);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }} className="w-full max-w-md">
        <Card>
          <h1 className="font-heading text-h2">Reset password</h1>
          <p className="mt-1 text-body text-text-secondary">Enter your email and we’ll send a reset link.</p>

          {message ? (
            <div className="mt-6 space-y-4">
              <p className="text-body text-success">{message}</p>
              {resetToken && (
                <Link href={`/reset-password?token=${encodeURIComponent(resetToken)}`}>
                  <Button className="w-full">Continue to reset</Button>
                </Link>
              )}
              <Link href="/login" className="block text-center text-small text-text-secondary hover:text-text-primary">Back to sign in</Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-4">
              <Input {...register("email")} type="email" placeholder="Email" />
              {formState.errors.email && <p className="text-small text-danger">{formState.errors.email.message}</p>}
              {error && <p className="text-small text-danger">{error}</p>}
              <Button type="submit" className="w-full" disabled={formState.isSubmitting}>
                {formState.isSubmitting ? "Sending…" : "Send reset link"}
              </Button>
              <Link href="/login" className="block text-center text-small text-text-secondary hover:text-text-primary">Back to sign in</Link>
            </form>
          )}
        </Card>
      </motion.div>
    </main>
  );
}
