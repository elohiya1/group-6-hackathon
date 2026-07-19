import { useEffect, useMemo, useState } from "react";
import {
  client,
  ApiError,
  type CategoryCoverage,
  type Company,
  type Entity,
  type Founder,
  type NeedsReviewRecord,
  type DataPoint,
} from "@/api/client";
import { ColdStartBadge, ConfidenceTierBadge, Sparkline } from "@/components/vc/primitives";
import { toast } from "sonner";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

type FounderEntity = Extract<Entity, { type: "founder" }>;

export function MemoryView() {
  const [records, setRecords] = useState<NeedsReviewRecord[]>([]);
  const [removing, setRemoving] = useState<Set<number>>(new Set());
  const [entities, setEntities] = useState<Entity[]>([]);
  const [openFounder, setOpenFounder] = useState<Founder | null>(null);
  const [openCompany, setOpenCompany] = useState<Company | null>(null);
  const [query, setQuery] = useState("");
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    const onError = (e: unknown) =>
      setLoadError(e instanceof ApiError ? e.message : "Failed to load memory data.");
    client.listNeedsReview().then(setRecords).catch(onError);
    client.listEntities().then(setEntities).catch(onError);
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return entities;
    return entities.filter((e) => {
      if (e.canonical_name.toLowerCase().includes(q)) return true;
      return e.identifiers.some((i) => `${i.type} ${i.value}`.toLowerCase().includes(q));
    });
  }, [entities, query]);

  async function resolve(
    r: NeedsReviewRecord,
    decision: { type: "merge"; entity_id: number } | { type: "create_new" },
  ) {
    try {
      await client.resolveRecord(r.raw_record_id, decision);
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Failed to resolve this record.");
      return;
    }
    // Trigger fade-and-collapse before removing from the list.
    setRemoving((s) => new Set(s).add(r.raw_record_id));
    toast.success("Resolved, data points extracted and scores recomputed");
    window.setTimeout(() => {
      setRecords((rs) => rs.filter((x) => x.raw_record_id !== r.raw_record_id));
      setRemoving((s) => {
        const n = new Set(s);
        n.delete(r.raw_record_id);
        return n;
      });
    }, 200);
    client
      .listEntities()
      .then(setEntities)
      .catch(() => {});
  }

  return (
    <div className="flex flex-col gap-8">
      {loadError && (
        <div className="rounded-md border border-bear/30 bg-bear/5 p-4 text-sm text-bear">
          {loadError}
        </div>
      )}
      <section>
        <header className="mb-3">
          <h1 className="text-lg font-semibold tracking-tight">Needs review</h1>
          <p className="text-xs text-muted-foreground">
            Records that matched more than one entity. Resolve to unblock extraction.
          </p>
        </header>
        {records.length === 0 && (
          <div className="rounded-md border bg-card p-6 text-sm text-muted-foreground">
            Queue is empty.
          </div>
        )}
        <div className="flex flex-col gap-3">
          {records.map((r) => (
            <div
              key={r.raw_record_id}
              className={`rounded-md border bg-card p-4 ${
                removing.has(r.raw_record_id) ? "motion-collapse" : ""
              }`}
            >
              <div className="mb-3 flex items-baseline justify-between">
                <div>
                  <span className="font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
                    {r.source_name} · raw-{r.raw_record_id}
                  </span>
                </div>
                <span className="text-[10px] tabular text-muted-foreground">
                  ingested {new Date(r.ingested_at).toLocaleString()}
                </span>
              </div>
              <pre className="mb-3 overflow-x-auto rounded-sm bg-muted/50 p-2 font-mono text-[11px] text-foreground/80">
                {r.payload_preview}
              </pre>
              <div className="mb-3 grid grid-cols-1 gap-2 md:grid-cols-2">
                {r.candidate_entities.map((c) => (
                  <div key={c.entity_id} className="rounded-md border bg-background p-3">
                    <div className="text-[10px] uppercase tracking-wide text-muted-foreground">
                      Entity {c.entity_id}
                    </div>
                    <div className="mt-1 text-sm font-medium">{c.canonical_name}</div>
                    <div className="mt-1 font-mono text-[11px] text-muted-foreground">
                      matched via {c.matched_identifier}
                    </div>
                  </div>
                ))}
              </div>
              <div className="flex flex-wrap gap-2">
                {r.candidate_entities.map((c) => (
                  <button
                    key={c.entity_id}
                    onClick={() => resolve(r, { type: "merge", entity_id: c.entity_id })}
                    className="rounded-md border bg-background px-2.5 py-1 text-xs font-medium hover:bg-accent"
                  >
                    Merge into {c.canonical_name}
                  </button>
                ))}
                <button
                  onClick={() => resolve(r, { type: "create_new" })}
                  className="rounded-md bg-primary px-2.5 py-1 text-xs font-medium text-primary-foreground"
                >
                  Create new entity
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section>
        <header className="mb-3 flex items-end justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold tracking-tight">Entity directory</h2>
            <p className="text-xs text-muted-foreground">
              All resolved founders and companies. Click a row for details.
            </p>
          </div>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Filter by name or identifier…"
            className="w-64 rounded-md border bg-background px-2.5 py-1.5 text-xs outline-none focus:ring-2 focus:ring-ring"
          />
        </header>
        <div className="overflow-hidden rounded-md border bg-card">
          <table className="w-full text-xs">
            <thead className="bg-muted/40 text-[10px] uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="px-3 py-2 text-left font-medium">Type</th>
                <th className="px-3 py-2 text-left font-medium">Name</th>
                <th className="px-3 py-2 text-left font-medium">Identifiers</th>
                <th className="px-3 py-2 text-left font-medium">Score / Sources</th>
                <th className="px-3 py-2 text-left font-medium">Data points</th>
                <th className="px-3 py-2 text-left font-medium">Contradictions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-3 py-6 text-center text-muted-foreground">
                    No entities match
                  </td>
                </tr>
              )}
              {filtered.map((e) =>
                e.type === "founder" ? (
                  <FounderRow key={`f-${e.entity_id}`} f={e} onOpen={() => setOpenFounder(e)} />
                ) : (
                  <CompanyRow key={`c-${e.entity_id}`} c={e} onOpen={() => setOpenCompany(e)} />
                ),
              )}
            </tbody>
          </table>
        </div>
      </section>

      {openFounder && <FounderPanel founder={openFounder} onClose={() => setOpenFounder(null)} />}
      {openCompany && <CompanyPanel company={openCompany} onClose={() => setOpenCompany(null)} />}
    </div>
  );
}

