import { useState } from "react";
import { client, ApiError } from "@/api/client";
import { toast } from "sonner";

export function FounderApplyView({ onSubmitted }: { onSubmitted: () => void }) {
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
      const op = await client.submitApplication({
        company_name: company.trim(),
        deck: deck!,
        founder_email: email.trim() || undefined,
        github_username: gh.trim() || undefined,
      });
      client.rememberFounderApplication(op.application_id);
      toast.success(`Submitted — ${op.company_name}`);
      setCompany("");
      setDeck(null);
      setEmail("");
      setGh("");
      onSubmitted();
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Failed to submit application.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold tracking-tight">Apply</h1>
        <p className="text-sm text-muted-foreground">
          That's all we need. You'll have an answer within 24 hours.
        </p>
      </header>

      <form onSubmit={submit} className="flex flex-col gap-5 rounded-lg border bg-card p-6">
        <Field label="Company name" required>
          <input
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            required
            className="w-full rounded-md border bg-background px-3 py-2 text-base outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30"
          />
        </Field>

        <Field label="Deck" required>
          <input
            type="file"
            onChange={(e) => setDeck(e.target.files?.[0] ?? null)}
            required
            className="w-full text-sm text-muted-foreground file:mr-3 file:rounded-md file:border file:border-border file:bg-background file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-foreground hover:file:bg-accent"
          />
        </Field>

        <Field label="Email" hint="optional">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-md border bg-background px-3 py-2 text-base outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30"
          />
        </Field>

        <Field label="GitHub username" hint="optional">
          <input
            value={gh}
            onChange={(e) => setGh(e.target.value)}
            className="w-full rounded-md border bg-background px-3 py-2 text-base outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30"
          />
        </Field>

        <button
          type="submit"
          disabled={!canSubmit}
          className="rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition-opacity disabled:opacity-50"
        >
          {busy ? "Submitting…" : "Submit application"}
        </button>
      </form>
    </div>
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
    <label className="flex flex-col gap-2">
      <span className="flex items-baseline justify-between text-xs uppercase tracking-wide text-muted-foreground">
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
