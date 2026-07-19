import { useEffect, useState } from "react";
import { client, type Founder, type CategoryCoverage } from "@/api/client";
import { ConfidenceTierBadge, Sparkline } from "@/components/vc/primitives";
import { useCountUp } from "@/hooks/use-count-up";


const CATEGORY_LABELS: Record<CategoryCoverage["category"], string> = {
  technical_execution: "Technical execution",
  track_record: "Track record",
  recognition: "Recognition",
  network: "Network",
};

const CATEGORY_HINTS: Record<CategoryCoverage["category"], string> = {
  technical_execution:
    "No technical execution signals yet: GitHub activity, published models, and shipped projects feed this category.",
  track_record:
    "No track record signals yet: prior exits, prior roles, and team sizes you've led feed this category.",
  recognition:
    "No recognition signals yet: hackathons, accelerator cohorts, and launches feed this category.",
  network:
    "No network signals yet: co-investors, advisors, and community activity feed this category.",
};

export function FounderProfileView() {
  const [founder, setFounder] = useState<Founder | null>(null);

  useEffect(() => {
    client.getFounderPortal().then((r) => setFounder(r.founder));
  }, []);

  if (!founder)
    return <div className="text-sm text-muted-foreground">Loading…</div>;

  const missing = founder.category_coverage.filter((c) => !c.has_data);
  const scoreHistory = founder.score_history.map((p) => p.score);

  return (
    <div className="flex flex-col gap-10">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">My profile</h1>
        <p className="text-sm text-muted-foreground">{founder.canonical_name}</p>
      </header>

      {/* Score */}
      <section className="flex flex-col gap-3 rounded-lg border bg-card p-6">
        <h2 className="text-sm font-semibold tracking-tight">
          Your Founder Score, a credit score for founders. It never resets.
        </h2>
        <div className="flex items-end gap-6">
          <div>
            <FounderScoreNumber score={founder.founder_score?.score ?? null} />
            <div className="mt-1 text-xs text-muted-foreground">
              Coverage {founder.founder_score?.coverage ?? "0/4"}
            </div>

          </div>
          <div className="pb-2">
            <Sparkline points={scoreHistory} width={160} height={44} />
          </div>
        </div>
      </section>

      {/* Coverage */}
      <section className="flex flex-col gap-3">
        <h2 className="text-sm font-semibold tracking-tight">Category coverage</h2>
        <div className="overflow-hidden rounded-lg border bg-card">
          {founder.category_coverage.map((c, i) => (
            <div
              key={c.category}
              className={`flex items-start justify-between gap-4 px-5 py-4 ${
                i > 0 ? "border-t" : ""
              }`}
            >
              <div>
                <div className="text-sm font-medium">
                  {CATEGORY_LABELS[c.category]}
                </div>
                <div className="mt-0.5 text-xs text-muted-foreground">
                  {c.attribute_names.length > 0
                    ? c.attribute_names.join(", ")
                    : "No signals recorded"}
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className="tabular text-[10px] text-muted-foreground">
                  weight {c.weight.toFixed(2)}
                </span>
                <span
                  className={`inline-flex rounded-sm border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide ${
                    c.has_data
                      ? "border-bullish/30 bg-bullish/5 text-bullish"
                      : "border-dashed border-muted-foreground/40 text-muted-foreground"
                  }`}
                >
                  {c.has_data ? "covered" : "empty"}
                </span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Evidence */}
      <section className="flex flex-col gap-3">
        <h2 className="text-sm font-semibold tracking-tight">
          What the fund sees
        </h2>
        <p className="text-xs text-muted-foreground">
          Every data point currently attached to your profile, with source and
          confidence.
        </p>
        <div className="overflow-hidden rounded-lg border bg-card">
          <table className="w-full text-sm">
            <thead className="bg-muted/40 text-[10px] uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="px-4 py-2 text-left font-medium">Attribute</th>
                <th className="px-4 py-2 text-left font-medium">Value</th>
                <th className="px-4 py-2 text-left font-medium">Source</th>
                <th className="px-4 py-2 text-left font-medium">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {founder.data_points.map((d) => (
                <tr key={d.id} className="border-t">
                  <td className="px-4 py-2 font-mono text-[11px] text-muted-foreground">
                    {d.attribute_name}
                  </td>
                  <td className="px-4 py-2 font-medium">{d.value}</td>
                  <td className="px-4 py-2 font-mono text-[11px] text-muted-foreground">
                    {d.source_name}
                  </td>
                  <td className="px-4 py-2">
                    <ConfidenceTierBadge tier={d.confidence_tier} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Grow your score */}
      {missing.length > 0 && (
        <section className="rounded-lg border border-primary/30 bg-primary/5 p-6">
          <h2 className="text-sm font-semibold tracking-tight text-primary">
            Grow your score
          </h2>
          <ul className="mt-3 flex flex-col gap-2 text-sm leading-relaxed">
            {missing.map((c) => (
              <li key={c.category} className="text-foreground">
                • {CATEGORY_HINTS[c.category]}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function FounderScoreNumber({ score }: { score: number | null }) {
  const v = useCountUp(score, 500);
  return (
    <div className="tabular text-5xl font-semibold text-primary">
      {score === null ? "—" : Math.round(v)}
    </div>
  );
}

