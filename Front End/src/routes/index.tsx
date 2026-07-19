import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/vc/AppShell";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "VC Brain — Maschmeyer Group" },
      {
        name: "description",
        content:
          "Investor dashboard for an AI-native venture fund: sources founders and issues $100K decisions within 24 hours.",
      },
      { property: "og:title", content: "VC Brain — Maschmeyer Group" },
      {
        property: "og:description",
        content: "AI-native sourcing. $100K decisions in 24 hours.",
      },
    ],
  }),
  component: Index,
});

function Index() {
  return <AppShell />;
}
