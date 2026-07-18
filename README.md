# The VC Brain 🧠

**Deploying $100K Checks in 24 Hours**

Built for the [Hack-Nation](https://hack-nation.ai) 6th Global AI Hackathon — Challenge 02, powered by **Maschmeyer Group**, in collaboration with the MIT Club of Northern California and the MIT Club of Germany.

---

## 🎯 The Problem

Venture capital today runs on networks, not merit. Founders stay invisible until they know the right person. Their story is scattered across pitch decks, GitHub repos, half-built websites, and social posts nobody reads closely. Diligence takes weeks. By the time a fund sees a founder clearly, dozens of equally strong ones have given up waiting.

**The VC Brain** is a data- and AI-first operating system that transforms how venture capital works — discovering exceptional founders before anyone else, and producing a decision-ready $100K recommendation within 24 hours.

## 🏗️ Architecture

The system maps the VC pipeline — **Sourcing → Screening → Diligence → Decision** — onto three layers:

```
┌─────────────────────────────────────────────────────┐
│  Experience Layer — Investor-facing UX              │
│  Investor dashboard · Ranked list · Decision memos  │
├─────────────────────────────────────────────────────┤
│  Intelligence Layer — Reasoning & scoring           │
│  Thesis Engine · Multi-axis scoring · Trust Score   │
├─────────────────────────────────────────────────────┤
│  Memory Layer — Data foundation                     │
│  Structured knowledge base · Founder Score ·        │
│  Timestamped, deduplicated, source-tagged data      │
└─────────────────────────────────────────────────────┘
```

### Memory — the data foundation
- Ingests pitch decks, interviews, launches, GitHub activity, and social traction
- Deduplicates, enriches, timestamps, and tags everything by source
- Houses the **Founder Score** — a persistent, per-person score that follows founders across applications and never resets
- Surfaces trends over time, not just the latest snapshot

### Intelligence — the reasoning layer
- Operates on top of Memory to produce insights, challenge assumptions, and recommend next steps
- Triggered by inbound applications or by outbound signals crossing a conviction threshold
- Transparent about confidence, uncertainty, and the evidence behind every conclusion

### Experience — investor-grade UX
- Notion-level approachability, Bloomberg-level analytical depth
- Ranked founder pipeline with momentum trends and decision-ready memo output

## 🔍 Sourcing: Dual-Track Funnel

Sourcing is the heart of the system — surfacing the strongest founders **before they formally begin fundraising**.

**Inbound** — founders apply directly. Minimum bar: pitch deck + company name. A fast first-pass filter removes clearly non-viable ideas before full analysis.

**Outbound** — the system continuously scans public signal sources and scores discovered founders the same way as inbound applications, then triggers real outreach to the strongest matches. Data sources include:

| Source | Signal |
|---|---|
| GitHub | Commit activity, repo momentum, technical depth |
| LinkedIn | Career history, network, founder-market fit |
| Twitter / X | Public footprint, distribution ability |
| Devpost & hackathons | Wins, shipped projects, team formation |
| Product Hunt | Launches and early traction |
| arXiv / research papers | Recently published research worth a phone call |
| Public patent search | Novel, defensible technology |
| University startup challenges | Pre-track-record founders surfacing early |
| Tavily (web search) | Enrichment and cross-verification |

Both tracks converge into the same screening funnel.

## ⚖️ Multi-Axis Screening

Every opportunity is scored along **three independent axes — never averaged**:

1. **Founder** — who they are, their traits and track record (the persistent Founder Score is one input here)
2. **Market** — sizing, competitors, SWOT — rated bullish / neutral / bear
3. **Idea vs. Market** — does the idea survive scrutiny as-is, or is the team strong enough to pivot?

Each axis carries a trend direction (improving / declining / stable) and feeds back into Memory to sharpen future scoring.

## 🧾 Evidence-Backed Memos & Trust Score

Every claim in an investment memo — traction, revenue, team background, market size — traces to specific evidence with a per-claim confidence level: the **Trust Score**. Claims are verified externally where possible, and contradictions are flagged before they reach the investor.

Missing data is never fabricated. Gaps are explicitly flagged (e.g. *"Cap table: not disclosed"*) — a memo that marks its own gaps is more trustworthy than one that fills them in invisibly.

**Required memo sections:** Company snapshot · Investment hypotheses · SWOT · Problem & product · Traction & KPIs

## 🎛️ Thesis Engine

Fully configurable, fund-specific lens. The investor sets:
- Sectors, stage, geography
- Check size and ownership targets
- Risk appetite

Every recommendation is filtered and scored through this lens — no hardcoded thesis.

## 💬 Multi-Attribute Reasoning

Beyond keyword search. The system resolves compound natural-language queries in a single pass:

> *"technical founder, Berlin, AI infra, enterprise traction, no prior VC backing, top-tier accelerator"*

## ❄️ The Cold-Start Case

First-time founders with no GitHub history, no funding, and no network are the core case this system exists to serve — otherwise we've just rebuilt the network-gated system the challenge aims to replace. The system leans on public footprints (social presence, university challenges, hackathon participation, published work) to build an initial profile, with honest confidence intervals where data is thin.

## 🚀 Getting Started

```bash
# Clone the repo
git clone <repo-url>
cd vc-brain

# Install dependencies
# (add your setup instructions here)

# Configure environment
# (API keys: Tavily, GitHub, etc.)

# Run
# (add your run command here)
```

## 📊 Evaluation Criteria (Hackathon)

| Criterion | Weight |
|---|---|
| Data Architecture and Intelligence | 30% |
| Investment Utility & Execution | 30% |
| Intelligent Analysis and Trust | 25% |
| User Experience and Design | 15% |

## 🌟 Stretch Goals

- **Agentic Traceability** — every recommendation cites the exact data point (deck slide, web signal, interview excerpt) that drove it, with step-level chain-of-thought logging
- **Self-Correction Loops** — a Validator Agent cross-references extracted claims against market databases and observable evidence
- **Sourcing & Network Intelligence** — model the sourcing graph and learn which channels produce quality, not just volume

## 🧭 Scope

This project covers **Sourcing → Screening → Diligence → Decision**. Downstream stages (portfolio monitoring, follow-on, fund ops, exit) are intentionally out of scope.

---

*Build the data layer. Build the reasoning layer. Build the experience. Build the infrastructure that gives exceptional founders the capital to begin.*
