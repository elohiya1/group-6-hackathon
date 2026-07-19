import type { AxisRating, ConfidenceTier, Trend } from "@/api/client";
import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";

export function AxisChip({
  label,
  score,
  rating,
  trend,
}: {
  label: string;
  score: number;
  rating: AxisRating;
  trend: Trend;
}) {
  const color =
    rating === "bullish"
      ? "text-bullish border-bullish/30 bg-bullish/5"
      : rating === "bear"
        ? "text-bear border-bear/30 bg-bear/5"
        : "text-neutral border-neutral/25 bg-neutral/5";
  const Icon =
    trend === "improving" ? ArrowUpRight : trend === "declining" ? ArrowDownRight : Minus;
  return (
    <div
      className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs font-medium ${color}`}
      title={`${label}: ${rating}`}
    >
      <span className="text-[10px] uppercase tracking-wide opacity-70">{label}</span>
      <span className="tabular font-semibold">{score}</span>
      <Icon className="h-3 w-3" strokeWidth={2.25} />
    </div>
  );
}

export function OriginBadge({ origin }: { origin: "inbound" | "outbound" }) {
  return (
    <span
      className={`inline-flex items-center rounded-sm border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide ${
        origin === "inbound"
          ? "border-primary/30 bg-primary/5 text-primary"
          : "border-neutral/30 bg-neutral/5 text-muted-foreground"
      }`}
    >
      {origin}
    </span>
  );
}

export function VerdictBadge({
  verdict,
  compact = false,
}: {
  verdict: "invest" | "pass" | "needs_review" | null | undefined;
  compact?: boolean;
}) {
  if (!verdict)
    return (
      <span className="inline-flex items-center rounded-sm border border-dashed px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-muted-foreground">
        pending
      </span>
    );
  const styles: Record<string, string> = {
    invest: "bg-bullish text-primary-foreground border-bullish",
    pass: "bg-neutral/10 text-muted-foreground border-neutral/30",
    needs_review: "bg-flag-bg text-flag border-flag/40",
  };
  const label = verdict === "needs_review" ? "needs review" : verdict;
  return (
    <span
      className={`inline-flex items-center rounded-sm border font-medium uppercase tracking-wide ${
        compact ? "px-1.5 py-0.5 text-[10px]" : "px-2.5 py-1 text-xs"
      } ${styles[verdict]}`}
    >
      {label}
    </span>
  );
}

export function TrustFlagBadge({ count }: { count: number }) {
  if (count <= 0) return null;
  return (
    <span
      className="inline-flex items-center gap-1 rounded-sm border border-bear/30 bg-bear/10 px-1.5 py-0.5 text-[10px] font-semibold text-bear"
      title={`${count} open trust flag(s)`}
    >
      ⚑ {count}
    </span>
  );
}

export function InThesisBadge({ inThesis }: { inThesis: boolean | null | undefined }) {
  if (inThesis === null || inThesis === undefined)
    return (
      <span className="text-[10px] uppercase tracking-wide text-muted-foreground">—</span>
    );
  return (
    <span
      className={`inline-flex items-center rounded-sm border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide ${
        inThesis
          ? "border-bullish/30 bg-bullish/5 text-bullish"
          : "border-neutral/30 bg-neutral/5 text-muted-foreground"
      }`}
    >
      {inThesis ? "in thesis" : "out of thesis"}
    </span>
  );
}

export function ConfidenceTierBadge({ tier }: { tier: ConfidenceTier | null }) {
  if (!tier)
    return <span className="text-xs text-muted-foreground">—</span>;
  const map: Record<ConfidenceTier, string> = {
    insufficient_data: "bg-neutral/10 text-muted-foreground border-neutral/25",
    corroborated: "bg-bullish/10 text-bullish border-bullish/30",
    contradicted: "bg-bear/10 text-bear border-bear/30",
  };
  return (
    <span
      className={`inline-flex items-center rounded-sm border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide ${map[tier]}`}
    >
      {tier.replace("_", " ")}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    submitted: "border-primary/25 bg-primary/5 text-primary",
    screened_pass: "border-bullish/25 bg-bullish/5 text-bullish",
    screened_fail: "border-bear/25 bg-bear/5 text-bear",
    identified: "border-neutral/30 bg-neutral/5 text-muted-foreground",
    activated: "border-primary/25 bg-primary/5 text-primary",
    converged: "border-bullish/25 bg-bullish/5 text-bullish",
  };
  return (
    <span
      className={`inline-flex items-center rounded-sm border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide ${
        map[status] ?? "border bg-muted text-muted-foreground"
      }`}
    >
      {status.replace("_", " ")}
    </span>
  );
}

export function Sparkline({
  points,
  width = 72,
  height = 22,
}: {
  points: number[];
  width?: number;
  height?: number;
}) {
  if (points.length === 0)
    return <span className="text-[10px] text-muted-foreground">—</span>;
  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = max - min || 1;
  const step = width / Math.max(1, points.length - 1);
  const d = points
    .map((p, i) => {
      const x = i * step;
      const y = height - ((p - min) / range) * (height - 4) - 2;
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  return (
    <svg width={width} height={height} className="text-primary/70">
      <path d={d} fill="none" stroke="currentColor" strokeWidth={1.25} />
    </svg>
  );
}

export function ColdStartBadge() {
  return (
    <span className="inline-flex items-center rounded-sm border border-dashed border-flag/40 bg-flag-bg px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-flag">
      cold start
    </span>
  );
}

export function FounderScoreCell({
  score,
  coverage,
  history,
}: {
  score: number | null;
  coverage: string | null;
  history: number[];
}) {
  if (score === null) return <ColdStartBadge />;
  const [num, denom] = (coverage ?? "0/4").split("/").map(Number);
  const low = num / (denom || 4) <= 0.5;
  return (
    <div className="flex items-center gap-2">
      <span
        className={`tabular font-semibold ${low ? "text-muted-foreground/60" : ""}`}
      >
        {score}
      </span>
      <span className={`tabular text-[10px] text-muted-foreground`}>
        ({coverage})
      </span>
      <Sparkline points={history} />
    </div>
  );
}
