"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

interface FlashValueProps {
  value: number;
  format: (value: number) => string;
  className?: string;
}

/**
 * The signature terminal touch: when a live number changes, briefly flash
 * the cell green (up) or red (down), then let it fade — the same tactile
 * feedback a real trading screen gives on every tick. Use for prices,
 * balances, P&L, anything driven by the WS feed.
 */
export function FlashValue({ value, format, className }: FlashValueProps) {
  const prev = useRef(value);
  const [flash, setFlash] = useState<"up" | "down" | null>(null);

  useEffect(() => {
    if (value === prev.current) return;
    setFlash(value > prev.current ? "up" : "down");
    prev.current = value;
    const t = setTimeout(() => setFlash(null), 400);
    return () => clearTimeout(t);
  }, [value]);

  return (
    <span
      className={cn(
        "inline-block rounded-[2px] px-1 tabular-nums",
        flash === "up" && "flash-up",
        flash === "down" && "flash-down",
        className,
      )}
    >
      {format(value)}
    </span>
  );
}
