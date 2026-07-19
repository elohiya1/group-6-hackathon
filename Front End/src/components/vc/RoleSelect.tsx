import { Briefcase, Rocket } from "lucide-react";
import entryCollage from "@/assets/entry-collage.png.asset.json";


export function RoleSelect({
  onSelect,
}: {
  onSelect: (role: "investor" | "founder") => void;
}) {
  return (
    <div className="relative flex min-h-screen w-full items-center justify-center overflow-hidden px-6 texture-paper">
      {/* Background collage — screened back with cream so title/buttons read cleanly over the quiet left area. */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 overflow-hidden"
      >
        <div
          className="motion-drift absolute inset-y-0 right-0 w-[75%] bg-[position:right_center] bg-cover bg-no-repeat"
          style={{ backgroundImage: `url(${entryCollage.url})` }}
        />
        {/* Cream overlay: 55-65% opacity so image reads as faint print, not a photo. */}
        <div
          className="absolute inset-0"
          style={{
            background:
              "linear-gradient(to right, var(--bg-paper) 0%, var(--bg-paper) 35%, color-mix(in oklab, var(--bg-paper) 62%, transparent) 65%, color-mix(in oklab, var(--bg-paper) 60%, transparent) 100%)",
          }}
        />
      </div>
      {/* Decorative red ticker trendline rising behind the title */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-[10%] h-[70%] ticker-trendline opacity-40"
      />

      {/* Green halftone dot cluster */}
      <div
        aria-hidden
        className="pointer-events-none absolute -left-16 bottom-10 h-56 w-56 rounded-full halftone-dots"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -right-10 top-16 h-40 w-40 rounded-full halftone-dots"
      />
      {/* Faint scattered monospace code fragments */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 select-none font-mono text-[10px] leading-[1.4] text-foreground"
        style={{ opacity: 0.08 }}
      >
        <div className="absolute left-[6%] top-[8%]">SEED · $100K · 24H</div>
        <div className="absolute right-[8%] top-[22%]">SIG=0.87  Δ=+0.12</div>
        <div className="absolute left-[10%] top-[38%]">gh://commits/1284</div>
        <div className="absolute right-[12%] bottom-[30%]">tier=corroborated</div>
        <div className="absolute left-[14%] bottom-[14%]">axis:market=bullish</div>
        <div className="absolute right-[18%] bottom-[10%]">verdict=INVEST</div>
      </div>

      <div className="relative z-10 flex w-full max-w-2xl flex-col items-center gap-10">
        <header className="flex flex-col items-center gap-3 text-center">
          <div className="label-caps tracking-[0.22em]">Maschmeyer Group</div>
          <h1 className="font-serif text-6xl font-bold tracking-tight text-foreground">
            VC Brain
          </h1>
          <p className="text-base text-muted-foreground">
            An AI-native fund. $100K decisions in 24 hours.
          </p>
        </header>

        <div className="grid w-full grid-cols-1 gap-4 sm:grid-cols-2">
          <RoleButton
            icon={<Briefcase className="h-5 w-5" />}
            title="Enter as Investor"
            subtitle="Pipeline, memos, evidence, thesis."
            onClick={() => onSelect("investor")}
          />
          <RoleButton
            icon={<Rocket className="h-5 w-5" />}
            title="Enter as Founder"
            subtitle="Apply and track your decision."
            onClick={() => onSelect("founder")}
          />
        </div>

        <p className="label-caps">
          No accounts. No passwords. Choose a role to continue.
        </p>
      </div>
    </div>
  );
}

function RoleButton({
  icon,
  title,
  subtitle,
  onClick,
}: {
  icon: React.ReactNode;
  title: string;
  subtitle: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="group flex flex-col items-start gap-3 rounded-lg border bg-card p-6 text-left transition-colors hover:border-primary/50 hover:bg-accent"
    >
      <div className="flex h-10 w-10 items-center justify-center rounded-md border bg-background text-primary">
        {icon}
      </div>
      <div>
        <div className="text-base font-semibold tracking-tight">{title}</div>
        <div className="mt-1 text-xs text-muted-foreground">{subtitle}</div>
      </div>
    </button>
  );
}
