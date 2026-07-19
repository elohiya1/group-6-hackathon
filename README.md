# The VC Brain 🧠

**Deploying $100K Checks in 24 Hours**

Built for the **Hack-Nation 6th Global AI Hackathon** — Challenge 02, powered by **Maschmeyer Group** ("Investing in Exceptional Founders"), in collaboration with the MIT Club of Northern California and the MIT Club of Germany.

---

## 🎯 The Problem

Imagine running the world's largest Shark Tank for AI innovation. Thousands of ambitious builders — any one of whom could be building the next Cursor, whose founders met at an MIT hackathon before anyone knew to look. The job: find them first, understand what they're capable of, and back them before the rest of the world catches on.

Right now, that's nearly impossible:

- Founders stay invisible until they know the right person
- Their story is scattered across pitch decks, GitHub repos, half-built websites, and social posts nobody reads closely
- Diligence takes weeks; capital flows through networks, not merit
- By the time a fund sees a founder clearly, dozens of equally strong ones have already given up waiting

**The fix has to work both ways.** Some founders get spotted first — a GitHub commit, a hackathon win, a paper worth a phone call. Others simply apply: a student with an idea, a first-time founder with zero connections. Either way, the same thing happens next: **within 24 hours, they know if they just got $100K to build it** — not because of who they know, but because of what the system already knows about them.

**North Star:** an autonomous venture fund with one human in the loop for oversight, not execution. This build covers **Sourcing → Screening → Diligence → Decision**. Downstream stages (portfolio monitoring, follow-on, fund ops, exit) are explicitly out of scope.

## 🏗️ Architecture

Three layers, mapped onto the four pipeline stages:

```
  Sourcing ──► Screening ──► Diligence ──► Decision
  In + outbound  3-axis scoring  Truth-gap check  Memo + score
        │             │              │               │
┌───────▼─────────────▼──────────────▼───────────────▼───────┐
│  EXPERIENCE LAYER — Investor-facing UX                     │
│  · Investor dashboard: ranked list + momentum trend        │
│  · Decision-ready outputs: memo + adversarial view         │
├────────────────────────────────────────────────────────────┤
│  INTELLIGENCE LAYER — Reasoning & scoring                  │
│  · Thesis Engine (fund-specific filter)                    │
│  · Multi-axis score (3 axes + trend)                       │
│  · Trust Score (evidence & flags)                          │
├────────────────────────────────────────────────────────────┤
│  MEMORY LAYER — Data foundation                            │
│  · Structured knowledge base (founders, decks, signals)    │
│  · Timestamped & deduplicated, source-tagged, persistent   │
└────────────────────────────────────────────────────────────┘
```

### Memory — the data foundation (nothing discarded)
- Ingests pitch decks, interviews, launches, GitHub activity, and social traction
- Deduplicates, enriches, timestamps, and tags everything by source
- Houses the **Founder Score** — persists across applications, never resets
- Surfaces the trend over time, not just the latest snapshot

### Intelligence — the reasoning layer
- Operates on top of Memory to produce insights, challenge assumptions, and recommend next steps
- Triggered by an inbound application **or** by signals crossing a conviction threshold on their own
- Transparent about confidence, uncertainty, and the evidence behind every conclusion

### Experience — investor-grade UX
- "Notion-level approachability, Bloomberg-level analytical depth" — usable by a non-technical investor without support
- Ranked founder pipeline with momentum trends, and decision-ready memo output with an adversarial view

## 🔍 Sourcing: The Dual-Track Funnel

**Sourcing is the most important part of the MVP** — the area with the least commercial competition, judged on data richness and smart sourcing ideas, not polish. The goal: surface the strongest founders *before they formally begin fundraising*.

### Inbound — Application & Automated Screening
- **Apply:** deck + company name is the minimum bar. Additional fields only if genuinely needed for a confident 24-hour decision — over-collecting works against you
- **Screen:** a fast first-pass filter removes clearly non-viable ideas before full analysis begins

### Outbound — Founder Identification & Activation
- **Identify:** continuously scan public signal sources; score discoveries the same way as an inbound application
- **Activate:** reach out to the strongest matches directly — *cold outreach, not cold investment*; the goal is to trigger a real application
- **Converge:** activated applications flow into the same Screening step as inbound, so both tracks feed one funnel

### Signal Sources

| Source | Signal |
|---|---|
| GitHub | Commit activity, repo momentum, technical depth |
| LinkedIn | Career history, founder-market fit, network position |
| Twitter / X | Public footprint, distribution ability |
| Devpost & hackathon wins | Shipped projects, team formation, execution speed |
| University startup challenges | Pre-track-record founders surfacing early |
| Product Hunt | Launches and early traction |
| Hacker News | Launch reception, community signal |
| arXiv / recently published papers | Research worth a phone call |
| Public patent search | Novel, defensible technology |
| Crunchbase / Grata | Company data, prior funding, deduplication anchor |
| Tavily (agentic web search) | Enrichment and external cross-verification |

## 🎛️ Thesis Engine

Configurable — **a hardcoded thesis misses the point of the pillar.** The investor sets:

