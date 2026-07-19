import { useEffect, useState } from "react";
import { client, type OutboundSignal } from "@/api/client";
import { StatusBadge } from "@/components/vc/primitives";
import { toast } from "sonner";

export function SourcingView({ onSubmitted }: { onSubmitted: () => void }) {
  const [signals, setSignals] = useState<OutboundSignal[]>([]);
  useEffect(() => {
    client.listOutboundSignals().then(setSignals);
  }, []);

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1.4fr_1fr]">
      <section className="flex flex-col gap-3">
        <header>
          <h1 className="text-lg font-semibold tracking-tight">Outbound signals</h1>
          <p className="text-xs text-muted-foreground">
            Founders surfaced from public sources, ordered by conviction.
          </p>
        </header>
        <div className="overflow-hidden rounded-md border bg-card">
          <table className="w-full text-xs">
            <thead className="bg-muted/40 text-[10px] uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="px-3 py-2 text-left font-medium">Founder</th>
                <th className="px-3 py-2 text-left font-medium">Conviction</th>
                <th className="px-3 py-2 text-left font-medium">Channel</th>
                <th className="px-3 py-2 text-left font-medium">Status</th>
                <th className="px-3 py-2 text-left font-medium">Detected</th>
              </tr>
            </thead>
            <tbody>
              {signals
                .slice()
                .sort((a, b) => b.conviction_score - a.conviction_score)
                .map((s) => (
                  <tr key={s.id} className="border-t">
                    <td className="px-3 py-2 font-medium">{s.founder_name}</td>
                    <td className="px-3 py-2 tabular">
                      {s.conviction_score.toFixed(2)}
                    </td>
                    <td className="px-3 py-2 font-mono text-muted-foreground">
                      {s.source_channel}
                    </td>
                    <td className="px-3 py-2">
                      <StatusBadge status={s.status} />
                    </td>
                    <td className="px-3 py-2 tabular text-[10px] text-muted-foreground">
                      {new Date(s.detected_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <InboundForm onSubmitted={onSubmitted} />
      </section>
    </div>
  );
}

function InboundForm({ onSubmitted }: { onSubmitted: () => void }) {
  const [company, setCompany] = useState("");
  const [deck, setDeck] = useState<File | null>(null);
  const [email, setEmail] = useState("");
  const [gh, setGh] = useState("");
  const [busy, setBusy] = useState(false);

  const canSubmit = company.trim().length > 0 && !!deck && !busy;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setBusy(true);
    try {
      const newOp = await client.submitApplication({
        company_name: company.trim(),
        deck_filename: deck!.name,
        founder_email: email.trim() || undefined,
        github_username: gh.trim() || undefined,
      });
      toast.success(`Submitted — ${newOp.company_name} is now in pipeline as submitted`);
      setCompany("");
      setDeck(null);
      setEmail("");
      setGh("");
      onSubmitted();
    } finally {
      setBusy(false);
    }
  }

  return (
    <form
      onSubmit={submit}
      className="flex flex-col gap-4 rounded-md border bg-card p-5"
    >
      <header>
        <h2 className="text-lg font-semibold tracking-tight">Inbound application</h2>
        <p className="text-xs text-muted-foreground">
          Deck + company name is all we need.
        </p>
      </header>

      <Field label="Company name" required>
        <input
          value={company}
          onChange={(e) => setCompany(e.target.value)}
          required
          className="w-full rounded-md border bg-background px-2.5 py-1.5 text-sm outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30"
        />
      </Field>

      <Field label="Deck" required>
        <input
          type="file"
          onChange={(e) => setDeck(e.target.files?.[0] ?? null)}
          required
          className="w-full text-xs text-muted-foreground file:mr-3 file:rounded-md file:border file:border-border file:bg-background file:px-2.5 file:py-1 file:text-xs file:font-medium file:text-foreground hover:file:bg-accent"
        />
      </Field>

      <Field label="Founder email" hint="optional">
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full rounded-md border bg-background px-2.5 py-1.5 text-sm outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30"
        />
      </Field>

      <Field label="GitHub username" hint="optional">
        <input
          value={gh}
          onChange={(e) => setGh(e.target.value)}
          className="w-full rounded-md border bg-background px-2.5 py-1.5 text-sm outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30"
        />
      </Field>

      <button
        type="submit"
        disabled={!canSubmit}
        className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition-opacity disabled:opacity-50"
      >
        {busy ? "Submitting…" : "Submit application"}
      </button>
    </form>
  );
}

function Field({
  label,
  hint,
  required,
  children,
}: {
  label: string;
  hint?: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="flex items-baseline justify-between text-[10px] uppercase tracking-wide text-muted-foreground">
        <span>
          {label}
          {required && <span className="ml-1 text-bear">*</span>}
        </span>
        {hint && <span className="normal-case">{hint}</span>}
      </span>
      {children}
    </label>
  );
}