function TypeBadge({ kind }: { kind: "founder" | "company" }) {
  return (
    <span
      className={`inline-flex rounded-sm border px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide ${
        kind === "founder"
          ? "border-primary/30 bg-primary/5 text-primary"
          : "border-neutral/30 bg-neutral/5 text-muted-foreground"
      }`}
    >
      {kind}
    </span>
  );
}

function FounderRow({ f, onOpen }: { f: FounderEntity; onOpen: () => void }) {
  return (
    <tr onClick={onOpen} className="cursor-pointer border-t hover:bg-accent/40">
      <td className="px-3 py-2">
        <TypeBadge kind="founder" />
      </td>
      <td className="px-3 py-2 font-medium">{f.canonical_name}</td>
      <td className="px-3 py-2">
        <div className="flex flex-wrap gap-1">
          {f.identifiers.map((i, k) => (
            <span
              key={k}
              className="inline-flex rounded-sm border bg-background px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground"
            >
              {i.type.replace("_username", "").replace("_", " ")}: {i.value}
            </span>
          ))}
        </div>
      </td>
      <td className="px-3 py-2">
        {f.founder_score ? (
          <div className="flex items-center gap-2">
            <span className="tabular">
              {f.founder_score.score}{" "}
              <span className="text-[10px] text-muted-foreground">
                ({f.founder_score.coverage})
              </span>
            </span>
            <Sparkline points={f.score_history.map((p) => p.score)} />
          </div>
        ) : (
          <ColdStartBadge />
        )}
      </td>
      <td className="px-3 py-2 tabular">{f.data_points.length}</td>
      <td className="px-3 py-2 tabular">
        {f.contradictions.length > 0 ? (
          <span className="text-bear">{f.contradictions.length}</span>
        ) : (
          <span className="text-muted-foreground">0</span>
        )}
      </td>
    </tr>
  );
}