- Sectors, stage, geography
- Check size and ownership targets
- Risk appetite

Every recommendation is filtered and scored through this fund-specific lens.

## ⚖️ Multi-Axis Screening

Every opportunity is scored along **three independent axes — explicitly never averaged** (collapsing them hides exactly the disagreement an investor needs to see):

1. **Founder** — who they are, their traits and track record
2. **Market** — sizing, competitors, SWOT — rated **bullish / neutral / bear**
3. **Idea vs. Market** — does the idea survive scrutiny as-is, or is the team strong enough to pivot?

Each axis carries a trend direction (**improving / declining / stable**) and feeds back into Memory to sharpen future scoring.

### Founder Score ≠ 3-Axis Score

These are distinct by design:

| | Founder Score | 3-Axis Score |
|---|---|---|
| Lives in | Memory layer | Intelligence layer |
| Scope | Per **person** | Per **opportunity** |
| Lifetime | Persists across applications, never resets | Scored fresh each opportunity |
| Relationship | One *input* into the Founder axis | Not a substitute for the Founder Score |

Ship something once, and your next idea starts from a stronger position. The system never forgets, and it never stops updating — a **credit score for founders**.

## 🧾 Diligence: Trust Score & Evidence-Backed Memos

The Trust Score is **per claim, not one number for the company.** Every assertion — traction, revenue, team background, market size — must:

- Trace to specific evidence with a confidence level
- Be verified externally where possible
- Have contradictions flagged *before* they reach the investor

**No fabrication.** Where data is missing, unavailable, or intentionally withheld, it's flagged explicitly (e.g. `Cap table: not disclosed`, `Customer references: unavailable at this stage`) rather than silently omitted or guessed. A memo that clearly marks its own gaps is more trustworthy — and scores higher — than one that fills them in invisibly.

### Investment Memo Structure

*Length rule: as detailed as the decision requires, as brief as clarity allows. Padding counts against you.*

**Required sections:**

| Section | Contents |
|---|---|
| Company snapshot | One-paragraph "in a nutshell": market size, structural problem, urgency, how the product solves it |
| Investment hypotheses | Explicit "why we want to invest" bullets — team quality, market wedge, stickiness/retention, traction signal, defensibility, expansion path |
| SWOT | Strengths, weaknesses, opportunities, risks — short, evidence-backed bullets |
| Problem & product | Core problem(s) in plain language, then the step-by-step product/process solving it |
| Traction & KPIs | Customer count, ARR/revenue, growth trajectory, unit economics (CAC, sales cycle, churn), usage metrics |

**Optional sections** (welcome, but padding counts against you): Team & history · Technology & defensibility · Market sizing (TAM/SAM/SOM with explicit assumptions) · Competition · Financials & round structure · Cap table · Due diligence log · Exit perspective

## 💬 Multi-Attribute Reasoning

Beyond keyword/filter search. The system resolves a compound natural-language query **in one pass — not as five manual filters**:

> *"technical founder, Berlin, AI infra, enterprise traction, no prior VC backing, top-tier accelerator"*

## ❄️ The Cold-Start Case (First-Class, Not an Afterthought)

**A generic ingestion/enrichment pipeline will not score highly if it ignores this.** How do you score a first-time founder with no GitHub, no funding, no network? Without an explicit method for pre-track-record founders, we've just rebuilt the network-gated system this challenge exists to replace.

Our approach:
- A founder with no funding or GitHub history often still has a **public footprint** — social presence, university challenges, hackathon participation, published work
- Build an initial profile from those signals with honest, explicit confidence levels where data is thin
- Directly engages **Area of Research 3**: how much can public footprints (Twitter, LinkedIn) actually predict founder success — the most direct lever on the cold-start weakness

## 📊 Evaluation Criteria

| Criterion | Weight | What's judged |
|---|---|---|
| **Data Architecture & Intelligence** | **30%** | Smart ingestion, deduplication, enrichment, and a reasoning layer honest about what it knows and what it doesn't. *Generic ingestion alone won't score highly if it ignores the cold-start case* |
| **Investment Utility & Execution** | **30%** | A recommendation a human investor could genuinely act on within 24 hours; instrumenting how fast and reliably an opportunity moves from first signal to decision |
| **Intelligent Analysis & Trust** | **25%** | Synthesising fragmented signals into decision-ready insights; Trust Scores surfacing evidence and uncertainty transparently |
| **User Experience & Design** | **15%** | Intuitive, clear, beautiful; makes complex AI reasoning feel effortless and trustworthy for a non-technical investor |

