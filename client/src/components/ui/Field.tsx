import { forwardRef, type InputHTMLAttributes, type ReactNode } from "react";

import { cn } from "@/lib/utils";

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  hint?: ReactNode;
  error?: string;
}

export const Field = forwardRef<HTMLInputElement, FieldProps>(function Field(
  { className, label, hint, error, id, ...props },
  ref
) {
  const inputId = id ?? props.name;
  return (
    <label className="block space-y-2" htmlFor={inputId}>
      <span className="text-sm font-medium">{label}</span>
      <input
        aria-describedby={hint || error ? `${inputId}-description` : undefined}
        aria-invalid={Boolean(error)}
        className={cn(
          "h-11 w-full rounded-xl border bg-background/70 px-3 text-sm shadow-sm transition",
          "placeholder:text-muted-foreground/60 hover:border-muted-foreground/40 focus:border-primary",
          error && "border-danger",
          className
        )}
        id={inputId}
        ref={ref}
        {...props}
      />
      {hint || error ? (
        <span
          className={cn("block text-xs text-muted-foreground", error && "text-danger")}
          id={`${inputId}-description`}
          role={error ? "alert" : undefined}
        >
          {error ?? hint}
        </span>
      ) : null}
    </label>
  );
});