function CompanyRow({ c, onOpen }: { c: Company; onOpen: () => void }) {
  const sourceCount = new Set(c.data_points.map((d) => d.source_name)).size;
  return (
    <tr onClick={onOpen} className="cursor-pointer border-t hover:bg-accent/40">
      <td className="px-3 py-2">
        <TypeBadge kind="company" />
      </td>
      <td className="px-3 py-2 font-medium">{c.canonical_name}</td>
      <td className="px-3 py-2">
        <div className="flex flex-wrap gap-1">
          {c.identifiers.map((i, k) => (
            <span
              key={k}
              className="inline-flex rounded-sm border bg-background px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground"
            >
              {i.type.replace("_", " ")}: {i.value}
            </span>
          ))}
        </div>
      </td>
      <td className="px-3 py-2 tabular text-muted-foreground">
        {sourceCount} source{sourceCount === 1 ? "" : "s"}
      </td>
      <td className="px-3 py-2 tabular">{c.data_points.length}</td>
      <td className="px-3 py-2 text-muted-foreground">—</td>
    </tr>
  );
}

function PanelShell({ onClose, children }: { onClose: () => void; children: React.ReactNode }) {
  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-foreground/10 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="h-full w-full max-w-xl overflow-y-auto border-l bg-card p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          className="mb-4 text-xs text-muted-foreground hover:text-foreground"
        >
          Close
        </button>
        {children}
      </div>
    </div>
  );
}

