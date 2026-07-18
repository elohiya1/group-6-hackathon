# Data Ingestion, Trust Score & Founder Score Pipeline — Design

**Date:** 2026-07-18
**Owner:** Data/Memory layer (Person A workstream, + Trust Score from Person C per BUILD_PLAN.md)
**Status:** Approved for planning

## 1. Scope

This spec covers the **Memory layer's data processing pipeline**: taking raw, per-source data that has already been fetched from outbound sourcing (GitHub, LinkedIn, Twitter, Tavily, Devpost, Product Hunt, Hacker News, patents, arXiv, Crunchbase/Grata, university startup challenges), and turning it into structured, trustworthy, queryable data for the rest of the system.

**In scope:**
- Ingesting raw per-source blobs from a shared local folder
- Normalizing into a common record shape
- Resolving records to founder/company entities (deterministic dedup)
- Computing a **Trust Score per data point** (source reliability + cross-source corroboration/contradiction), with explicit cold-start handling
- Computing a **Founder Score per person** (persistent, trend over time, renormalized for missing signal categories)
- Persisting everything to local SQLite, readable by teammates' Intelligence/Experience layers

**Out of scope (explicitly deferred):**
- Building the source-specific fetchers/scrapers/API adapters themselves — raw blobs are assumed to already exist, dropped by upstream ingestion (outbound sourcing / Person B's workstream)
- Automated outreach drafting or sending (a downstream consumer of Founder Score / Trust Score, owned elsewhere)
- The 3-axis opportunity score (Founder / Market / Idea-vs-Market) — Person C's Intelligence layer, which takes Founder Score as *one input*, not a substitute
- Self-reported claim extraction from unstructured pitch decks/interviews — this version scores structured data points from public sources, not deck-derived claims

## 2. Data Flow

```
raw blobs (local folder, per-source, source-tagged)
        │
        ▼
   Ingest & Normalize   ── common record shape + timestamp + source tag
        │
        ▼
  Entity Resolution      ── match to existing founder/company entity, or create new
        │
        ▼
  Store data points      ── each attribute stored individually (not flattened per entity)
        │
        ▼
  Trust Score engine      ── per data point: source reliability + corroboration/contradiction
        │
        ▼
  Founder Score engine     ── per founder: weighted aggregate of their data points' signals
        │
        ▼
      SQLite               ── queryable by Intelligence & Experience layers
```

**Ingestion input contract:** raw files land in a watched folder structured by source, e.g. `data/incoming/<source_name>/*.json` (source name matches the `sources` table, e.g. `github`, `linkedin`, `crunchbase`). Each file is one raw payload for one entity-candidate. After processing, files are moved to `data/processed/<source_name>/` for traceability (originals are never discarded, matching the brief's "nothing discarded").

## 3. Data Model (SQLite)

### `sources`
Reference table of the known source channels and their fixed reliability weight.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT UNIQUE | `github`, `linkedin`, `twitter`, `tavily`, `devpost`, `producthunt`, `hackernews`, `patents`, `arxiv`, `crunchbase`, `university_challenge` |
| reliability_weight | REAL | 0–1, config-driven, not hardcoded in logic |

### `entities`
A founder or a company.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| type | TEXT | `founder` \| `company` |
| canonical_name | TEXT | |
| created_at | TIMESTAMP | |

### `entity_identifiers`
Known identifiers used for deterministic matching.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| entity_id | FK → entities | |
| identifier_type | TEXT | `email`, `github_username`, `linkedin_url`, `company_domain`, `twitter_handle`, etc. |
| identifier_value | TEXT | |
| UNIQUE(identifier_type, identifier_value) | | enforces one entity per known identifier |

### `entity_relationships`
Links founders to the companies they're associated with, so Founder Score can follow a person across ventures.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| founder_entity_id | FK → entities | |
| company_entity_id | FK → entities | |
| relationship | TEXT | e.g. `founder_of` |
| created_at | TIMESTAMP | |

### `raw_records`
The untouched ingested payload.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| source_id | FK → sources | |
| entity_id | FK → entities, NULLABLE | null until resolved |
| raw_payload | TEXT (JSON) | verbatim |
| origin_file | TEXT | path, for traceability |
| ingested_at | TIMESTAMP | |
| resolution_status | TEXT | `resolved` \| `new_entity` \| `needs_review` |

### `data_points`
**The core unit** — one row per individual observed attribute. This grain is what makes "confidence per claim, not per company" possible.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| entity_id | FK → entities | |
| raw_record_id | FK → raw_records | |
| source_id | FK → sources | |
| attribute_name | TEXT | e.g. `revenue`, `github_stars`, `job_title`, `user_count` |
| value | TEXT | raw value (numeric values stored as text, parsed by `value_type`) |
| value_type | TEXT | `numeric` \| `categorical` \| `text` |
| observed_at | TIMESTAMP, NULLABLE | timestamp claimed by the source, if present |
| created_at | TIMESTAMP | ingestion time |
| confidence_score | REAL | 0–1 |
| confidence_tier | TEXT | `insufficient_data` \| `corroborated` \| `contradicted` |

### `contradictions`
Conflicting data points on the same entity/attribute — surfaced, never silently resolved.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| entity_id | FK → entities | |
| attribute_name | TEXT | |
| data_point_id_a | FK → data_points | |
| data_point_id_b | FK → data_points | |
| detected_at | TIMESTAMP | |
| description | TEXT | human-readable summary of the conflict |

### `founder_scores`
Current score per founder — one row per founder entity.

| Column | Type | Notes |
|---|---|---|
| entity_id | FK → entities, PK | |
| score | REAL | 0–100 |
| coverage | TEXT | e.g. `"2/5"` — how many signal categories had any data |
| computed_at | TIMESTAMP | |

### `founder_score_history`
Append-only snapshots for trend display (never overwritten).

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| entity_id | FK → entities | |
| score | REAL | |
| coverage | TEXT | |
| computed_at | TIMESTAMP | |

Raw payloads are retained in `raw_records` even after normalization/scoring — matches the brief's "nothing discarded."

## 4. Entity Resolution

Deterministic, exact-identifier matching only (no fuzzy matching in this version — avoids false merges at the cost of missing some matches when identifiers are absent).

Per raw record:
1. Extract whatever identifiers the source-specific payload contains (GitHub blob → username; LinkedIn blob → profile URL; Crunchbase blob → company domain/name; Twitter blob → handle; email wherever present).
2. Look up `entity_identifiers` for an exact match on any extracted identifier.
3. **Exactly one match** → attach data points to that entity; register any newly-seen identifiers against it so future matching improves.
4. **No match** → create a new entity (`founder` or `company`, inferred from payload shape), register its identifiers.
5. **Conflicting matches** (identifiers point to two different existing entities) → do not auto-merge. Set `resolution_status = needs_review`, leave `entity_id` null. Never silently merge two different people/companies.

## 5. Trust Score Computation

Computed per `(entity_id, attribute_name)` group — i.e. across every data point ever recorded for that specific claim about that specific entity.

| Tier | Condition | Investor-facing meaning |
|---|---|---|
| `insufficient_data` | Exactly one source has ever reported this attribute | "Unverified — thin data." Cold-start case: honestly labeled, not treated as suspicious. |
| `corroborated` | 2+ independent sources report consistent values | Score = weighted average of agreeing sources' reliability + a small bonus per additional agreeing source (diminishing returns, capped at 1.0) |
| `contradicted` | 2+ sources report conflicting values | Score lowered; **all conflicting values remain visible** (never silently pick one); a row is written to `contradictions` |

**Agreement check** (config per `value_type`, not a single global rule):
- `numeric`: agree within a configurable tolerance (e.g. ±10%)
- `categorical` / `text`: agree on exact or normalized match

**Source reliability weights** live in the `sources` table / a config file, not hardcoded in scoring logic — e.g. official APIs (GitHub, arXiv, patents, Crunchbase) weighted higher than self-reported/noisy sources (Twitter, LinkedIn profile text, university challenge pages).

This tiering is what implements the cold-start requirement: a founder with only a GitHub profile is `insufficient_data`, not "low trust" — a materially different, honest signal.

## 6. Founder Score

Distinct from Trust Score by design (BUILD_PLAN.md): Founder Score is per-**person**, lives in Memory, persists across ventures, never resets. Trust Score is per-**data-point**, tied to a specific claim. Founder Score is *one input* into Person C's Founder axis, not a substitute for it.

**Computation:**
- A rule-based weighted sum across configured signal categories (e.g. technical execution from GitHub momentum, track record from prior ventures/patents/publications, recognition from hackathon wins/launches/accelerator programs, network signals from career history). Category-to-attribute mapping and weights live in config, not code.
- Each signal's contribution is scaled by its Trust Score tier — a `corroborated` signal counts more than an `insufficient_data` one — keeping Founder Score and Trust Score consistent rather than two disconnected numbers.
- **Missing categories are excluded and the remaining weights renormalized** — a founder with no GitHub and no patents is not scored as if those categories were zero. Alongside the score, a `coverage` value (e.g. `"2/5"`) is stored and surfaced so the investor sees how much evidence backs the number. This directly avoids re-creating the network-gated bias the brief calls out as the problem to solve.
- **Recompute trigger:** whenever new data points land for a founder entity, the score is recalculated and a new row is appended to `founder_score_history` (never overwritten) — this is what lets the Experience layer show a trend, not just a snapshot.

## 7. Interface & Consumption

Storage is local SQLite (no live Supabase project exists for this hackathon yet). Other layers read the file directly rather than through a network service — SQLite has bindings in effectively every language.

To keep that stable even as the underlying schema evolves, this spec includes:
- The documented schema above as the contract
- Read-only SQL views for common access patterns: `v_founder_scores_latest`, `v_data_points_with_confidence`, `v_contradictions_open`
- A thin Python read module (`query.py`) exposing convenience functions: `get_founder_score(entity_id)`, `get_data_points(entity_id, attribute=None)`, etc., for other Python-based layers

## 8. Testing Strategy

- **Entity resolution:** fixtures for exact match, no match (new entity created), conflicting match (flagged `needs_review`, not merged)
- **Trust Score tiers:** single-source → `insufficient_data`; agreeing multi-source → `corroborated` with correct weighted score; conflicting → `contradicted` + row written to `contradictions`
- **Founder Score:** renormalization correctness when categories are missing; `coverage` value correctness; history append-only behavior
- **End-to-end:** a batch of synthetic multi-source raw blobs for one founder run through the full pipeline, asserting final DB state (entities, data_points with correct tiers, founder_score, coverage) matches expectations

## 9. Tech Stack

- **Language:** Python
- **Storage:** local SQLite file
- **Config:** source reliability weights, agreement tolerances, and Founder Score category weights live in config files (not hardcoded), so they can be tuned without code changes
