"use client";

import { create } from "zustand";

export type ToastKind = "success" | "error" | "info";
export interface Toast { id: number; kind: ToastKind; message: string; }

interface ToastState {
  toasts: Toast[];
  push: (kind: ToastKind, message: string) => void;
  remove: (id: number) => void;
}

let _seq = 0;

export const useToastStore = create<ToastState>((set) => ({
  toasts: [],
  push: (kind, message) => {
    const id = ++_seq;
    set((s) => ({ toasts: [...s.toasts, { id, kind, message }] }));
    setTimeout(() => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })), 4000);
  },
  remove: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}));

/** Imperative helpers usable from event handlers / mutations. */
export const toast = {
  success: (m: string) => useToastStore.getState().push("success", m),
  error: (m: string) => useToastStore.getState().push("error", m),
  info: (m: string) => useToastStore.getState().push("info", m),
};
