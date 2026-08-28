"use client";

import { cn } from "@/lib/utils";

export function Spinner({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "size-5 animate-spin rounded-full border-2 border-zinc-600 border-t-zinc-200",
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
    primary:
      "bg-indigo-600 text-white hover:bg-indigo-500 disabled:hover:bg-indigo-600",
    success:
      "bg-emerald-600 text-white hover:bg-emerald-500 disabled:hover:bg-emerald-600",
    danger:
      "bg-rose-600 text-white hover:bg-rose-500 disabled:hover:bg-rose-600",
    ghost: "bg-transparent text-zinc-300 hover:bg-zinc-800",
    outline:
      "bg-transparent border border-zinc-700 text-zinc-200 hover:bg-zinc-800",
  };
  const sizes: Record<string, string> = {
    sm: "px-3 py-1.5 text-xs rounded-lg",
    md: "px-4 py-2 text-sm rounded-lg",
    lg: "px-5 py-3 text-base rounded-xl",
  };

  return (
    <button
      className={cn(
        "inline-flex cursor-pointer items-center justify-center gap-2 font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60",
        variants[variant],
        sizes[size],
        className,
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <Spinner className="size-4 border-zinc-500" />}
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
      className={cn(
        "rounded-xl border border-zinc-800 bg-zinc-900/60 backdrop-blur",
        className,
      )}
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
    <div className="flex items-start justify-between border-b border-zinc-800 px-5 py-4">
      <div>
        <h2 className="text-sm font-semibold tracking-wide text-zinc-100">
          {title}
        </h2>
        {subtitle && (
          <p className="mt-0.5 text-xs text-zinc-500">{subtitle}</p>
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
        <span className="mb-1 block text-xs font-medium text-zinc-400">
          {label}
        </span>
      )}
      <input
        className={cn(
          "w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 outline-none transition-colors focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500",
          error && "border-rose-500 focus:border-rose-500 focus:ring-rose-500",
          className,
        )}
        {...rest}
      />
      {error && <span className="mt-1 block text-xs text-rose-400">{error}</span>}
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
        <span className="mb-1 block text-xs font-medium text-zinc-400">
          {label}
        </span>
      )}
      <select
        className={cn(
          "w-full appearance-none rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 outline-none transition-colors focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500",
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
    default: "bg-zinc-800 text-zinc-300",
    green: "bg-emerald-500/10 text-emerald-400",
    red: "bg-rose-500/10 text-rose-400",
    amber: "bg-amber-500/10 text-amber-400",
    blue: "bg-sky-500/10 text-sky-400",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center rounded px-2 py-0.5 text-xs font-medium",
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
    error: "border-rose-500/40 bg-rose-500/10 text-rose-300",
    success: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
    info: "border-sky-500/40 bg-sky-500/10 text-sky-300",
  };
  return (
    <div
      className={cn("rounded-lg border px-3 py-2 text-sm", tones[tone])}
      role="alert"
    >
      {children}
    </div>
  );
}