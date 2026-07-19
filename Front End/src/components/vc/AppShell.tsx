import { useState } from "react";
import { Toaster } from "@/components/ui/sonner";
import { PipelineView } from "@/components/vc/PipelineView";
import { OpportunityDetail } from "@/components/vc/OpportunityDetail";
import { SourcingView } from "@/components/vc/SourcingView";
import { MemoryView } from "@/components/vc/MemoryView";
import { ThesisView } from "@/components/vc/ThesisView";
import { RoleSelect } from "@/components/vc/RoleSelect";
import { FounderShell } from "@/components/vc/founder/FounderShell";
import { LayoutList, Radio, Database, Target, LogOut } from "lucide-react";

type View = "pipeline" | "sourcing" | "memory" | "thesis";
type Role = null | "investor" | "founder";

export function AppShell() {
  const [role, setRole] = useState<Role>(null);

  return (
    <>
      {role === null && <RoleSelect onSelect={setRole} />}
      {role === "investor" && <InvestorShell onSwitchRole={() => setRole(null)} />}
      {role === "founder" && <FounderShell onSwitchRole={() => setRole(null)} />}
      <Toaster />
    </>
  );
}

function InvestorShell({ onSwitchRole }: { onSwitchRole: () => void }) {
  const [view, setView] = useState<View>("pipeline");
  const [openId, setOpenId] = useState<number | null>(null);
  const [pipelineKey, setPipelineKey] = useState(0);

  return (
    <div className="flex min-h-screen w-full bg-background text-foreground">
      <aside className="flex w-56 shrink-0 flex-col border-r bg-sidebar text-sidebar-foreground">
        <div className="border-b px-5 py-5">
          <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
            Maschmeyer Group
          </div>
          <div className="mt-0.5 text-base font-semibold tracking-tight">
            VC Brain
          </div>
        </div>
        <nav className="flex flex-1 flex-col gap-0.5 p-3">
          <NavItem
            icon={<LayoutList className="h-3.5 w-3.5" />}
            label="Pipeline"
            active={view === "pipeline"}
            onClick={() => {
              setView("pipeline");
              setOpenId(null);
            }}
          />
          <NavItem
            icon={<Radio className="h-3.5 w-3.5" />}
            label="Sourcing"
            active={view === "sourcing"}
            onClick={() => {
              setView("sourcing");
              setOpenId(null);
            }}
          />
          <NavItem
            icon={<Database className="h-3.5 w-3.5" />}
            label="Memory"
            active={view === "memory"}
            onClick={() => {
              setView("memory");
              setOpenId(null);
            }}
          />
          <NavItem
            icon={<Target className="h-3.5 w-3.5" />}
            label="Thesis"
            active={view === "thesis"}
            onClick={() => {
              setView("thesis");
              setOpenId(null);
            }}
          />
        </nav>
        <div className="border-t p-3">
          <NavItem
            icon={<LogOut className="h-3.5 w-3.5" />}
            label="Switch role"
            active={false}
            onClick={onSwitchRole}
          />
          <div className="mt-3 px-3 text-[10px] leading-relaxed text-muted-foreground">
            $100K decisions in 24h.
            <br />
            AI-native sourcing.
          </div>
        </div>
      </aside>

      <main className="min-w-0 flex-1 overflow-x-hidden">
        <div
          key={`${view}:${openId ?? "list"}`}
          className="motion-view mx-auto max-w-[1400px] px-8 py-8"
        >
          {openId !== null ? (
            <OpportunityDetail id={openId} onBack={() => setOpenId(null)} />
          ) : view === "pipeline" ? (
            <PipelineView key={pipelineKey} onOpen={setOpenId} />
          ) : view === "sourcing" ? (
            <SourcingView onSubmitted={() => setPipelineKey((k) => k + 1)} />
          ) : view === "memory" ? (
            <MemoryView />
          ) : (
            <ThesisView onSaved={() => setPipelineKey((k) => k + 1)} />
          )}
        </div>
      </main>

    </div>
  );
}

export function NavItem({
  icon,
  label,
  active,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex w-full items-center gap-2.5 rounded-md px-3 py-2 text-left text-sm transition-colors ${
        active
          ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
          : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-foreground"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}
