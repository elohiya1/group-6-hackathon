import { useEffect, useMemo, useState } from "react";
import {
  client,
  ApiError,
  type AxisScore,
  type Contradiction,
  type DataPoint,
  type Opportunity,
} from "@/api/client";
import {
  AxisChip,
  ConfidenceTierBadge,
  FounderScoreCell,
  InThesisBadge,
  OriginBadge,
  StatusBadge,
  VerdictBadge,
} from "@/components/vc/primitives";
import { ArrowLeft } from "lucide-react";
import { useCountUp } from "@/hooks/use-count-up";

export function OpportunityDetail({ id, onBack }: { id: number; onBack: () => void }) {
  const [op, setOp] = useState<Opportunity | null>(null);
  const [tab, setTab] = useState<"memo" | "evidence" | "flags" | "adversarial">("memo");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    client
      .getOpportunity(id)
      .then((o) => {
        setOp(o);
        setLoading(false);
      })
      .catch((e) => {
        setError(e instanceof ApiError ? e.message : "Failed to load this opportunity.");
        setLoading(false);
      });
  }, [id]);

  if (loading) return <div className="p-8 text-sm text-muted-foreground">Loading…</div>;
  if (error) return <div className="p-8 text-sm text-bear">{error}</div>;
  if (!op) return <div className="p-8 text-sm text-muted-foreground">Not found.</div>;

  return (
    <div className="flex flex-col gap-6">
      <button
        onClick={onBack}
        className="inline-flex w-fit items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-3 w-3" /> Back to pipeline
      </button>

      {/* Header */}
      <header className="flex flex-col gap-4 rounded-md border bg-card p-5">
        <div className="flex items-start justify-between gap-6">
          <div className="min-w-0">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span className="font-mono">APP-{op.application_id}</span>
              <OriginBadge origin={op.origin} />
              <StatusBadge status={op.status} />
            </div>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight">{op.company_name}</h1>
            <div className="mt-1 flex items-center gap-3 text-sm text-muted-foreground">
              <span>
                {op.founder ? (
                  op.founder.canonical_name
                ) : (
                  <span className="text-flag">Unresolved founder</span>
                )}
              </span>
              {op.thesis_fit && <InThesisBadge inThesis={op.thesis_fit.in_thesis} />}
            </div>
          </div>

          {/* Recommendation — most prominent element */}
          {op.recommendation ? (
            <div className="max-w-md rounded-md border bg-background p-4">
              <div className="mb-2 flex items-center gap-2">
                <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
                  Recommendation
                </span>
                <span className="motion-pop inline-flex">
                  <VerdictBadge verdict={op.recommendation.verdict} />
                </span>
              </div>

              <p className="text-sm leading-snug text-foreground">{op.recommendation.rationale}</p>
              <p className="mt-2 text-[11px] text-muted-foreground">
                <span className="uppercase tracking-wide">Derivation: </span>
                {op.recommendation.derivation}
              </p>
            </div>
          ) : (
            <div className="max-w-md rounded-md border border-dashed bg-background p-4">
              <div className="text-[10px] uppercase tracking-wide text-muted-foreground">
                Recommendation
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                Not yet computed — application still being processed.
              </p>
            </div>
          )}
        </div>

        {op.founder && op.founder.founder_score === null && (
          <div className="rounded-sm border border-dashed border-flag/40 bg-flag-bg px-3 py-2 text-xs text-flag">
            No track record on file. Scored from public footprint with reduced confidence.
          </div>
        )}
      </header>

      {/* Axis cards */}
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        {op.axes ? (
          op.axes.map((a) => <AxisCard key={a.axis} axis={a} />)
        ) : (
          <div className="col-span-3 rounded-md border bg-card p-4 text-sm text-muted-foreground">
            Axes not yet scored for this application.
          </div>
        )}
      </div>

      {/* Tabs */}
      <div>
        <div className="flex gap-1 border-b">
          {(
            [
              ["memo", "Memo"],
              ["evidence", "Evidence"],
              ["flags", `Trust flags${op.trust_flags_open ? ` (${op.trust_flags_open})` : ""}`],
              ["adversarial", "Adversarial"],
            ] as const
          ).map(([k, label]) => (
            <button
              key={k}
              onClick={() => setTab(k)}
              className={`-mb-px border-b-2 px-3 py-2 text-xs font-medium ${
                tab === k
                  ? "border-primary text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="pt-5">
          {tab === "memo" && <MemoTab op={op} />}
          {tab === "evidence" && (
            <EvidenceTab
              points={op.founder?.data_points ?? []}
              founderName={op.founder?.canonical_name ?? null}
            />
          )}
          {tab === "flags" && <FlagsTab contradictions={op.founder?.contradictions ?? []} />}
          {tab === "adversarial" && <AdversarialTab op={op} />}
        </div>
      </div>

      {/* Decision trace */}
      <DecisionTrace op={op} />
    </div>
  );
}

function AxisCard({ axis }: { axis: AxisScore }) {
  const label =
    axis.axis === "founder" ? "Founder" : axis.axis === "market" ? "Market" : "Idea × Market";
  const color =
    axis.rating === "bullish"
      ? "text-bullish"
      : axis.rating === "bear"
        ? "text-bear"
        : "text-neutral";
  const animated = useCountUp(axis.score, 500);
  return (
    <div className="rounded-md border bg-card p-4 transition-transform duration-[120ms] hover:-translate-y-px hover:border-foreground/25">
      <div className="flex items-baseline justify-between">
        <span className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</span>
        <AxisChip label={label[0]} score={axis.score} rating={axis.rating} trend={axis.trend} />
      </div>
      <div className={`mt-2 tabular text-3xl font-semibold ${color}`}>{Math.round(animated)}</div>
      <div className="mt-0.5 text-[10px] uppercase tracking-wide text-muted-foreground">
        {axis.rating} · {axis.trend}
      </div>
      <p className="mt-3 text-xs leading-relaxed text-foreground/80">{axis.rationale}</p>
    </div>
  );
}

function MemoTab({ op }: { op: Opportunity }) {
  if (!op.memo)
    return (
      <div className="rounded-md border bg-card p-6 text-sm text-muted-foreground">
        Memo not yet generated.
      </div>
    );
  const m = op.memo;
  return (
    <div className="flex flex-col gap-5">
      {m.gaps_flagged.length > 0 && (
        <div className="rounded-md border border-flag/40 bg-flag-bg p-4">
          <div className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-flag">
            Flagged gaps
          </div>
          <ul className="space-y-1 text-sm text-flag">
            {m.gaps_flagged.map((g, i) => (
              <li key={i}>• {g}</li>
            ))}
          </ul>
        </div>
      )}

      <Section title="Company snapshot">
        <p className="text-sm leading-relaxed">{m.company_snapshot}</p>
      </Section>

      <Section title="Investment hypotheses">
        <ul className="list-disc space-y-1.5 pl-5 text-sm leading-relaxed">
          {m.investment_hypotheses.map((h, i) => (
            <li key={i}>{h}</li>
          ))}
        </ul>
      </Section>

      <Section title="SWOT">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <SwotCell label="Strengths" items={m.swot.strengths} tone="bullish" />
          <SwotCell label="Weaknesses" items={m.swot.weaknesses} tone="bear" />
          <SwotCell label="Opportunities" items={m.swot.opportunities} tone="bullish" />
          <SwotCell label="Risks" items={m.swot.risks} tone="bear" />
        </div>
      </Section>

      <Section title="Problem & product">
        <p className="text-sm leading-relaxed">{m.problem_and_product}</p>
      </Section>

      <Section title="Traction & KPIs">
        <p className="text-sm leading-relaxed">{m.traction_and_kpis}</p>
      </Section>

      <div className="text-[10px] text-muted-foreground">
        <span className="font-mono">{m.model_used}</span> · generated{" "}
        {new Date(m.generated_at).toLocaleString()}
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h3 className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
        {title}
      </h3>
      {children}
    </section>
  );
}

function SwotCell({
  label,
  items,
  tone,
}: {
  label: string;
  items: string[];
  tone: "bullish" | "bear";
}) {
  return (
    <div className="rounded-md border bg-card p-3">
      <div
        className={`mb-1.5 text-[10px] font-semibold uppercase tracking-wide ${
          tone === "bullish" ? "text-bullish" : "text-bear"
        }`}
      >
        {label}
      </div>
      <ul className="space-y-1 text-xs leading-relaxed">
        {items.map((i, k) => (
          <li key={k}>• {i}</li>
        ))}
      </ul>
    </div>
  );
}

function EvidenceTab({ points, founderName }: { points: DataPoint[]; founderName: string | null }) {
  const grouped = useMemo(() => {
    const g = new Map<string, DataPoint[]>();
    points.forEach((p) => {
      if (!g.has(p.attribute_name)) g.set(p.attribute_name, []);
      g.get(p.attribute_name)!.push(p);
    });
    // Sort corroborated first
    const tierRank = (t: DataPoint["confidence_tier"]) =>
      t === "corroborated" ? 0 : t === "contradicted" ? 1 : 2;
    for (const arr of g.values()) {
      arr.sort((a, b) => tierRank(a.confidence_tier) - tierRank(b.confidence_tier));
    }
    return [...g.entries()].sort(
      ([, a], [, b]) => tierRank(a[0].confidence_tier) - tierRank(b[0].confidence_tier),
    );
  }, [points]);

  if (points.length === 0) {
    return (
      <div className="rounded-md border bg-card p-6 text-sm text-muted-foreground">
        No evidence collected yet
        {founderName ? ` for ${founderName}` : ""}.
      </div>
    );
  }

  return (
    <div className="rounded-md border bg-card">
      {grouped.map(([attr, rows]) => (
        <div key={attr} className="border-b last:border-b-0">
          <div className="bg-muted/30 px-4 py-1.5 font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
            {attr}
          </div>
          <table className="w-full text-xs">
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-t first:border-t-0">
                  <td className="px-4 py-2 font-medium">{r.value}</td>
                  <td className="px-4 py-2">
                    <span className="font-mono text-muted-foreground">{r.source_name}</span>
                    <span className="ml-2 inline-flex rounded-sm border bg-background px-1.5 py-0.5 text-[10px] text-muted-foreground">
                      weight {r.source_reliability.toFixed(2)}
                    </span>
                  </td>
                  <td className="px-4 py-2 tabular text-muted-foreground">
                    {r.confidence_score !== null ? r.confidence_score.toFixed(2) : "—"}
                  </td>
                  <td className="px-4 py-2">
                    <ConfidenceTierBadge tier={r.confidence_tier} />
                  </td>
                  <td className="px-4 py-2 text-right tabular text-[10px] text-muted-foreground">
                    {r.observed_at ? new Date(r.observed_at).toLocaleDateString() : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}

function FlagsTab({ contradictions }: { contradictions: Contradiction[] }) {
  if (contradictions.length === 0)
    return (
      <div className="rounded-md border bg-card p-6 text-center text-sm text-muted-foreground">
        No open contradictions.
      </div>
    );
  return (
    <div className="flex flex-col gap-3">
      {contradictions.map((c) => (
        <div key={c.id} className="rounded-md border border-flag/40 bg-flag-bg/40 p-4">
          <div className="mb-3 flex items-baseline justify-between">
            <div>
              <span className="font-mono text-[10px] uppercase tracking-wide text-flag">
                {c.attribute_name}
              </span>
              <p className="mt-1 text-sm text-foreground">{c.description}</p>
            </div>
            <span className="text-[10px] text-muted-foreground">
              detected {new Date(c.detected_at).toLocaleString()}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-md border bg-card p-3">
              <div className="text-[10px] uppercase tracking-wide text-muted-foreground">
                {c.source_a}
              </div>
              <div className="mt-1 font-mono text-lg text-foreground">{c.value_a}</div>
            </div>
            <div className="rounded-md border bg-card p-3">
              <div className="text-[10px] uppercase tracking-wide text-muted-foreground">
                {c.source_b}
              </div>
              <div className="mt-1 font-mono text-lg text-foreground">{c.value_b}</div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function DecisionTrace({ op }: { op: Opportunity }) {
  const steps = [
    {
      label: "First signal",
      at: op.first_signal_at,
      done: true,
    },
    {
      label: "Screened",
      at: op.screened_at,
      done: !!op.screened_at,
      delta: op.hours_to_screen !== null ? `${op.hours_to_screen}h` : null,
    },
    {
      label: "Memo generated",
      at: op.memo_generated_at,
      done: !!op.memo_generated_at,
    },
  ];
  return (
    <section className="rounded-md border bg-card p-5">
      <h3 className="mb-4 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
        Decision trace
      </h3>
      <div className="flex items-start gap-4">
        {steps.map((s, i) => (
          <div key={i} className="flex flex-1 items-start gap-3">
            <div className="flex flex-col items-center">
              <div
                className={`h-2.5 w-2.5 rounded-full ${
                  s.done ? "bg-primary" : "border border-dashed border-muted-foreground"
                }`}
              />
              {i < steps.length - 1 && <div className="mt-1 h-8 w-px bg-border" />}
            </div>
            <div className="flex-1">
              <div className="text-xs font-medium">{s.label}</div>
              <div className="text-[10px] tabular text-muted-foreground">
                {s.at ? new Date(s.at).toLocaleString() : "pending"}
              </div>
              {s.delta && <div className="mt-0.5 text-[10px] text-primary tabular">+{s.delta}</div>}
            </div>
          </div>
        ))}
      </div>
      <div className="mt-6 border-t pt-4">
        <div className="text-[10px] uppercase tracking-wide text-muted-foreground">
          First signal to decision
        </div>
        <HoursCounter hours={op.hours_to_decision} />
      </div>
    </section>
  );
}

function HoursCounter({ hours }: { hours: number | null }) {
  const v = useCountUp(hours ?? 0, 500);
  return (
    <div className="tabular text-3xl font-semibold">
      {hours !== null ? `${Math.round(v)}h` : "—"}
    </div>
  );
}

function AdversarialTab({ op }: { op: Opportunity }) {
  if (!op.axes || !op.memo) {
    return (
      <div className="rounded-md border bg-card p-6 text-sm text-muted-foreground">
        Adversarial view is not available until the deal has been fully analyzed.
      </div>
    );
  }

  const bearAxes = op.axes.filter((a) => a.rating === "bear");
  const focusAxes =
    bearAxes.length > 0 ? bearAxes : [op.axes.slice().sort((a, b) => a.score - b.score)[0]];

  const contradictions = op.founder?.contradictions ?? [];
  const gaps = op.memo.gaps_flagged;
  const weaknesses = op.memo.swot.weaknesses;
  const risks = op.memo.swot.risks;

  const axisLabel = (k: string) =>
    k === "founder" ? "Founder" : k === "market" ? "Market" : "Idea × Market";

  return (
    <div className="rounded-md border border-bear/30 bg-bear/[0.03] border-l-4 border-l-bear p-6">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-bear">
        The case against this deal
      </h3>

      <section className="mt-5">
        <div className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
          {bearAxes.length > 0 ? "Bear axes" : "Weakest axis"}
        </div>
        <ul className="mt-2 flex flex-col gap-2 text-sm leading-relaxed">
          {focusAxes.map((a) => (
            <li key={a.axis}>
              <span className="font-semibold">{axisLabel(a.axis)}</span>{" "}
              <span className="tabular text-muted-foreground">({a.score})</span>
              {" — "}
              {a.rationale}
            </li>
          ))}
        </ul>
      </section>

      {(weaknesses.length > 0 || risks.length > 0) && (
        <section className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
          {weaknesses.length > 0 && (
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                Weaknesses
              </div>
              <ul className="mt-2 space-y-1 text-sm leading-relaxed">
                {weaknesses.map((w, i) => (
                  <li key={i}>• {w}</li>
                ))}
              </ul>
            </div>
          )}
          {risks.length > 0 && (
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                Risks
              </div>
              <ul className="mt-2 space-y-1 text-sm leading-relaxed">
                {risks.map((r, i) => (
                  <li key={i}>• {r}</li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}

      {contradictions.length > 0 && (
        <section className="mt-5">
          <div className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
            Open contradictions ({contradictions.length})
          </div>
          <ul className="mt-2 flex flex-col gap-1.5 text-sm leading-relaxed">
            {contradictions.map((c) => (
              <li key={c.id}>
                <span className="font-mono text-xs text-bear">{c.attribute_name}</span> —{" "}
                {c.description}
              </li>
            ))}
          </ul>
        </section>
      )}

      {gaps.length > 0 && (
        <section className="mt-5">
          <div className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
            Gaps flagged
          </div>
          <ul className="mt-2 space-y-1 text-sm leading-relaxed">
            {gaps.map((g, i) => (
              <li key={i}>• {g}</li>
            ))}
          </ul>
        </section>
      )}

      <p className="mt-6 border-t border-bear/20 pt-3 text-[10px] uppercase tracking-wide text-muted-foreground">
        Generated adversarially from the same evidence as the memo.
      </p>
    </div>
  );
}
