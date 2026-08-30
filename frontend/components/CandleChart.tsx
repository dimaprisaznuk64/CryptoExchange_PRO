"use client";

import { memo, useMemo, useState } from "react";
import type { Candle } from "@/lib/types";
import { formatPrice } from "@/lib/format";

interface PriceChartProps {
  candles: Candle[];
  height?: number;
}

export const CandleChart = memo(function CandleChart({ candles, height = 320 }: PriceChartProps) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  const { points, width, bodyW, step } = useMemo(() => {
    if (candles.length === 0) return { points: [], width: 0, bodyW: 0, step: 0 };
    const w = 720;
    const viewCandles = candles.slice(-120);
    const n = viewCandles.length;
    const bodyW = Math.max(2, Math.min(14, (w / n) * 0.6));
    const step = w / n;

    let lo = Infinity;
    let hi = -Infinity;
    for (const c of viewCandles) {
      lo = Math.min(lo, c.low);
      hi = Math.max(hi, c.high);
    }
    const pad = (hi - lo) * 0.08 || hi * 0.01;
    const priceMin = lo - pad;
    const priceMax = hi + pad;

    const y = (price: number) =>
      ((priceMax - price) / (priceMax - priceMin)) * height;

    const points = viewCandles.map((c, i) => ({
      x: i * step + step / 2,
      openY: y(c.open),
      closeY: y(c.close),
      highY: y(c.high),
      lowY: y(c.low),
      up: c.close >= c.open,
      candle: c,
    }));

    return { points, width: w, bodyW, step };
  }, [candles, height]);

  if (candles.length === 0) {
    return (
      <div
        className="flex items-center justify-center text-sm text-ink/50"
        style={{ height }}
      >
        No data
      </div>
    );
  }

  const hovered = hoverIndex !== null ? points[hoverIndex] : null;
  const last = points[points.length - 1];
  const lastUp = last.up;

  return (
    <div>
      <div className="mb-2 flex items-baseline justify-between">
        <span
          className={`text-lg font-semibold ${
            lastUp ? "text-bull" : "text-bear"
          }`}
        >
          {formatPrice(last.candle.close)}
        </span>
        <div className="flex gap-1 text-[10px] font-medium text-ink/50">
          <span>
            O {formatPrice(last.candle.open)}
          </span>
          <span>
            H {formatPrice(last.candle.high)}
          </span>
          <span>
            L {formatPrice(last.candle.low)}
          </span>
          <span>
            C {formatPrice(last.candle.close)}
          </span>
        </div>
      </div>

      <svg
        viewBox={`0 0 ${width} ${height}`}
        width="100%"
        height={height}
        className="select-none"
        onMouseLeave={() => setHoverIndex(null)}
      >
        <defs>
          <linearGradient id="grid" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#1a1a1d" stopOpacity="1" />
            <stop offset="100%" stopColor="#141416" stopOpacity="1" />
          </linearGradient>
        </defs>
        <rect x="0" y="0" width={width} height={height} fill="url(#grid)" rx="2" />

        {[0.25, 0.5, 0.75].map((f) => (
          <line
            key={f}
            x1="0"
            x2={width}
            y1={height * f}
            y2={height * f}
            stroke="#2a2a2e"
            strokeWidth="1"
          />
        ))}

        {points.map((p, i) => (
          <g key={i}>
            <line
              x1={p.x}
              x2={p.x}
              y1={p.highY}
              y2={p.lowY}
              stroke={p.up ? "#17c979" : "#ff4d4d"}
              strokeWidth="1"
            />
            <rect
              x={p.x - bodyW / 2}
              y={Math.min(p.openY, p.closeY)}
              width={bodyW}
              height={Math.max(Math.abs(p.openY - p.closeY), 1)}
              fill={p.up ? "#17c979" : "#ff4d4d"}
              rx="1"
            />
          </g>
        ))}

        {hovered && (
          <g>
            {hovered.highY > 8 && (
              <line
                x1="0"
                x2={width}
                y1={hovered.closeY}
                y2={hovered.closeY}
                stroke={hovered.up ? "#17c979" : "#ff4d4d"}
                strokeWidth="1"
                strokeDasharray="4 4"
                opacity="0.6"
              />
            )}
          </g>
        )}

        {points.map((p, i) => (
          <rect
            key={`hit-${i}`}
            x={p.x - step / 2}
            y="0"
            width={step}
            height={height}
            fill="transparent"
            onMouseEnter={() => setHoverIndex(i)}
          />
        ))}

        {hovered && (
          <g>
            <rect
              x={Math.min(Math.max(hovered.x - 45, 4), width - 94)}
              y="6"
              width="90"
              height="58"
              rx="2"
              fill="#1a1a1d"
              stroke="#3a3a3f"
            />
            <text x={hovered.x + 4} y="20" fill="#a1a1aa" fontSize="10">
              {new Date(hovered.candle.time).toLocaleString("en-US", {
                month: "short",
                day: "2-digit",
                hour: "2-digit",
                minute: "2-digit",
              })}
            </text>
            <text
              x={hovered.x + 4}
              y="34"
              fill={hovered.up ? "#17c979" : "#ff4d4d"}
              fontSize="10"
            >
              O {hovered.candle.open.toFixed(2)}
            </text>
            <text
              x={hovered.x + 4}
              y="47"
              fill={hovered.up ? "#17c979" : "#ff4d4d"}
              fontSize="10"
            >
              H {hovered.candle.high.toFixed(2)}
            </text>
            <text
              x={hovered.x + 4}
              y="60"
              fill={hovered.up ? "#17c979" : "#ff4d4d"}
              fontSize="10"
            >
              L {hovered.candle.low.toFixed(2)}
            </text>
          </g>
        )}
      </svg>
    </div>
  );
});