**Prioritization (from the brief's FAQ):** sourcing carries the most weight and is explicitly the priority — but a rich data layer with no honest reasoning on top also scores poorly. **Build sourcing deep, then a thin-but-transparent Intelligence layer over it** — not a polished reasoner over shallow data. If forced to trade, protect the data + reasoning layers (55% combined) before UI polish.

## 🌟 Stretch Goals

Ranked — if there's only time for one, it's **Agentic Traceability** (it directly reinforces the core Trust Score requirement, so it's the highest-leverage add):

1. **Agentic Traceability** — every recommendation cites the exact data point (pitch deck slide, web signal, interview excerpt) that drove the conclusion, with step-level chain-of-thought logging to visualise the full reasoning process
2. **Self-Correction Loops** — a Validator Agent cross-references extracted founder claims against market databases, comparable funding rounds, and observable evidence to catch primary-agent hallucination
3. **Sourcing & Network Intelligence** — model the sourcing graph (programs, institutions, individuals through which founders become visible), track which channels historically produce the strongest opportunities, suggest underexplored channels, and feed funded-deal outcomes back so the model learns which channels generate *quality*, not just volume

## 🔬 Open Research Areas

Genuinely open problems — solving them robustly could be industry-defining:

1. **Confidence Scoring** — can prediction intervals be built around soft-skill assessments like resilience or founder-market fit, given messy and incomplete founder data?
2. **Data Quality vs. Volume** — more data isn't always better; how do you decide what's worth collecting vs. flagging as low-confidence?
3. **Founder Traits & Success** — how much can public footprints (Twitter, LinkedIn) predict founder success, and how would you test it?

## 📦 Data

No dedicated dataset is provided. We bring/synthesise our own:
- Public web data (Crunchbase, LinkedIn, GitHub, ProductHunt, Hacker News, arXiv, patents)
- Synthetic founder profiles with seeded contradictions
- Anonymised / fictional pitch decks

**Ingestion quality beats dataset size.**

## 🚀 Getting Started

The repo has two halves: this directory is the **backend** (Python/FastAPI +
SQLite), and `Front End/` is the **frontend** (TanStack Start / React, built
in Lovable). They run as two separate local servers and talk over HTTP.

```
Backend  (this dir)  → http://localhost:8000   (FastAPI, uvicorn)
Frontend (Front End/) → http://localhost:8080   (Vite dev server)
```

### 1. Install dependencies

```bash
# Backend — from the repo root
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Frontend
cd "Front End"
npm install                      # or bun install, if you have bun
cd ..
```

### 2. Configure environment variables

```bash
# Backend: copy and fill in at least OPENAI_API_KEY
cp .env.example .env

# Frontend: defaults already point at the backend on :8000, override if needed
cp "Front End/.env.example" "Front End/.env"
```

Backend `.env` keys:

| Variable | Required | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | Yes, for Intelligence | Thesis fit, 3-axis scoring, and memo generation call OpenAI (`gpt-4.1-mini`). Without it, applications still get created and screened, but axes/memo stay unset ("not yet analyzed") instead of erroring. |
| `TAVILY_API_KEY`, `GITHUB_TOKEN`, `PRODUCTHUNT_TOKEN`, `PATENTSVIEW_API_KEY`, `COMPANIES_HOUSE_API_KEY`, `OPENCORPORATES_API_KEY` | No | Only used by the `memory_layer fetch` CLI commands that pull outbound sourcing signals — not required to run the API/frontend. |
| `VC_BRAIN_DB_PATH` | No (default `data/vc_brain.db`) | SQLite file the API reads/writes. |
| `CORS_ORIGINS` | No | Extra comma-separated origins allowed to call the API, beyond the default localhost dev ports (3000/5173/4173/8080). |

Frontend `Front End/.env`:

| Variable | Purpose |
|---|---|
| `VITE_API_BASE_URL` | Base URL of the FastAPI backend. Defaults to `http://localhost:8000`. Never hardcode the backend URL in a component — always read it through `src/api/client.ts`. |

### 3. Start the backend

```bash
source .venv/bin/activate
uvicorn api.main:app --reload --port 8000
```

Interactive API docs: http://localhost:8000/docs

### 4. Start the frontend

```bash
cd "Front End"
npm run dev
```

Vite prints the local URL (default `http://localhost:8080`) — open it in a
browser. Pick either role from the entry screen (there are no accounts).

### 5. Verify the connection

```bash
curl http://localhost:8000/api/health          # {"ok":true}
curl http://localhost:8000/api/opportunities   # [] on a fresh DB
```

With both servers running, open the frontend and go to **Pipeline** — a
"No opportunities match these filters." empty state (not an infinite
"Loading…" or a red error banner) confirms the frontend successfully reached
the backend. Submitting an application from **Sourcing** (investor) or
**Apply** (founder role) exercises the full round trip: file upload → intake
→ screen → (if it passes and `OPENAI_API_KEY` is set) thesis fit + 3-axis
scoring + memo generation, all visible back in Pipeline within a few
seconds.

### Running tests

```bash
# Backend unit tests
source .venv/bin/activate
pytest

# Frontend type check, lint, build
cd "Front End"
npx tsc --noEmit
npm run lint
npm run build
```

## 🧭 Scope

**In scope:** Sourcing → Screening → Diligence → Decision.
**Out of scope:** portfolio monitoring, follow-on, fund ops, exit — real stages, but the brief explicitly says not to spend hackathon time on them. The "fund that runs itself" is ambition framing, not a deliverable.

---

*Build the data layer. Build the reasoning layer. Build the experience. Build the infrastructure that gives exceptional founders the capital to begin.*