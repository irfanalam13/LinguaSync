"use client";

import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, XCircle, Info, X } from "lucide-react";
import { useToastStore, type ToastKind } from "@/shared/store/toast";

const ICON: Record<ToastKind, React.ReactNode> = {
  success: <CheckCircle2 className="text-success" size={18} />,
  error: <XCircle className="text-danger" size={18} />,
  info: <Info className="text-accent" size={18} />,
};

/** Global toast outlet — mount once near the app root. */
export function Toaster() {
  const toasts = useToastStore((s) => s.toasts);
  const remove = useToastStore((s) => s.remove);
  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-full max-w-sm flex-col gap-2">
      <AnimatePresence initial={false}>
        {toasts.map((t) => (
          <motion.div
            key={t.id}
            layout
            initial={{ opacity: 0, y: 16, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, x: 32 }}
            className="glass pointer-events-auto flex items-start gap-3 rounded-xl p-4 shadow-lg"
          >
            {ICON[t.kind]}
            <p className="flex-1 text-small text-text-primary">{t.message}</p>
            <button onClick={() => remove(t.id)} className="text-text-secondary hover:text-text-primary" aria-label="Dismiss">
              <X size={16} />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
