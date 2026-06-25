"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LayoutDashboard, Film, KeyRound, User, LogOut, Waves } from "lucide-react";
import { api } from "@/shared/lib/api";
import { toast } from "@/shared/store/toast";
import { cn } from "@/shared/lib/cn";

const LINKS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/videos", label: "Videos", icon: Film },
  { href: "/api-keys", label: "API Keys", icon: KeyRound },
  { href: "/profile", label: "Profile", icon: User },
];

/** Top navigation for the authenticated app shell. */
export function AppNav() {
  const pathname = usePathname();
  const router = useRouter();

  async function signOut() {
    await api.logout();
    toast.info("Signed out");
    router.push("/login");
  }

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-surface/70 backdrop-blur-md">
      <nav className="mx-auto flex max-w-6xl items-center gap-1 px-4 py-3 sm:px-6">
        <Link href="/dashboard" className="mr-4 flex items-center gap-2 font-heading text-h3">
          <Waves className="text-accent" size={22} />
          <span className="hidden sm:inline">VoiceLocalize</span>
        </Link>
        <div className="flex flex-1 items-center gap-1 overflow-x-auto">
          {LINKS.map((l) => {
            const active = pathname === l.href;
            return (
              <Link
                key={l.href}
                href={l.href}
                className={cn(
                  "flex items-center gap-2 rounded-xl px-3 py-2 text-small transition-colors",
                  active ? "bg-white/5 text-text-primary" : "text-text-secondary hover:text-text-primary"
                )}
              >
                <l.icon size={16} />
                <span className="hidden sm:inline">{l.label}</span>
              </Link>
            );
          })}
        </div>
        <button
          onClick={signOut}
          className="flex items-center gap-2 rounded-xl px-3 py-2 text-small text-text-secondary transition-colors hover:text-text-primary"
        >
          <LogOut size={16} />
          <span className="hidden sm:inline">Sign out</span>
        </button>
      </nav>
    </header>
  );
}
