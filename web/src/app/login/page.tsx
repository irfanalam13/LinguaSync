"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion } from "framer-motion";
import { api } from "@/shared/lib/api";
import { useAuthStore } from "@/shared/store/auth";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(8, "At least 8 characters"),
  full_name: z.string().optional(),
});
type Form = z.infer<typeof schema>;

export default function LoginPage() {
  const router = useRouter();
  const setTokens = useAuthStore((s) => s.setTokens);
  const [mode, setMode] = useState<"login" | "register">("login");
  const [error, setError] = useState<string | null>(null);
  const { register, handleSubmit, formState } = useForm<Form>({ resolver: zodResolver(schema) });

  async function onSubmit(data: Form) {
    setError(null);
    try {
      const tokens =
        mode === "login"
          ? await api.login(data.email, data.password)
          : await api.register(data.email, data.password, data.full_name);
      setTokens(tokens.access_token, tokens.refresh_token);
      router.push("/dashboard");
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }} className="w-full max-w-md">
        <Card>
          <h1 className="font-heading text-h2">{mode === "login" ? "Welcome back" : "Create account"}</h1>
          <p className="mt-1 text-body text-text-secondary">Localize videos in your own voice.</p>
          <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-4">
            {mode === "register" && (
              <input {...register("full_name")} placeholder="Full name"
                className="w-full rounded-xl border border-border bg-surface px-4 py-3 text-body outline-none focus:ring-2 focus:ring-primary/50" />
            )}
            <input {...register("email")} type="email" placeholder="Email"
              className="w-full rounded-xl border border-border bg-surface px-4 py-3 text-body outline-none focus:ring-2 focus:ring-primary/50" />
            {formState.errors.email && <p className="text-small text-danger">{formState.errors.email.message}</p>}
            <input {...register("password")} type="password" placeholder="Password"
              className="w-full rounded-xl border border-border bg-surface px-4 py-3 text-body outline-none focus:ring-2 focus:ring-primary/50" />
            {formState.errors.password && <p className="text-small text-danger">{formState.errors.password.message}</p>}
            {error && <p className="text-small text-danger">{error}</p>}
            {mode === "login" && (
              <a href="/forgot-password" className="block text-right text-small text-text-secondary hover:text-text-primary">Forgot password?</a>
            )}
            <Button type="submit" className="w-full" disabled={formState.isSubmitting}>
              {formState.isSubmitting ? "Please wait…" : mode === "login" ? "Sign in" : "Sign up"}
            </Button>
          </form>
          <button onClick={() => setMode(mode === "login" ? "register" : "login")}
            className="mt-4 text-small text-text-secondary hover:text-text-primary">
            {mode === "login" ? "Need an account? Sign up" : "Have an account? Sign in"}
          </button>
        </Card>
      </motion.div>
    </main>
  );
}
