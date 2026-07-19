import { useEffect, useState } from "react";
import { client, type Thesis } from "@/api/client";
import { toast } from "sonner";

const SECTOR_OPTIONS = [
  "AI infra",
  "Applied AI",
  "Developer tools",
  "Fintech",
  "Cybersecurity",
  "Biotech",
  "Robotics",
  "Data infra",
];
const STAGE_OPTIONS = ["Pre-seed", "Pre-seed / Seed", "Seed", "Seed / Series A"];
const GEO_OPTIONS = ["EU", "US", "UK", "APAC", "LATAM"];
const RISK_OPTIONS = ["Low", "Medium", "High"];

export function ThesisView({ onSaved }: { onSaved: () => void }) {
  const [t, setT] = useState<Thesis | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    client.getThesis().then(setT);
  }, []);

  if (!t)
    return <div className="p-8 text-sm text-muted-foreground">Loading…</div>;

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!t) return;
    setSaving(true);
    const saved = await client.saveThesis(t);
    setT(saved);
    setSaving(false);
    toast.success("All scoring now filtered through this thesis");
    onSaved();
  }

  const toggle = (arr: string[], v: string) =>
    arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v];

  return (
    <form onSubmit={save} className="flex max-w-3xl flex-col gap-6">
      <header>
        <h1 className="text-lg font-semibold tracking-tight">Investment thesis</h1>
        <p className="text-xs text-muted-foreground">
          Every axis, thesis-fit call and recommendation flows through these settings.
        </p>
      </header>

      <Group label="Sectors">
        <div className="flex flex-wrap gap-1.5">
          {SECTOR_OPTIONS.map((s) => (
            <Toggle
              key={s}
              active={t.sectors.includes(s)}
              onClick={() => setT({ ...t, sectors: toggle(t.sectors, s) })}
            >
              {s}
            </Toggle>
          ))}
        </div>
      </Group>

      <Group label="Stage">
        <select
          value={t.stage}
          onChange={(e) => setT({ ...t, stage: e.target.value })}
          className="w-64 rounded-md border bg-background px-2.5 py-1.5 text-sm outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30"
        >
          {STAGE_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </Group>

      <Group label="Geography">
        <div className="flex flex-wrap gap-1.5">
          {GEO_OPTIONS.map((g) => (
            <Toggle
              key={g}
              active={t.geography.includes(g)}
              onClick={() => setT({ ...t, geography: toggle(t.geography, g) })}
            >
              {g}
            </Toggle>
          ))}
        </div>
      </Group>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Group label="Check size min ($)">
          <input
            type="number"
            value={t.check_size_min}
            onChange={(e) => setT({ ...t, check_size_min: Number(e.target.value) })}
            className="w-full rounded-md border bg-background px-2.5 py-1.5 text-sm tabular outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30"
          />
        </Group>
        <Group label="Check size max ($)">
          <input
            type="number"
            value={t.check_size_max}
            onChange={(e) => setT({ ...t, check_size_max: Number(e.target.value) })}
            className="w-full rounded-md border bg-background px-2.5 py-1.5 text-sm tabular outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30"
          />
        </Group>
        <Group label="Ownership target (%)">
          <input
            type="number"
            step="0.5"
            value={t.ownership_target_pct}
            onChange={(e) =>
              setT({ ...t, ownership_target_pct: Number(e.target.value) })
            }
            className="w-full rounded-md border bg-background px-2.5 py-1.5 text-sm tabular outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30"
          />
        </Group>
      </div>

      <Group label="Risk appetite">
        <select
          value={t.risk_appetite}
          onChange={(e) => setT({ ...t, risk_appetite: e.target.value })}
          className="w-48 rounded-md border bg-background px-2.5 py-1.5 text-sm outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30"
        >
          {RISK_OPTIONS.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
      </Group>

      <div className="flex items-center gap-3 border-t pt-4">
        <button
          type="submit"
          disabled={saving}
          className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
        >
          {saving ? "Saving…" : "Save thesis"}
        </button>
        <span className="text-[10px] tabular text-muted-foreground">
          last updated {new Date(t.updated_at).toLocaleString()}
        </span>
      </div>
    </form>
  );
}

function Group({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <label className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
        {label}
      </label>
      {children}
    </div>
  );
}

function Toggle({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-md border px-2.5 py-1 text-xs transition-colors ${
        active
          ? "border-primary/40 bg-primary/10 text-primary"
          : "border-border bg-card text-muted-foreground hover:text-foreground"
      }`}
    >
      {children}
    </button>
  );
}
