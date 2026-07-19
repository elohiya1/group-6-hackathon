import { useState } from "react";
import { NavItem } from "@/components/vc/AppShell";
import { FounderApplyView } from "@/components/vc/founder/FounderApplyView";
import { FounderStatusView } from "@/components/vc/founder/FounderStatusView";
import { FounderProfileView } from "@/components/vc/founder/FounderProfileView";
import { FileUp, Clock, User, LogOut } from "lucide-react";

type FView = "apply" | "status" | "profile";

export function FounderShell({ onSwitchRole }: { onSwitchRole: () => void }) {
  const [view, setView] = useState<FView>("status");
  // Bump to refresh status view when a new application is submitted
  const [statusKey, setStatusKey] = useState(0);

  return (
    <div className="flex min-h-screen w-full bg-background text-foreground">
      <aside className="flex w-56 shrink-0 flex-col border-r bg-sidebar text-sidebar-foreground">
        <div className="border-b px-5 py-5">
          <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
            Founder portal
          </div>
          <div className="mt-0.5 text-base font-semibold tracking-tight">
            VC Brain
          </div>
        </div>
        <nav className="flex flex-1 flex-col gap-0.5 p-3">
          <NavItem
            icon={<FileUp className="h-3.5 w-3.5" />}
            label="Apply"
            active={view === "apply"}
            onClick={() => setView("apply")}
          />
          <NavItem
            icon={<Clock className="h-3.5 w-3.5" />}
            label="My Status"
            active={view === "status"}
            onClick={() => setView("status")}
          />
          <NavItem
            icon={<User className="h-3.5 w-3.5" />}
            label="My Profile"
            active={view === "profile"}
            onClick={() => setView("profile")}
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
            An answer within 24 hours.
          </div>
        </div>
      </aside>

      <main className="min-w-0 flex-1 overflow-x-hidden">
        <div key={view} className="motion-view mx-auto max-w-3xl px-8 py-10">
          {view === "apply" && (
            <FounderApplyView
              onSubmitted={() => {
                setStatusKey((k) => k + 1);
                setView("status");
              }}
            />
          )}
          {view === "status" && <FounderStatusView key={statusKey} />}
          {view === "profile" && <FounderProfileView />}
        </div>
      </main>

    </div>
  );
}
