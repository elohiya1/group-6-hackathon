# The VC Brain — Build Plan

Four workstreams, mapped directly to the challenge doc. Evaluation weights: Data Architecture & Intelligence 30% · Investment Utility & Execution 30% · Intelligent Analysis & Trust 25% · UX & Design 15%.

---

## Person A — Memory Layer & Data Collection (Data Architecture, 30%)

**Owns:** Smart Data Collection & Management — the data foundation. Nothing discarded.

- Build ingestion for the sourcing channels from the doc:
  - GitHub
  - LinkedIn
  - Twitter
  - Tavily (web search / enrichment)
  - Devpost
  - University startup challenges
  - Product Hunt
  - Hacker News
  - Public patent search
  - Recently published research papers (arXiv)
  - Crunchbase / Grata
- Actively collect, validate, and structure founder and company data from these heterogeneous sources — the data layer matters as much as the intelligence built on top of it
- Deduplicate, enrich, timestamp, and tag everything by source
- Ingest pitch decks, interviews, launches, GitHub activity, and social traction
- Build the **Founder Score** — lives in Memory, persists across applications, never resets; follows the person across different startups over time
- Surface the trend over time, not just the latest snapshot
- Synthesize data where needed: synthetic founder profiles **with seeded contradictions**, anonymised/fictional pitch decks — ingestion quality beats dataset size
- **Cold-start case (not an afterthought):** an explicit method for first-time founders with no GitHub, no funding, no network — score them from their public footprint (Twitter, LinkedIn, university challenges, hackathons). Generic ingestion/enrichment won't score highly without this

## Person B — Inbound & Outbound Funnel (Sourcing — the most important part of the MVP)

**Owns:** the dual-track funnel. Surface the strongest founders before they formally begin fundraising. Judged on data richness and smart sourcing ideas, not polish — least commercial competition, go further here than anywhere else.

- **Inbound — Application & Automated Screening:**
  - Apply: deck + company name is the minimum bar; add fields only if genuinely needed for a confident 24-hour decision (over-collecting works against you)
  - Screen: fast first-pass filter that removes clearly non-viable ideas before full analysis begins
- **Outbound — Founder Identification & Activation:**
  - Identify: continuously scan GitHub, launches, hackathons, papers/patents, and accelerator cohorts — scored the same way as an inbound application
  - Activate: reach out to the strongest matches directly — cold outreach, not cold investment; the goal is to trigger a real application
  - Converge: activated applications flow into the same Screening step as inbound, so both tracks feed one funnel
- Trigger conditions for the Intelligence layer: an inbound application, or signals crossing a conviction threshold on their own
- Instrument how fast and reliably an opportunity moves from first signal to decision (Investment Utility explicitly rewards this)

## Person C — Intelligence Layer (Analysis & Trust 25% + Investment Utility 30%)

**Owns:** the reasoning layer — makes or supports every investment decision. Operates on top of Memory to produce insights, challenge assumptions, and recommend next steps. Transparent about confidence, uncertainty, and the evidence behind every conclusion.

- **Thesis Engine:** investor sets sectors, stage, geography, check size, ownership targets, and risk appetite; every recommendation is filtered and scored through this fund-specific lens. Configurable — a hardcoded thesis misses the point of the pillar
- **Multi-Axis Screening** — three independent axes, **not averaged** (collapsing them hides exactly the disagreement an investor needs to see):
  - Founder: who they are, their traits and track record (Founder Score is one input into this axis, not a substitute)
  - Market: sizing, competitors, SWOT — rated bullish, neutral, or bear
  - Idea vs. Market: does the idea survive scrutiny as-is, or is the team strong enough to pivot?
  - Each axis shows trend (improving / declining / stable) and feeds back into Memory to sharpen future scoring
- **Trust Score** — per claim, not one number for the company: every claim (traction, revenue, team background, market size) traces to evidence with a confidence level, verified externally where possible, contradictions flagged before they reach the investor
- **Multi-Attribute Reasoning:** resolve compound natural-language queries in one pass — not five manual filters — e.g. "technical founder, Berlin, AI infra, enterprise traction, no prior VC backing, top-tier accelerator"
- **Investment Memo** (see Appendix 1 of the brief):
  - Required sections: Company snapshot, Investment hypotheses, SWOT, Problem & product, Traction & KPIs
  - Length rule: as detailed as the decision requires, as brief as clarity allows — padding counts against you
  - Don't fabricate missing data — flag gaps explicitly ("Cap table: not disclosed"); a memo that marks its own gaps scores as more trustworthy
- Final output: a $100K recommendation a human investor could genuinely act on within 24 hours
- **Stretch goals (in the doc's priority order):**
  1. Agentic Traceability — cite the exact data point (deck slide, web signal, interview excerpt) behind each conclusion; step-level chain-of-thought logging. Highest-leverage add: directly reinforces the Trust Score requirement
  2. Self-Correction Loops — Validator Agent cross-references extracted founder claims against market databases, comparable funding rounds, and observable evidence
  3. Sourcing & Network Intelligence — model the sourcing graph, track which channels produce the strongest opportunities, feed funded-deal outcomes back so it learns which channels generate quality, not just volume

## Person D — Experience Layer (UX & Design, 15%)

**Owns:** the investor-facing UX. Notion-level approachability, Bloomberg-level analytical depth — intuitive enough to use without technical support; clarity and usability are non-negotiable. Smallest evaluation slice — if forced to trade, protect the data and reasoning layers (55% combined) first.

- **Investor dashboard:** ranked list + momentum trend
- **Decision-ready outputs:** memo + adversarial view
- Thesis Engine configuration UI (sectors, stage, geography, check size, ownership, risk appetite)
- Display the three axes separately with trend directions — visually never averaged
- Surface Trust Scores with evidence and uncertainty transparently; render flagged gaps and contradictions clearly
- Natural-language query interface for Multi-Attribute Reasoning
- Founder Score trend over time (not just the latest snapshot)
- Make complex AI reasoning feel effortless and trustworthy for a non-technical investor
- Inbound application page + outbound pipeline view (the "inbound and outbound site" from the notes)

---

## Scope (applies to everyone)

- **In scope:** Sourcing → Screening → Diligence → Decision
- **Out of scope:** portfolio monitoring, follow-on, fund ops, exit — don't spend hackathon time designing UI for them. The "fund that runs itself" is ambition framing, not a deliverable
- If we can only nail one thing: sourcing wins — build sourcing deep, then a thin-but-transparent Intelligence layer over it, not a polished reasoner over shallow data
