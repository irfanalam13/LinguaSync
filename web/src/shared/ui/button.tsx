"use client";

import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/shared/lib/cn";

const button = cva(
  "inline-flex items-center justify-center gap-2 rounded-xl font-medium transition-all focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:opacity-50 disabled:pointer-events-none",
  {
    variants: {
      variant: {
        primary: "bg-primary text-white hover:bg-primary/90 shadow-lg shadow-primary/20",
        secondary: "bg-secondary text-white hover:bg-secondary/90",
        ghost: "bg-transparent text-text-secondary hover:text-text-primary hover:bg-white/5",
        outline: "border border-border text-text-primary hover:bg-white/5",
      },
      size: { sm: "h-9 px-3 text-small", md: "h-11 px-5 text-body", lg: "h-13 px-7 text-body-lg" },
    },
    defaultVariants: { variant: "primary", size: "md" },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof button> {}

export function Button({ className, variant, size, ...props }: ButtonProps) {
  return <button className={cn(button({ variant, size }), className)} {...props} />;
}
