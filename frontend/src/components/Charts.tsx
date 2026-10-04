/** Liquid Glass SVG Charts with glowing paths and subtle atmospheric grid lines. */

export function LineChart({
  values,
  labels,
  unit = "number",
  height = 240,
}: {
  values: number[];
  labels: string[];
  unit?: string;
  height?: number;
}) {
  if (values.length < 2) {
    return (
      <div style={{ padding: "40px 0", textAlign: "center", color: "var(--text-muted)", fontSize: "13px" }}>
        Not enough historical data points to generate telemetry curves.
      </div>
    );
  }

  const width = 760;
  const padX = 48;
  const padY = 28;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || Math.abs(max) || 1;
  const lo = min - span * 0.15;
  const hi = max + span * 0.15;

  const x = (i: number) => padX + (i * (width - padX * 2)) / (values.length - 1);
  const y = (v: number) => height - padY - ((v - lo) / (hi - lo)) * (height - padY * 2);

  const line = values.map((v, i) => `${i === 0 ? "M" : "L"}${x(i)},${y(v)}`).join(" ");
  const area = `${line} L${x(values.length - 1)},${height - padY} L${x(0)},${height - padY} Z`;

  const gridValues = [0, 0.25, 0.5, 0.75, 1].map((t) => lo + (hi - lo) * t);

  return (
    <div style={{ width: "100%", overflowX: "auto" }}>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        style={{ width: "100%", height: "auto", display: "block" }}
        role="img"
        aria-label={`Trend from ${labels[0]} to ${labels[labels.length - 1]}`}
      >
        <defs>
          <linearGradient id="liquidAreaGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#8B5CFF" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#8B5CFF" stopOpacity="0.0" />
          </linearGradient>
          <linearGradient id="liquidLineGradient" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#8B5CFF" />
            <stop offset="50%" stopColor="#A78BFA" />
            <stop offset="100%" stopColor="#5B8CFF" />
          </linearGradient>
          <filter id="glowFilter" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor="#8B5CFF" floodOpacity="0.6" />
          </filter>
        </defs>

        {/* Subtle grid lines */}
        {gridValues.map((gv, i) => (
          <g key={i}>
            <line
              x1={padX}
              x2={width - padX}
              y1={y(gv)}
              y2={y(gv)}
              stroke="rgba(255, 255, 255, 0.08)"
              strokeDasharray="3 3"
            />
            <text
              x={6}
              y={y(gv) + 4}
              fill="var(--text-muted)"
              fontSize="10.5"
              fontFamily="var(--font-mono)"
            >
              {formatCompact(gv, unit)}
            </text>
          </g>
        ))}

        {/* Translucent Area Gradient */}
        <path d={area} fill="url(#liquidAreaGradient)" />

        {/* Glowing Data Curve */}
        <path
          d={line}
          fill="none"
          stroke="url(#liquidLineGradient)"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
          filter="url(#glowFilter)"
        />

        {/* Interactive Data Points */}
        {values.map((v, i) => (
          <g key={i}>
            <circle
              cx={x(i)}
              cy={y(v)}
              r="4.5"
              fill="#05050A"
              stroke="#A78BFA"
              strokeWidth="2.5"
              style={{ cursor: "pointer" }}
            >
              <title>{`${labels[i]}: ${formatCompact(v, unit)}`}</title>
            </circle>
          </g>
        ))}

        {/* X-Axis Period Labels */}
        {labels.map((label, i) =>
          i % Math.ceil(labels.length / 7) === 0 ? (
            <text
              key={label}
              x={x(i)}
              y={height - 8}
              fill="var(--text-muted)"
              fontSize="11"
              fontFamily="var(--font-mono)"
              textAnchor="middle"
            >
              {label}
            </text>
          ) : null,
        )}
      </svg>
    </div>
  );
}

export function Sparkline({ values }: { values: number[] }) {
  if (values.length < 2) return null;
  const width = 120;
  const height = 32;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const points = values
    .map((v, i) => `${(i * width) / (values.length - 1)},${height - ((v - min) / span) * height}`)
    .join(" ");

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-hidden>
      <polyline
        points={points}
        fill="none"
        stroke="var(--violet-bright)"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

function formatCompact(value: number, unit: string): string {
  if (unit === "percent") return `${value.toFixed(0)}%`;
  if (unit === "currency") {
    if (Math.abs(value) >= 1_000_000) return `₹${(value / 1_000_000).toFixed(1)}M`;
    if (Math.abs(value) >= 1_000) return `₹${(value / 1_000).toFixed(0)}K`;
    return `₹${value.toFixed(0)}`;
  }
  return Math.abs(value) >= 1000 ? `${(value / 1000).toFixed(1)}k` : value.toFixed(0);
}