function FounderPanel({ founder, onClose }: { founder: Founder; onClose: () => void }) {
  const chartData = founder.score_history.map((p) => ({
    date: new Date(p.computed_at).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
    }),
    score: p.score,
  }));

  const bySource = founder.data_points.reduce<Record<string, DataPoint[]>>((acc, d) => {
    (acc[d.source_name] ||= []).push(d);
    return acc;
  }, {});

  return (
    <PanelShell onClose={onClose}>
      <h3 className="text-xl font-semibold">{founder.canonical_name}</h3>
      <div className="mt-1 flex items-center gap-3">
        {founder.founder_score ? (
          <span className="tabular text-3xl font-semibold">
            {founder.founder_score.score}
            <span className="ml-2 text-sm font-normal text-muted-foreground">
              ({founder.founder_score.coverage})
            </span>
          </span>
        ) : (
          <ColdStartBadge />
        )}
      </div>

      {chartData.length > 0 && (
        <div className="mt-4">
          <h4 className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
            Score history
          </h4>
          <div style={{ width: 480, maxWidth: "100%", height: 160 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 8, right: 12, bottom: 4, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
                  stroke="hsl(var(--border))"
                />
                <YAxis
                  tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
                  stroke="hsl(var(--border))"
                  width={28}
                  domain={["dataMin - 5", "dataMax + 5"]}
                />
                <Tooltip
                  contentStyle={{
                    fontSize: 11,
                    background: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="score"
                  stroke="hsl(var(--primary))"
                  strokeWidth={1.75}
                  dot={{ r: 2.5, fill: "hsl(var(--primary))" }}
                  activeDot={{ r: 4 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      <div className="mt-6">
        <h4 className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
          Category coverage
        </h4>
        <div className="flex flex-col gap-2">
          {founder.category_coverage.map((c) => (
            <CategoryRow key={c.category} c={c} dataPoints={founder.data_points} />
          ))}
        </div>
      </div>

      <div className="mt-6">
        <h4 className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
          Evidence
        </h4>
        {Object.keys(bySource).length === 0 && (
          <p className="text-xs italic text-muted-foreground">No data points recorded.</p>
        )}
        <div className="flex flex-col gap-3">
          {Object.entries(bySource).map(([source, points]) => (
            <div key={source} className="rounded-md border bg-background">
              <div className="border-b bg-muted/30 px-3 py-1.5 font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
                {source}
              </div>
              <table className="w-full text-xs">
                <thead className="text-[10px] uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-3 py-1.5 text-left font-medium">Attribute</th>
                    <th className="px-3 py-1.5 text-left font-medium">Value</th>
                    <th className="px-3 py-1.5 text-left font-medium">Conf.</th>
                    <th className="px-3 py-1.5 text-left font-medium">Tier</th>
                    <th className="px-3 py-1.5 text-left font-medium">Observed</th>
                  </tr>
                </thead>
                <tbody>
                  {points.map((d) => (
                    <tr key={d.id} className="border-t">
                      <td className="px-3 py-1.5 font-mono text-[11px] text-muted-foreground">
                        {d.attribute_name}
                      </td>
                      <td className="px-3 py-1.5">{d.value}</td>
                      <td className="px-3 py-1.5 tabular">
                        {d.confidence_score !== null ? d.confidence_score.toFixed(2) : "—"}
                      </td>
                      <td className="px-3 py-1.5">
                        <ConfidenceTierBadge tier={d.confidence_tier} />
                      </td>
                      <td className="px-3 py-1.5 tabular text-[10px] text-muted-foreground">
                        {d.observed_at ? new Date(d.observed_at).toLocaleDateString() : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      </div>

      {founder.contradictions.length > 0 && (
        <div className="mt-6">
          <h4 className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
            Contradictions
          </h4>
          <div className="flex flex-col gap-2 border-l-2 border-bear/60 pl-3">
            {founder.contradictions.map((c) => (
              <div key={c.id} className="rounded-md border bg-bear/5 p-3">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="font-mono text-[11px] font-medium text-bear">
                    {c.attribute_name}
                  </span>
                  <span className="tabular text-[10px] text-muted-foreground">
                    detected {new Date(c.detected_at).toLocaleString()}
                  </span>
                </div>
                <p className="mt-1 text-xs">{c.description}</p>
                <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
                  <div className="rounded-sm border bg-background p-2">
                    <div className="font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
                      {c.source_a}
                    </div>
                    <div className="mt-0.5 font-medium">{c.value_a}</div>
                  </div>
                  <div className="rounded-sm border bg-background p-2">
                    <div className="font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
                      {c.source_b}
                    </div>
                    <div className="mt-0.5 font-medium">{c.value_b}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </PanelShell>
  );
}

function CompanyPanel({ company, onClose }: { company: Company; onClose: () => void }) {
  return (
    <PanelShell onClose={onClose}>
      <h3 className="text-xl font-semibold">{company.canonical_name}</h3>
      <div className="mt-1">
        <TypeBadge kind="company" />
      </div>

      <div className="mt-6">
        <h4 className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
          Identifiers
        </h4>
        <div className="flex flex-wrap gap-1">
          {company.identifiers.map((i, k) => (
            <span
              key={k}
              className="inline-flex rounded-sm border bg-background px-1.5 py-0.5 font-mono text-[11px] text-muted-foreground"
            >
              {i.type.replace("_", " ")}: {i.value}
            </span>
          ))}
        </div>
      </div>

      <div className="mt-6">
        <h4 className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
          Data points
        </h4>
        <div className="overflow-hidden rounded-md border bg-background">
          <table className="w-full text-xs">
            <thead className="bg-muted/30 text-[10px] uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="px-3 py-1.5 text-left font-medium">Attribute</th>
                <th className="px-3 py-1.5 text-left font-medium">Value</th>
                <th className="px-3 py-1.5 text-left font-medium">Source</th>
                <th className="px-3 py-1.5 text-left font-medium">Tier</th>
              </tr>
            </thead>
            <tbody>
              {company.data_points.map((d) => (
                <tr key={d.id} className="border-t">
                  <td className="px-3 py-1.5 font-mono text-[11px] text-muted-foreground">
                    {d.attribute_name}
                  </td>
                  <td className="px-3 py-1.5">{d.value}</td>
                  <td className="px-3 py-1.5 font-mono text-[11px] text-muted-foreground">
                    {d.source_name}
                  </td>
                  <td className="px-3 py-1.5">
                    <ConfidenceTierBadge tier={d.confidence_tier} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </PanelShell>
  );
}

function CategoryRow({ c, dataPoints }: { c: CategoryCoverage; dataPoints: DataPoint[] }) {
  const label = c.category.replace(/_/g, " ");
  return (
    <div
      className={`rounded-md border p-3 ${
        c.has_data ? "bg-background" : "border-dashed bg-muted/30"
      }`}
    >
      <div className="flex items-baseline justify-between">
        <span className="text-sm font-medium capitalize">{label}</span>
        <span className="tabular text-[10px] text-muted-foreground">
          weight {c.weight.toFixed(2)}
        </span>
      </div>
      {c.has_data ? (
        <div className="mt-2 flex flex-col gap-1">
          {c.attribute_names.map((a) => {
            const dp = dataPoints.find((d) => d.attribute_name === a);
            return (
              <div key={a} className="flex items-baseline justify-between text-xs">
                <span className="font-mono text-muted-foreground">{a}</span>
                <span>{dp ? dp.value : "—"}</span>
              </div>
            );
          })}
        </div>
      ) : (
        <p className="mt-2 text-xs italic text-muted-foreground">
          no signal yet, excluded from score (not zeroed)
        </p>
      )}
    </div>
  );
}
