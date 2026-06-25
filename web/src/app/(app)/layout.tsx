"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/shared/store/auth";
import { AppNav } from "@/widgets/app-nav/app-nav";

/**
 * Authenticated app shell. Guards every nested route: unauthenticated users are
 * redirected to /login. Renders the persistent top navigation.
 */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const isAuthed = useAuthStore((s) => s.isAuthenticated);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    // Wait for Zustand persist to rehydrate from localStorage before deciding.
    if (!isAuthed()) router.replace("/login");
    else setReady(true);
  }, [isAuthed, router]);

  if (!ready) return null;

  return (
    <div className="min-h-screen">
      <AppNav />
      {children}
    </div>
  );
}
