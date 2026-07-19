import { useEffect, useMemo, useState } from "react";
import { client, type Opportunity } from "@/api/client";
import { Check } from "lucide-react";
import founderBanner from "@/assets/founder-banner.png.asset.json";


type StepKey = "submitted" | "screened" | "under_analysis" | "decision";
type StepState = { key: StepKey; label: string; at: string | null; current: boolean };

export function FounderStatusView() {
  const [op, setOp] = useState<Opportunity | null | undefined>(undefined);

  useEffect(() => {
    client.getFounderPortal().then((r) => setOp(r.opportunity));
  }, []);

  if (op === undefined)
    return <div className="text-sm text-muted-foreground">Loading…</div>;

  if (op === null)
    return (
      <div className="flex flex-col gap-6">
        <h1 className="text-2xl font-semibold tracking-tight">My status</h1>
        <div className="rounded-lg border bg-card p-8 text-center text-sm text-muted-foreground">
          No application on file yet. Submit one from Apply.
        </div>
      </div>
    );

  const steps = buildSteps(op);

  return (
    <div className="flex flex-col gap-8">
      {/* Banner strip — puzzle-assembly collage screened back strongly so its
          red and green cannot be read as status colors next to the tracker. */}
      <div
        aria-hidden
        className="relative -mx-8 -mt-10 mb-2 h-[110px] overflow-hidden border-b"
      >
        <div
          className="absolute inset-0 bg-cover bg-[position:center_45%] bg-no-repeat"
          style={{ backgroundImage: `url(${founderBanner.url})` }}
        />
        <div
          className="absolute inset-0"
          style={{
            background:
              "color-mix(in oklab, var(--bg-paper) 88%, transparent)",
          }}
        />
      </div>

      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">My status</h1>
        <p className="text-sm text-muted-foreground">
          {op.company_name} · submitted {new Date(op.submitted_at).toLocaleString()}
        </p>
      </header>


      <Countdown submittedAt={op.submitted_at} hasDecision={!!op.recommendation} />

      <DecisionPanel op={op} />

      <ol className="flex flex-col">
        {steps.map((s, i) => (
          <StepRow key={s.key} step={s} last={i === steps.length - 1} />
        ))}
      </ol>
    </div>
  );
}

function buildSteps(op: Opportunity): StepState[] {
  const submitted = { key: "submitted" as const, label: "Submitted", at: op.submitted_at };
  const screened = {
    key: "screened" as const,
    label: "Screened",
    at: op.screened_at,
  };
  const analysis = {
    key: "under_analysis" as const,
    label: "Under analysis",
    at: op.memo_generated_at,
  };
  const decision = {
    key: "decision" as const,
    label: "Decision",
    at: op.recommendation ? op.memo_generated_at : null,
  };
  const all = [submitted, screened, analysis, decision];
  // Current = first step without a timestamp; if all set, decision is current.
  let currentIdx = all.findIndex((s) => !s.at);
  if (currentIdx === -1) currentIdx = all.length - 1;
  return all.map((s, i) => ({ ...s, current: i === currentIdx }));
}

function StepRow({ step, last }: { step: StepState; last: boolean }) {
  const done = !!step.at;
  return (
    <li className="flex items-start gap-4">
      <div className="flex flex-col items-center">
        <div
          className={`flex h-6 w-6 items-center justify-center rounded-full border ${
            done
              ? "border-primary bg-primary text-primary-foreground"
              : step.current
                ? "border-primary bg-background text-primary"
                : "border-dashed border-muted-foreground/40 bg-background text-muted-foreground"
          }`}
        >
          {done ? (
            <Check className="h-3.5 w-3.5" strokeWidth={3} />
          ) : (
            <div
              className={`h-1.5 w-1.5 rounded-full ${
                step.current ? "bg-primary animate-pulse" : "bg-muted-foreground/40"
              }`}
            />
          )}
        </div>
        {!last && <div className="my-1 h-10 w-px bg-border" />}
      </div>
      <div className="pb-4">
        <div
          className={`text-sm ${
            step.current ? "font-semibold" : done ? "font-medium" : "text-muted-foreground"
          }`}
        >
          {step.label}
          {step.current && !done && (
            <span className="ml-2 text-[10px] uppercase tracking-wide text-primary">
              in progress
            </span>
          )}
        </div>
        <div className="mt-0.5 tabular text-xs text-muted-foreground">
          {step.at ? new Date(step.at).toLocaleString() : "pending"}
        </div>
      </div>
    </li>
  );
}

function Countdown({
  submittedAt,
  hasDecision,
}: {
  submittedAt: string;
  hasDecision: boolean;
}) {
  const deadline = useMemo(
    () => new Date(submittedAt).getTime() + 24 * 3600 * 1000,
    [submittedAt],
  );
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (hasDecision) return;
    const t = setInterval(() => setNow(Date.now()), 30_000);
    return () => clearInterval(t);
  }, [hasDecision]);

  if (hasDecision) return null;

  const remaining = deadline - now;
  const overdue = remaining <= 0;
  const abs = Math.abs(remaining);
  const h = Math.floor(abs / 3600_000);
  const m = Math.floor((abs % 3600_000) / 60_000);

  return (
    <div className="rounded-lg border bg-card p-6">
      <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
        {overdue ? "Decision overdue" : "Decision due in"}
      </div>
      <div className="mt-1 tabular text-4xl font-semibold tracking-tight text-primary">
        {h}h {m}m
      </div>
    </div>
  );
}

function DecisionPanel({ op }: { op: Opportunity }) {
  const rec = op.recommendation;
  if (!rec) return null;

  if (rec.verdict === "invest") {
    return (
      <div className="rounded-lg border border-bullish/40 bg-bullish/5 p-6">
        <div className="text-[10px] uppercase tracking-[0.18em] text-bullish">
          Decision
        </div>
        <h2 className="mt-1 text-3xl font-semibold tracking-tight text-bullish">
          You're funded: $100K
        </h2>
        {op.memo && (
          <p className="mt-4 text-sm leading-relaxed text-foreground">
            {op.memo.company_snapshot}
          </p>
        )}
      </div>
    );
  }
  if (rec.verdict === "needs_review") {
    return (
      <div className="rounded-lg border border-flag/40 bg-flag-bg p-6">
        <div className="text-[10px] uppercase tracking-[0.18em] text-flag">
          Decision
        </div>
        <h2 className="mt-1 text-3xl font-semibold tracking-tight text-flag">
          In final review
        </h2>
      </div>
    );
  }
  return (
    <div className="rounded-lg border bg-card p-6">
      <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
        Decision
      </div>
      <h2 className="mt-1 text-2xl font-semibold tracking-tight">
        Not this time.
      </h2>
      <p className="mt-3 text-sm leading-relaxed text-foreground">
        Your Founder Score persists. Ship again and your next application starts from
        a stronger position.
      </p>
    </div>
  );
}
