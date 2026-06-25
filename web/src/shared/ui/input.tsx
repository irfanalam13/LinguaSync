import { cn } from "@/shared/lib/cn";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
}

/** Themed text input. Use with react-hook-form's register or as a controlled input. */
export const Input = ({ className, label, id, ...props }: InputProps) => {
  const input = (
    <input
      id={id}
      className={cn(
        "w-full rounded-xl border border-border bg-surface px-4 py-3 text-body text-text-primary outline-none transition-colors placeholder:text-text-secondary focus:ring-2 focus:ring-primary/50 disabled:opacity-50",
        className
      )}
      {...props}
    />
  );
  if (!label) return input;
  return (
    <label htmlFor={id} className="block space-y-1.5">
      <span className="text-small text-text-secondary">{label}</span>
      {input}
    </label>
  );
};
