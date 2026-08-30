"use client";

import { useMemo } from "react";
import { formatCompact, formatPercent, formatUsd } from "@/lib/format";
import { cn } from "@/lib/utils";

interface Point {
  time: string;
  value: number;
}

const W = 760;
const H = 260;
const PAD = 12;

export function PortfolioChart({ data }: { data: Point[] }) {
  const { line, area, min, max } = useMemo(() => {
    const values = data.map((p) => p.value);
    if (values.length === 0) return { line: "", area: "", min: 0, max: 0 };
    const minVal = Math.min(...values);
    const maxVal = Math.max(...values);
    const span = maxVal - minVal || 1;
    const stepX = (W - PAD * 2) / Math.max(data.length - 1, 1);
    const pts: string[] = [];
    const areas: string[] = [];
    data.forEach((p, i) => {
      const x = PAD + i * stepX;
      const y = H - PAD - ((p.value - minVal) / span) * (H - PAD * 2);
      pts.push(`${x.toFixed(2)},${y.toFixed(2)}`);
      areas.push(`${x.toFixed(2)},${y.toFixed(2)}`);
    });
    return {
      line: pts.join(" "),
      area: `${PAD},${H - PAD} ${areas.join(" ")} ${W - PAD},${H - PAD}`,
      min: minVal,
      max: maxVal,
    };
  }, [data]);

  const first = data[0]?.value ?? 0;
  const last = data[data.length - 1]?.value ?? 0;
  const diff = last - first;
  const pct = first > 0 ? (diff / first) * 100 : 0;
  const up = diff >= 0;
  const color = up ? "#17c979" : "#ff4d4d";

  if (data.length === 0) {
    return (
      <p className="px-6 py-10 text-center text-sm text-ink/50">
        No portfolio history yet.
      </p>
    );
  }

  return (
    <div>
      <div className="flex items-end justify-between px-6 pt-2">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-ink/50">
            Value now
          </p>
          <p className="mt-1 text-2xl font-extrabold text-ink">
            {formatUsd(last)}
          </p>
        </div>
        <p
          className={cn(
            "pb-1 text-sm font-bold",
            up ? "text-bull" : "text-bear",
          )}
        >
          {formatUsd(diff)} ({formatPercent(pct)})
        </p>
      </div>

      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="mt-2 block w-full"
        role="img"
        aria-label="Portfolio value over the last 7 days"
      >
        <defs>
          <linearGradient id="portfolio-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.18" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </linearGradient>
        </defs>

        {[0.25, 0.5, 0.75].map((f) => {
          const y = PAD + (H - PAD * 2) * f;
          return (
            <line
              key={f}
              x1={PAD}
              x2={W - PAD}
              y1={y}
              y2={y}
              stroke="#2a2a2e"
              strokeDasharray="3 6"
              strokeWidth="1"
            />
          );
        })}

        <polygon points={area} fill="url(#portfolio-fill)" />
        <polyline
          points={line}
          fill="none"
          stroke={color}
          strokeWidth="2"
          strokeLinejoin="round"
          strokeLinecap="round"
        />

        <text x={W - PAD} y={PAD + 10} textAnchor="end" fontSize="10" fill="#a1a1aa">
          {formatCompact(max)}
        </text>
        <text
          x={W - PAD}
          y={H - PAD + 2}
          textAnchor="end"
          fontSize="10"
          fill="#a1a1aa"
        >
          {formatCompact(min)}
        </text>
      </svg>
    </div>
  );
}