import { useEffect, useMemo, useRef, useState } from "react";
import { client, type Opportunity, type Thesis } from "@/api/client";
import {
  AxisChip,
  FounderScoreCell,
  InThesisBadge,
  OriginBadge,
  StatusBadge,
  TrustFlagBadge,
  VerdictBadge,
} from "@/components/vc/primitives";
import { Search } from "lucide-react";
import pipelineBanner from "@/assets/pipeline-banner.png.asset.json";


type SearchResult = { opportunity: Opportunity; matched_attributes: string[] };

export function PipelineView({
  onOpen,
}: {
  onOpen: (id: number) => void;
}) {
  const [ops, setOps] = useState<Opportunity[]>([]);
  const [thesis, setThesis] = useState<Thesis | null>(null);
  const [originFilter, setOriginFilter] = useState<"all" | "inbound" | "outbound">(
    "all",
  );
  const [statusFilter, setStatusFilter] = useState<"all" | Opportunity["status"]>(
    "all",
  );
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [loading, setLoading] = useState(true);
  // Stagger the very first render only; further filter/search changes never re-animate.
  const firstLoadRef = useRef(true);


  useEffect(() => {
    let alive = true;
    Promise.all([client.listOpportunities(), client.getThesis()]).then(
      ([o, t]) => {
        if (!alive) return;
        setOps(o);
        setThesis(t);
        setLoading(false);
      },
    );
    return () => {
      alive = false;
    };
  }, []);

  // After the first render with data, disable the stagger so filter/search changes
  // don't re-animate rows.
  useEffect(() => {
    if (!loading && firstLoadRef.current) {
      const t = window.setTimeout(() => {
        firstLoadRef.current = false;
      }, 400);
      return () => window.clearTimeout(t);
    }
  }, [loading]);


  useEffect(() => {
    if (!query.trim()) {
      setResults(null);
      return;
    }
    let alive = true;
    client.searchOpportunities(query).then((r) => {
      if (alive) setResults(r);
    });
    return () => {
      alive = false;
    };
  }, [query]);

  // Priority = rank by verdict > axis-sum > trust flags asc > hours asc
  const priorityOf = (o: Opportunity) => {
    const verdictWeight =
      o.recommendation?.verdict === "invest"
        ? 3
        : o.recommendation?.verdict === "needs_review"
          ? 2
          : o.axes
            ? 1
            : o.status === "submitted"
              ? 0.5
              : 0;
    const axisSum = o.axes?.reduce((s, a) => s + a.score, 0) ?? 0;
    return verdictWeight * 1000 + axisSum - o.trust_flags_open * 5;
  };

  const filtered = useMemo(() => {
    const base = results ? results.map((r) => r.opportunity) : ops;
    return base
      .filter((o) => (originFilter === "all" ? true : o.origin === originFilter))
      .filter((o) => (statusFilter === "all" ? true : o.status === statusFilter))
      .sort((a, b) => priorityOf(b) - priorityOf(a));
  }, [ops, results, originFilter, statusFilter]);

  const matchedMap = useMemo(() => {
    const m = new Map<number, string[]>();
    results?.forEach((r) => m.set(r.opportunity.application_id, r.matched_attributes));
    return m;
  }, [results]);

  return (
    <div className="flex flex-col gap-6">
      {/* Banner strip — collage screened back so table headers below stay legible. */}
      <div
        aria-hidden
        className="relative -mx-8 -mt-8 mb-2 h-[110px] overflow-hidden border-b"
      >
        <div
          className="absolute inset-0 bg-cover bg-[position:center_55%] bg-no-repeat"
          style={{ backgroundImage: `url(${pipelineBanner.url})` }}
        />

        <div
          className="absolute inset-0"
          style={{
            background:
              "color-mix(in oklab, var(--bg-paper) 76%, transparent)",
          }}
        />
      </div>

      <header className="flex items-baseline justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Pipeline</h1>
          <p className="text-xs text-muted-foreground">
            Ranked by priority — not a merged score. Axes shown separately.
          </p>
        </div>
        {thesis && <ThesisChipRow thesis={thesis} />}
      </header>


      {/* Search + filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[320px]">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="technical founder, Berlin, AI infra, no prior VC backing"
            className="w-full rounded-md border bg-card py-1.5 pl-8 pr-3 text-xs outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30"
          />
        </div>
        <FilterSelect
          label="Origin"
          value={originFilter}
          onChange={(v) => setOriginFilter(v as typeof originFilter)}
          options={[
            ["all", "All"],
            ["inbound", "Inbound"],
            ["outbound", "Outbound"],
          ]}
        />
        <FilterSelect
          label="Status"
          value={statusFilter}
          onChange={(v) => setStatusFilter(v as typeof statusFilter)}
          options={[
            ["all", "All"],
            ["submitted", "Submitted"],
            ["screened_pass", "Screened pass"],
            ["screened_fail", "Screened fail"],
          ]}
        />
        <div className="ml-auto text-xs text-muted-foreground tabular">
          {filtered.length} opportunit{filtered.length === 1 ? "y" : "ies"}
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-md border bg-card">
        <table className="w-full text-xs">
          <thead className="bg-muted/40 text-[10px] uppercase tracking-wide text-muted-foreground">
            <tr>
              <Th>Priority</Th>
              <Th>Company</Th>
              <Th>Founder</Th>
              <Th>Origin</Th>
              <Th>Founder axis</Th>
              <Th>Market axis</Th>
              <Th>Idea × Market</Th>
              <Th>Founder Score</Th>
              <Th>Flags</Th>
              <Th>Thesis</Th>
              <Th>Verdict</Th>
              <Th>Age</Th>
              <Th>Status</Th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={13} className="py-6 text-center text-muted-foreground">
                  Loading…
                </td>
              </tr>
            )}
            {!loading && filtered.length === 0 && (
              <tr>
                <td colSpan={13} className="py-6 text-center text-muted-foreground">
                  No opportunities match these filters.
                </td>
              </tr>
            )}
            {filtered.map((o, idx) => {
              const hours = Math.round(
                (Date.now() - new Date(o.first_signal_at).getTime()) / 3600_000,
              );
              const founderAxis = o.axes?.find((a) => a.axis === "founder");
              const marketAxis = o.axes?.find((a) => a.axis === "market");
              const ideaAxis = o.axes?.find((a) => a.axis === "idea_vs_market");
              const matches = matchedMap.get(o.application_id);
              const stagger = firstLoadRef.current;
              return (
                <>
                  <tr
                    key={o.application_id}
                    onClick={() => onOpen(o.application_id)}
                    className={`cursor-pointer border-t hover:bg-accent/40 ${
                      stagger ? "motion-row" : ""
                    }`}
                    style={
                      stagger
                        ? { animationDelay: `${Math.min(idx, 9) * 30}ms` }
                        : undefined
                    }
                  >

                    <Td>
                      <span className="tabular text-muted-foreground">
                        {String(idx + 1).padStart(2, "0")}
                      </span>
                    </Td>
                    <Td>
                      <span className="font-medium text-foreground">
                        {o.company_name}
                      </span>
                      {o.status === "screened_fail" && o.screen_reason && (
                        <div className="mt-0.5 text-[10px] text-bear">
                          {o.screen_reason}
                        </div>
                      )}
                    </Td>
                    <Td>
                      {o.founder ? (
                        <span>{o.founder.canonical_name}</span>
                      ) : (
                        <span className="inline-flex rounded-sm border border-dashed border-flag/40 bg-flag-bg px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-flag">
                          Unresolved
                        </span>
                      )}
                    </Td>
                    <Td>
                      <OriginBadge origin={o.origin} />
                    </Td>
                    <Td>
                      {founderAxis ? (
                        <AxisChip
                          label="F"
                          score={founderAxis.score}
                          rating={founderAxis.rating}
                          trend={founderAxis.trend}
                        />
                      ) : (
                        <Dash />
                      )}
                    </Td>
                    <Td>
                      {marketAxis ? (
                        <AxisChip
                          label="M"
                          score={marketAxis.score}
                          rating={marketAxis.rating}
                          trend={marketAxis.trend}
                        />
                      ) : (
                        <Dash />
                      )}
                    </Td>
                    <Td>
                      {ideaAxis ? (
                        <AxisChip
                          label="I×M"
                          score={ideaAxis.score}
                          rating={ideaAxis.rating}
                          trend={ideaAxis.trend}
                        />
                      ) : (
                        <Dash />
                      )}
                    </Td>
                    <Td>
                      {o.founder ? (
                        <FounderScoreCell
                          score={o.founder.founder_score?.score ?? null}
                          coverage={o.founder.founder_score?.coverage ?? null}
                          history={o.founder.score_history.map((p) => p.score)}
                        />
                      ) : (
                        <Dash />
                      )}
                    </Td>
                    <Td>
                      <TrustFlagBadge count={o.trust_flags_open} />
                    </Td>
                    <Td>
                      <InThesisBadge inThesis={o.thesis_fit?.in_thesis ?? null} />
                    </Td>
                    <Td>
                      <VerdictBadge verdict={o.recommendation?.verdict ?? null} compact />
                    </Td>
                    <Td>
                      <span className="tabular text-muted-foreground">{hours}h</span>
                    </Td>
                    <Td>
                      <StatusBadge status={o.status} />
                    </Td>
                  </tr>
                  {matches && matches.length > 0 && (
                    <tr className="border-t border-dashed bg-primary/[0.03]">
                      <td colSpan={13} className="px-3 py-1.5 text-[10px]">
                        <span className="text-muted-foreground">Matched:</span>{" "}
                        {matches.map((m) => (
                          <span
                            key={m}
                            className="ml-1 inline-flex rounded-sm border border-primary/25 bg-primary/5 px-1.5 py-0.5 font-mono text-primary"
                          >
                            {m}
                          </span>
                        ))}
                      </td>
                    </tr>
                  )}
                </>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return <th className="px-3 py-2 text-left font-medium">{children}</th>;
}
function Td({ children }: { children: React.ReactNode }) {
  return <td className="whitespace-nowrap px-3 py-2 align-middle">{children}</td>;
}
function Dash() {
  return <span className="text-muted-foreground">—</span>;
}

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: [string, string][];
}) {
  return (
    <label className="flex items-center gap-1.5 text-[10px] uppercase tracking-wide text-muted-foreground">
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-md border bg-card px-2 py-1 text-xs normal-case tracking-normal text-foreground outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30"
      >
        {options.map(([v, l]) => (
          <option key={v} value={v}>
            {l}
          </option>
        ))}
      </select>
    </label>
  );
}

function ThesisChipRow({ thesis }: { thesis: Thesis }) {
  const chips = [
    ...thesis.sectors.map((s) => ({ k: "sector", v: s })),
    { k: "stage", v: thesis.stage },
    ...thesis.geography.map((g) => ({ k: "geo", v: g })),
    {
      k: "check",
      v: `$${(thesis.check_size_min / 1000).toFixed(0)}K${
        thesis.check_size_max !== thesis.check_size_min
          ? `–$${(thesis.check_size_max / 1000).toFixed(0)}K`
          : ""
      }`,
    },
    { k: "own", v: `${thesis.ownership_target_pct}% target` },
    { k: "risk", v: `${thesis.risk_appetite} risk` },
  ];
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
        Active thesis
      </span>
      {chips.map((c, i) => (
        <span
          key={i}
          className="inline-flex items-center rounded-sm border bg-card px-1.5 py-0.5 text-[10px]"
        >
          <span className="mr-1 text-muted-foreground">{c.k}</span>
          <span className="font-medium">{c.v}</span>
        </span>
      ))}
    </div>
  );
}
