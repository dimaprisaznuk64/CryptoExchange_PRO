"use client";

import { cn } from "@/lib/utils";

export function Spinner({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "size-4 animate-spin rounded-full border-2 border-hairline border-t-amber",
        className,
      )}
      aria-label="Loading"
    />
  );
}

export function Button({
  children,
  variant = "primary",
  size = "md",
  loading = false,
  className,
  disabled,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "success" | "danger" | "ghost" | "outline";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
}) {
  const variants: Record<string, string> = {
    primary: "bg-amber text-bg hover:bg-amber/90 disabled:hover:bg-amber",
    success: "bg-bull text-bg hover:bg-bull/90 disabled:hover:bg-bull",
    danger: "bg-bear text-bg hover:bg-bear/90 disabled:hover:bg-bear",
    ghost: "bg-transparent text-ink/70 hover:bg-surface-2 hover:text-ink",
    outline:
      "bg-transparent border border-hairline text-ink hover:border-hairline-strong hover:bg-surface",
  };
  const sizes: Record<string, string> = {
    sm: "px-2.5 py-1 text-[11px]",
    md: "px-3.5 py-1.5 text-xs",
    lg: "px-5 py-2.5 text-sm",
  };

  return (
    <button
      className={cn(
        "inline-flex cursor-pointer items-center justify-center gap-2 rounded-[2px] font-semibold uppercase tracking-wide transition-colors disabled:cursor-not-allowed disabled:opacity-40",
        variants[variant],
        sizes[size],
        className,
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <Spinner className="size-3.5 border-current/30 border-t-current" />}
      {children}
    </button>
  );
}

export function Card({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn("rounded-[2px] border border-hairline bg-surface", className)}
    >
      {children}
    </div>
  );
}

export function CardHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between border-b border-hairline px-4 py-3">
      <div>
        <h2 className="text-[11px] font-semibold uppercase tracking-[0.08em] text-ink/90">
          {title}
        </h2>
        {subtitle && (
          <p className="mt-0.5 font-body text-xs text-ink/50">{subtitle}</p>
        )}
      </div>
      {action}
    </div>
  );
}

export function Input(
  props: React.InputHTMLAttributes<HTMLInputElement> & {
    label?: string;
    error?: string;
  },
) {
  const { label, error, className, ...rest } = props;
  return (
    <label className="block">
      {label && (
        <span className="mb-1 block text-[10px] font-medium uppercase tracking-wide text-ink/50">
          {label}
        </span>
      )}
      <input
        className={cn(
          "w-full rounded-[2px] border border-hairline bg-bg px-2.5 py-2 text-sm text-ink placeholder-ink/30 outline-none transition-colors tabular-nums focus:border-amber",
          error && "border-bear focus:border-bear",
          className,
        )}
        {...rest}
      />
      {error && <span className="mt-1 block text-xs text-bear">{error}</span>}
    </label>
  );
}

export function Select(
  props: React.SelectHTMLAttributes<HTMLSelectElement> & {
    label?: string;
  },
) {
  const { label, className, children, ...rest } = props;
  return (
    <label className="block">
      {label && (
        <span className="mb-1 block text-[10px] font-medium uppercase tracking-wide text-ink/50">
          {label}
        </span>
      )}
      <select
        className={cn(
          "w-full appearance-none rounded-[2px] border border-hairline bg-bg px-2.5 py-2 text-sm text-ink outline-none transition-colors focus:border-amber",
          className,
        )}
        {...rest}
      >
        {children}
      </select>
    </label>
  );
}

export function Badge({
  children,
  tone = "default",
}: {
  children: React.ReactNode;
  tone?: "default" | "green" | "red" | "amber" | "blue";
}) {
  const tones: Record<string, string> = {
    default: "bg-surface-2 text-ink/60",
    green: "bg-bull/10 text-bull",
    red: "bg-bear/10 text-bear",
    amber: "bg-amber/10 text-amber",
    blue: "bg-ink/10 text-ink/70",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-[2px] px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
        tones[tone],
      )}
    >
      {children}
    </span>
  );
}

export function Alert({
  children,
  tone = "error",
}: {
  children: React.ReactNode;
  tone?: "error" | "success" | "info";
}) {
  const tones: Record<string, string> = {
    error: "border-bear text-bear",
    success: "border-bull text-bull",
    info: "border-amber text-amber",
  };
  return (
    <div
      className={cn(
        "rounded-[2px] border-l-2 bg-surface px-3 py-2 font-body text-sm text-ink/90",
        tones[tone],
      )}
      role="alert"
    >
      {children}
    </div>
  );
}
