// Single source of truth for data access.
// All components import from here. Mock implementations will be swapped for
// fetch() calls to a FastAPI backend without touching any consumer.

export type ConfidenceTier = "insufficient_data" | "corroborated" | "contradicted";
export type Trend = "improving" | "declining" | "stable";
export type AxisRating = "bullish" | "neutral" | "bear";
export type AppStatus = "submitted" | "screened_pass" | "screened_fail";
export type SignalStatus = "identified" | "activated" | "converged";

export interface DataPoint {
  id: number;
  attribute_name: string;
  value: string;
  confidence_score: number | null;
  confidence_tier: ConfidenceTier | null;
  source_name: string;
  source_reliability: number;
  observed_at: string | null;
}

export interface Contradiction {
  id: number;
  attribute_name: string;
  value_a: string;
  source_a: string;
  value_b: string;
  source_b: string;
  description: string;
  detected_at: string;
}

export interface FounderScorePoint {
  score: number;
  coverage: string;
  computed_at: string;
}

export interface CategoryCoverage {
  category: "technical_execution" | "track_record" | "recognition" | "network";
  weight: number;
  has_data: boolean;
  attribute_names: string[];
}

export interface Founder {
  entity_id: number;
  canonical_name: string;
  founder_score: FounderScorePoint | null;
  score_history: FounderScorePoint[];
  category_coverage: CategoryCoverage[];
  data_points: DataPoint[];
  contradictions: Contradiction[];
  identifiers: { type: string; value: string }[];
}

export interface Company {
  entity_id: number;
  canonical_name: string;
  type: "company";
  data_points: DataPoint[];
  identifiers: { type: string; value: string }[];
}

export type Entity =
  | ({ type: "founder" } & Founder)
  | Company;

export interface AxisScore {
  axis: "founder" | "market" | "idea_vs_market";
  rating: AxisRating;
  score: number;
  rationale: string;
  trend: Trend;
  computed_at: string;
}

export interface Memo {
  company_snapshot: string;
  investment_hypotheses: string[];
  swot: {
    strengths: string[];
    weaknesses: string[];
    opportunities: string[];
    risks: string[];
  };
  problem_and_product: string;
  traction_and_kpis: string;
  gaps_flagged: string[];
  model_used: string;
  generated_at: string;
}

export interface ThesisFit {
  in_thesis: boolean;
  rationale: string;
  computed_at: string;
}

export interface Recommendation {
  verdict: "invest" | "pass" | "needs_review";
  rationale: string;
  derivation: string;
}

export interface Opportunity {
  application_id: number;
  origin: "inbound" | "outbound";
  company_name: string;
  founder: Founder | null;
  status: AppStatus;
  screen_reason: string | null;
  first_signal_at: string;
  submitted_at: string;
  screened_at: string | null;
  hours_to_screen: number | null;
  memo_generated_at: string | null;
  hours_to_decision: number | null;
  thesis_fit: ThesisFit | null;
  axes: AxisScore[] | null;
  memo: Memo | null;
  recommendation: Recommendation | null;
  trust_flags_open: number;
}

export interface OutboundSignal {
  id: number;
  founder_name: string;
  conviction_score: number;
  status: SignalStatus;
  detected_at: string;
  source_channel: string;
}

export interface NeedsReviewRecord {
  raw_record_id: number;
  source_name: string;
  payload_preview: string;
  candidate_entities: {
    entity_id: number;
    canonical_name: string;
    matched_identifier: string;
  }[];
  ingested_at: string;
}

export interface Thesis {
  sectors: string[];
  stage: string;
  geography: string[];
  check_size_min: number;
  check_size_max: number;
  ownership_target_pct: number;
  risk_appetite: string;
  updated_at: string;
}

// --- helpers ---

const delay = <T,>(v: T, ms = 300): Promise<T> =>
  new Promise((r) => setTimeout(() => r(v), ms));

function computeRecommendation(
  thesis_fit: ThesisFit | null,
  axes: AxisScore[] | null,
  trust_flags_open: number,
): Recommendation | null {
  if (!thesis_fit || !axes) return null;
  const hasBear = axes.some((a) => a.rating === "bear");
  const hasBullish = axes.some((a) => a.rating === "bullish");
  const derivation =
    'invest = thesis_fit.in_thesis AND no axis bear AND trust_flags_open = 0; needs_review = axes disagree (bullish AND bear) OR trust_flags_open > 0; else pass.';
  if (thesis_fit.in_thesis && !hasBear && trust_flags_open === 0) {
    return {
      verdict: "invest",
      rationale:
        "In thesis, no axis rated bear, no open trust flags. Deterministic invest.",
      derivation,
    };
  }
  if ((hasBullish && hasBear) || trust_flags_open > 0) {
    return {
      verdict: "needs_review",
      rationale:
        trust_flags_open > 0
          ? `${trust_flags_open} open trust flag(s) block a clean call.`
          : "Axes disagree — at least one bullish and one bear signal.",
      derivation,
    };
  }
  return {
    verdict: "pass",
    rationale: thesis_fit.in_thesis
      ? "In thesis but a bear axis without offsetting bullish evidence."
      : "Out of thesis and no bullish/bear conflict to warrant review.",
    derivation,
  };
}

// --- mock data ---

const now = Date.now();
const hoursAgo = (h: number) => new Date(now - h * 3600_000).toISOString();

// Cross-source founder: github + hn + huggingface, corroborated
const founderCrossSource: Founder = {
  entity_id: 101,
  canonical_name: "Elena Vogt",
  founder_score: { score: 82, coverage: "4/4", computed_at: hoursAgo(2) },
  score_history: [
    { score: 61, coverage: "2/4", computed_at: hoursAgo(240) },
    { score: 68, coverage: "3/4", computed_at: hoursAgo(180) },
    { score: 71, coverage: "3/4", computed_at: hoursAgo(120) },
    { score: 76, coverage: "4/4", computed_at: hoursAgo(72) },
    { score: 80, coverage: "4/4", computed_at: hoursAgo(24) },
    { score: 82, coverage: "4/4", computed_at: hoursAgo(2) },
  ],
  category_coverage: [
    {
      category: "technical_execution",
      weight: 0.3,
      has_data: true,
      attribute_names: ["github_stars", "github_contributions", "huggingface_downloads"],
    },
    {
      category: "track_record",
      weight: 0.25,
      has_data: true,
      attribute_names: ["prior_exits", "employee_count_prior"],
    },
    {
      category: "recognition",
      weight: 0.25,
      has_data: true,
      attribute_names: ["hn_points", "arxiv_citations"],
    },
    {
      category: "network",
      weight: 0.2,
      has_data: true,
      attribute_names: ["accelerator_cohort"],
    },
  ],
  data_points: [
    {
      id: 1,
      attribute_name: "github_stars",
      value: "14,200",
      confidence_score: 0.94,
      confidence_tier: "corroborated",
      source_name: "github",
      source_reliability: 0.9,
      observed_at: hoursAgo(4),
    },
    {
      id: 2,
      attribute_name: "github_contributions",
      value: "3,140 last year",
      confidence_score: 0.9,
      confidence_tier: "corroborated",
      source_name: "github",
      source_reliability: 0.9,
      observed_at: hoursAgo(4),
    },
    {
      id: 3,
      attribute_name: "hn_points",
      value: "1,820",
      confidence_score: 0.85,
      confidence_tier: "corroborated",
      source_name: "hackernews",
      source_reliability: 0.75,
      observed_at: hoursAgo(6),
    },
    {
      id: 4,
      attribute_name: "huggingface_downloads",
      value: "612,000",
      confidence_score: 0.88,
      confidence_tier: "corroborated",
      source_name: "huggingface",
      source_reliability: 0.85,
      observed_at: hoursAgo(8),
    },
    {
      id: 5,
      attribute_name: "arxiv_citations",
      value: "412",
      confidence_score: 0.8,
      confidence_tier: "corroborated",
      source_name: "arxiv",
      source_reliability: 0.85,
      observed_at: hoursAgo(20),
    },
    {
      id: 6,
      attribute_name: "accelerator_cohort",
      value: "YC W23",
      confidence_score: 0.95,
      confidence_tier: "corroborated",
      source_name: "ycombinator",
      source_reliability: 0.95,
      observed_at: hoursAgo(30),
    },
  ],
  contradictions: [],
  identifiers: [
    { type: "github_username", value: "evogt" },
    { type: "hackernews_username", value: "evogt" },
    { type: "huggingface_username", value: "elena-vogt" },
    { type: "email", value: "elena@lumen.ai" },
  ],
};

// Cold-start founder
const founderColdStart: Founder = {
  entity_id: 102,
  canonical_name: "Amara Okoye",
  founder_score: null,
  score_history: [],
  category_coverage: [
    {
      category: "technical_execution",
      weight: 0.3,
      has_data: false,
      attribute_names: [],
    },
    {
      category: "track_record",
      weight: 0.25,
      has_data: false,
      attribute_names: [],
    },
    {
      category: "recognition",
      weight: 0.25,
      has_data: true,
      attribute_names: ["university_challenge_placement"],
    },
    { category: "network", weight: 0.2, has_data: false, attribute_names: [] },
  ],
  data_points: [
    {
      id: 20,
      attribute_name: "university_challenge_placement",
      value: "ETH Zurich Deep Tech Challenge – 3rd place",
      confidence_score: 0.35,
      confidence_tier: "insufficient_data",
      source_name: "events",
      source_reliability: 0.5,
      observed_at: hoursAgo(72),
    },
    {
      id: 21,
      attribute_name: "prior_role",
      value: "PhD candidate, robotics",
      confidence_score: 0.4,
      confidence_tier: "insufficient_data",
      source_name: "university_challenge",
      source_reliability: 0.55,
      observed_at: hoursAgo(72),
    },
    {
      id: 22,
      attribute_name: "public_talks",
      value: "1 lightning talk",
      confidence_score: 0.3,
      confidence_tier: "insufficient_data",
      source_name: "events",
      source_reliability: 0.5,
      observed_at: hoursAgo(96),
    },
  ],
  contradictions: [],
  identifiers: [{ type: "email", value: "amara@kinesis.dev" }],
};

// Contradictions founder
const founderContradiction: Founder = {
  entity_id: 103,
  canonical_name: "Marcus Reinhardt",
  founder_score: { score: 64, coverage: "3/4", computed_at: hoursAgo(3) },
  score_history: [
    { score: 58, coverage: "2/4", computed_at: hoursAgo(120) },
    { score: 62, coverage: "3/4", computed_at: hoursAgo(72) },
    { score: 66, coverage: "3/4", computed_at: hoursAgo(36) },
    { score: 64, coverage: "3/4", computed_at: hoursAgo(3) },
  ],
  category_coverage: [
    {
      category: "technical_execution",
      weight: 0.3,
      has_data: true,
      attribute_names: ["github_stars", "patents_filed"],
    },
    {
      category: "track_record",
      weight: 0.25,
      has_data: true,
      attribute_names: ["employee_count", "revenue"],
    },
    {
      category: "recognition",
      weight: 0.25,
      has_data: true,
      attribute_names: ["hn_points"],
    },
    { category: "network", weight: 0.2, has_data: false, attribute_names: [] },
  ],
  data_points: [
    {
      id: 30,
      attribute_name: "github_stars",
      value: "3,120",
      confidence_score: 0.9,
      confidence_tier: "corroborated",
      source_name: "github",
      source_reliability: 0.9,
      observed_at: hoursAgo(5),
    },
    {
      id: 31,
      attribute_name: "patents_filed",
      value: "4",
      confidence_score: 0.85,
      confidence_tier: "corroborated",
      source_name: "patents",
      source_reliability: 0.85,
      observed_at: hoursAgo(48),
    },
    {
      id: 32,
      attribute_name: "revenue",
      value: "50,000",
      confidence_score: 0.5,
      confidence_tier: "contradicted",
      source_name: "deck",
      source_reliability: 0.55,
      observed_at: hoursAgo(24),
    },
    {
      id: 33,
      attribute_name: "revenue",
      value: "12,000",
      confidence_score: 0.7,
      confidence_tier: "contradicted",
      source_name: "sec_edgar",
      source_reliability: 0.95,
      observed_at: hoursAgo(20),
    },
    {
      id: 34,
      attribute_name: "employee_count",
      value: "22",
      confidence_score: 0.5,
      confidence_tier: "contradicted",
      source_name: "tavily",
      source_reliability: 0.6,
      observed_at: hoursAgo(18),
    },
    {
      id: 35,
      attribute_name: "employee_count",
      value: "9",
      confidence_score: 0.6,
      confidence_tier: "contradicted",
      source_name: "deck",
      source_reliability: 0.55,
      observed_at: hoursAgo(24),
    },
    {
      id: 36,
      attribute_name: "hn_points",
      value: "240",
      confidence_score: 0.75,
      confidence_tier: "corroborated",
      source_name: "hackernews",
      source_reliability: 0.75,
      observed_at: hoursAgo(30),
    },
  ],
  contradictions: [
    {
      id: 1,
      attribute_name: "revenue",
      value_a: "50,000",
      source_a: "deck",
      value_b: "12,000",
      source_b: "sec_edgar",
      description: "revenue: '50000' conflicts with '12000'",
      detected_at: hoursAgo(20),
    },
    {
      id: 2,
      attribute_name: "employee_count",
      value_a: "22",
      source_a: "tavily",
      value_b: "9",
      source_b: "deck",
      description: "employee_count: '22' conflicts with '9'",
      detected_at: hoursAgo(18),
    },
  ],
  identifiers: [
    { type: "github_username", value: "mreinhardt" },
    { type: "email", value: "marcus@ferric.io" },
  ],
};

// Generic founders (used by other opportunities)
function makeGenericFounder(
  id: number,
  name: string,
  score: number,
  coverage: string,
): Founder {
  const hist: FounderScorePoint[] = [];
  for (let i = 5; i >= 0; i--) {
    hist.push({
      score: Math.max(20, score - i * 3 + (i % 2 === 0 ? 2 : -1)),
      coverage,
      computed_at: hoursAgo(24 * i + 2),
    });
  }
  const dps: DataPoint[] = [
    {
      id: id * 100 + 1,
      attribute_name: "github_stars",
      value: `${300 + id * 47}`,
      confidence_score: 0.85,
      confidence_tier: "corroborated",
      source_name: "github",
      source_reliability: 0.9,
      observed_at: hoursAgo(id + 4),
    },
    {
      id: id * 100 + 2,
      attribute_name: "employee_count",
      value: `${5 + (id % 15)}`,
      confidence_score: 0.72,
      confidence_tier: "corroborated",
      source_name: "opencorporates",
      source_reliability: 0.8,
      observed_at: hoursAgo(id + 10),
    },
    {
      id: id * 100 + 3,
      attribute_name: "hn_points",
      value: `${40 + id * 11}`,
      confidence_score: 0.68,
      confidence_tier: "corroborated",
      source_name: "hackernews",
      source_reliability: 0.75,
      observed_at: hoursAgo(id + 16),
    },
    {
      id: id * 100 + 4,
      attribute_name: "prior_role",
      value: id % 2 === 0 ? "Senior ML Engineer" : "Founder (prior startup)",
      confidence_score: 0.55,
      confidence_tier: "insufficient_data",
      source_name: "tavily",
      source_reliability: 0.6,
      observed_at: hoursAgo(id + 22),
    },
  ];
  return {
    entity_id: id,
    canonical_name: name,
    founder_score: { score, coverage, computed_at: hoursAgo(2) },
    score_history: hist,
    category_coverage: [
      {
        category: "technical_execution",
        weight: 0.3,
        has_data: true,
        attribute_names: ["github_stars"],
      },
      {
        category: "track_record",
        weight: 0.25,
        has_data: true,
        attribute_names: ["employee_count"],
      },
      {
        category: "recognition",
        weight: 0.25,
        has_data: true,
        attribute_names: ["hn_points"],
      },
      {
        category: "network",
        weight: 0.2,
        has_data: coverage.startsWith("4"),
        attribute_names: coverage.startsWith("4") ? ["accelerator_cohort"] : [],
      },
    ],
    data_points: dps,
    contradictions: [],
    identifiers: [
      { type: "github_username", value: name.split(" ")[0].toLowerCase() },
      { type: "email", value: `${name.split(" ")[0].toLowerCase()}@company.io` },
    ],
  };
}

// Build the 12 opportunities
function buildAxes(
  founderS: number,
  marketS: number,
  ideaS: number,
): AxisScore[] {
  const rate = (s: number): AxisRating =>
    s >= 65 ? "bullish" : s <= 45 ? "bear" : "neutral";
  const trend = (s: number): Trend =>
    s >= 65 ? "improving" : s <= 45 ? "declining" : "stable";
  return [
    {
      axis: "founder",
      rating: rate(founderS),
      score: founderS,
      rationale:
        founderS >= 65
          ? "Strong technical footprint and prior shipping cadence."
          : founderS <= 45
            ? "Thin public track record; unclear execution history."
            : "Mixed signal, some technical depth but limited public output.",
      trend: trend(founderS),
      computed_at: hoursAgo(3),
    },
    {
      axis: "market",
      rating: rate(marketS),
      score: marketS,
      rationale:
        marketS >= 65
          ? "Category is expanding, TAM re-rated in the last 12 months."
          : marketS <= 45
            ? "Category is crowded; incumbents compressing margin."
            : "Adjacent tailwinds but no obvious wedge into a large budget line.",
      trend: trend(marketS),
      computed_at: hoursAgo(3),
    },
    {
      axis: "idea_vs_market",
      rating: rate(ideaS),
      score: ideaS,
      rationale:
        ideaS >= 65
          ? "Product wedge aligns with a specific buyer with budget authority."
          : ideaS <= 45
            ? "Product is a feature; buyer motion is unclear."
            : "Reasonable framing, but distribution advantage is not yet proven.",
      trend: trend(ideaS),
      computed_at: hoursAgo(3),
    },
  ];
}

function makeMemo(company: string, gaps: string[] = []): Memo {
  return {
    company_snapshot: `${company} is building automation for a specific enterprise workflow, currently piloting with 2–3 design partners and iterating on a paid pilot motion.`,
    investment_hypotheses: [
      "The buyer has a line-item budget for this problem and is switching from spreadsheets.",
      "Model quality is a durable moat given the team's compounded data advantage.",
      "The team's shipping cadence outpaces two well-funded incumbents.",
    ],
    swot: {
      strengths: [
        "Technical founding team with prior shipped systems.",
        "Design partner traction with measurable ROI signal.",
      ],
      weaknesses: [
        "Small team, key-person risk on the technical lead.",
        "Sales motion is still founder-led and undocumented.",
      ],
      opportunities: [
        "Adjacent workflow expansion after initial wedge lands.",
        "Ecosystem partnerships with dominant system-of-record vendors.",
      ],
      risks: [
        "Incumbent bundles the feature within 12 months.",
        "Regulatory shift compresses monetization surface.",
      ],
    },
    problem_and_product:
      "Existing tooling is stitched together across three systems; buyers accept high error rates because switching is painful. Product replaces the manual reconciliation step with an automated agent that plugs into existing systems.",
    traction_and_kpis:
      "2 paid pilots at $2–4K MRR each, 60-day activation, 90%+ weekly usage across seats. Sales cycle 4–6 weeks. Net revenue retention not yet measurable.",
    gaps_flagged: gaps,
    model_used: "gpt-5-analyst-v2",
    generated_at: hoursAgo(3),
  };
}

let OPPORTUNITIES: Opportunity[] = [];

function build() {
  OPPORTUNITIES = [];
  let appId = 1;

  const push = (o: Omit<Opportunity, "recommendation"> & { recommendation?: Recommendation | null }) => {
    const rec = computeRecommendation(o.thesis_fit, o.axes, o.trust_flags_open);
    OPPORTUNITIES.push({ ...o, recommendation: rec });
  };

  // 1. Cross-source founder – strong invest
  push({
    application_id: appId++,
    origin: "inbound",
    company_name: "Lumen AI",
    founder: founderCrossSource,
    status: "screened_pass",
    screen_reason: null,
    first_signal_at: hoursAgo(19),
    submitted_at: hoursAgo(19),
    screened_at: hoursAgo(17),
    hours_to_screen: 2,
    memo_generated_at: hoursAgo(4),
    hours_to_decision: 15,
    thesis_fit: {
      in_thesis: true,
      rationale: "AI infra, seed, EU-based, within check size.",
      computed_at: hoursAgo(4),
    },
    axes: buildAxes(85, 72, 78),
    memo: makeMemo("Lumen AI", [
      "Cap table: not disclosed",
      "Customer references: unavailable at this stage",
    ]),
    trust_flags_open: 0,
  });

  // 2. Cold-start founder – submitted
  push({
    application_id: appId++,
    origin: "inbound",
    company_name: "Kinesis Robotics",
    founder: founderColdStart,
    status: "submitted",
    screen_reason: null,
    first_signal_at: hoursAgo(2),
    submitted_at: hoursAgo(2),
    screened_at: null,
    hours_to_screen: null,
    memo_generated_at: null,
    hours_to_decision: null,
    thesis_fit: null,
    axes: null,
    memo: null,
    trust_flags_open: 0,
  });

  // 3. Contradiction founder – needs_review (2 trust flags)
  push({
    application_id: appId++,
    origin: "inbound",
    company_name: "Ferric Systems",
    founder: founderContradiction,
    status: "screened_pass",
    screen_reason: null,
    first_signal_at: hoursAgo(22),
    submitted_at: hoursAgo(22),
    screened_at: hoursAgo(21),
    hours_to_screen: 1,
    memo_generated_at: hoursAgo(6),
    hours_to_decision: 16,
    thesis_fit: {
      in_thesis: true,
      rationale: "Deep tech, seed, EU.",
      computed_at: hoursAgo(6),
    },
    axes: buildAxes(64, 58, 62),
    memo: makeMemo("Ferric Systems", [
      "Revenue figures conflict between deck and SEC filing",
      "Employee count conflict between deck and third-party",
    ]),
    trust_flags_open: 2,
  });

  // 4. Disagreeing axes – founder bullish, market bear
  push({
    application_id: appId++,
    origin: "outbound",
    company_name: "Halcyon Data",
    founder: makeGenericFounder(201, "Priya Raman", 84, "4/4"),
    status: "screened_pass",
    screen_reason: null,
    first_signal_at: hoursAgo(30),
    submitted_at: hoursAgo(30),
    screened_at: hoursAgo(29),
    hours_to_screen: 1,
    memo_generated_at: hoursAgo(12),
    hours_to_decision: 18,
    thesis_fit: {
      in_thesis: true,
      rationale: "Data infra, seed, US.",
      computed_at: hoursAgo(12),
    },
    axes: buildAxes(84, 38, 55),
    memo: makeMemo("Halcyon Data"),
    trust_flags_open: 0,
  });

  // 5. Disagreeing axes – market bullish, founder bear
  push({
    application_id: appId++,
    origin: "inbound",
    company_name: "Sable Legal",
    founder: makeGenericFounder(202, "Jonas Weber", 42, "2/4"),
    status: "screened_pass",
    screen_reason: null,
    first_signal_at: hoursAgo(40),
    submitted_at: hoursAgo(40),
    screened_at: hoursAgo(39),
    hours_to_screen: 1,
    memo_generated_at: hoursAgo(18),
    hours_to_decision: 22,
    thesis_fit: {
      in_thesis: true,
      rationale: "Vertical AI, seed, EU.",
      computed_at: hoursAgo(18),
    },
    axes: buildAxes(42, 74, 60),
    memo: makeMemo("Sable Legal"),
    trust_flags_open: 0,
  });

  // 6. Disagreeing axes – idea_vs_market bear
  push({
    application_id: appId++,
    origin: "outbound",
    company_name: "Northline Logistics",
    founder: makeGenericFounder(203, "Sara Nilsson", 70, "3/4"),
    status: "screened_pass",
    screen_reason: null,
    first_signal_at: hoursAgo(45),
    submitted_at: hoursAgo(45),
    screened_at: hoursAgo(44),
    hours_to_screen: 1,
    memo_generated_at: hoursAgo(20),
    hours_to_decision: 25,
    thesis_fit: {
      in_thesis: true,
      rationale: "Applied AI, seed, EU.",
      computed_at: hoursAgo(20),
    },
    axes: buildAxes(70, 68, 40),
    memo: makeMemo("Northline Logistics"),
    trust_flags_open: 0,
  });

  // 7. Out-of-thesis but fully analyzed
  push({
    application_id: appId++,
    origin: "inbound",
    company_name: "Bayou BioMed",
    founder: makeGenericFounder(204, "Andre Laurent", 72, "3/4"),
    status: "screened_pass",
    screen_reason: null,
    first_signal_at: hoursAgo(60),
    submitted_at: hoursAgo(60),
    screened_at: hoursAgo(58),
    hours_to_screen: 2,
    memo_generated_at: hoursAgo(30),
    hours_to_decision: 30,
    thesis_fit: {
      in_thesis: false,
      rationale: "Biotech is outside the current sector focus (AI infra / applied AI).",
      computed_at: hoursAgo(30),
    },
    axes: buildAxes(72, 66, 64),
    memo: makeMemo("Bayou BioMed"),
    trust_flags_open: 0,
  });

  // 8. Clean invest
  push({
    application_id: appId++,
    origin: "outbound",
    company_name: "Corvid Security",
    founder: makeGenericFounder(205, "Naomi Feld", 78, "4/4"),
    status: "screened_pass",
    screen_reason: null,
    first_signal_at: hoursAgo(15),
    submitted_at: hoursAgo(15),
    screened_at: hoursAgo(14),
    hours_to_screen: 1,
    memo_generated_at: hoursAgo(4),
    hours_to_decision: 11,
    thesis_fit: {
      in_thesis: true,
      rationale: "AI security tooling, seed, EU/US.",
      computed_at: hoursAgo(4),
    },
    axes: buildAxes(78, 72, 70),
    memo: makeMemo("Corvid Security"),
    trust_flags_open: 0,
  });

  // 9. Submitted
  push({
    application_id: appId++,
    origin: "inbound",
    company_name: "Pineglass Analytics",
    founder: makeGenericFounder(206, "Tomas Krupka", 55, "2/4"),
    status: "submitted",
    screen_reason: null,
    first_signal_at: hoursAgo(1),
    submitted_at: hoursAgo(1),
    screened_at: null,
    hours_to_screen: null,
    memo_generated_at: null,
    hours_to_decision: null,
    thesis_fit: null,
    axes: null,
    memo: null,
    trust_flags_open: 0,
  });

  // 10. Screened fail – deck too thin
  push({
    application_id: appId++,
    origin: "inbound",
    company_name: "Vermilion Notes",
    founder: null,
    status: "screened_fail",
    screen_reason: "deck too thin (89 bytes < 200)",
    first_signal_at: hoursAgo(8),
    submitted_at: hoursAgo(8),
    screened_at: hoursAgo(8),
    hours_to_screen: 0,
    memo_generated_at: null,
    hours_to_decision: null,
    thesis_fit: null,
    axes: null,
    memo: null,
    trust_flags_open: 0,
  });

  // 11. Screened fail – duplicate
  push({
    application_id: appId++,
    origin: "inbound",
    company_name: "Lumen AI (resubmit)",
    founder: null,
    status: "screened_fail",
    screen_reason: "duplicate of application 3 within 7d",
    first_signal_at: hoursAgo(5),
    submitted_at: hoursAgo(5),
    screened_at: hoursAgo(5),
    hours_to_screen: 0,
    memo_generated_at: null,
    hours_to_decision: null,
    thesis_fit: null,
    axes: null,
    memo: null,
    trust_flags_open: 0,
  });

  // 12. Neutral pass
  push({
    application_id: appId++,
    origin: "outbound",
    company_name: "Cinder Tools",
    founder: makeGenericFounder(207, "Hana Suzuki", 58, "3/4"),
    status: "screened_pass",
    screen_reason: null,
    first_signal_at: hoursAgo(50),
    submitted_at: hoursAgo(50),
    screened_at: hoursAgo(49),
    hours_to_screen: 1,
    memo_generated_at: hoursAgo(26),
    hours_to_decision: 24,
    thesis_fit: {
      in_thesis: true,
      rationale: "Developer tools, seed, EU.",
      computed_at: hoursAgo(26),
    },
    axes: buildAxes(58, 55, 54),
    memo: makeMemo("Cinder Tools"),
    trust_flags_open: 0,
  });
}
build();

const OUTBOUND_SIGNALS: OutboundSignal[] = [
  {
    id: 1,
    founder_name: "Ana Perez",
    conviction_score: 0.86,
    status: "identified",
    detected_at: hoursAgo(2),
    source_channel: "github trending",
  },
  {
    id: 2,
    founder_name: "Yusuf Demir",
    conviction_score: 0.79,
    status: "identified",
    detected_at: hoursAgo(4),
    source_channel: "arxiv paper",
  },
  {
    id: 3,
    founder_name: "Ling Chen",
    conviction_score: 0.72,
    status: "activated",
    detected_at: hoursAgo(20),
    source_channel: "hackernews",
  },
  {
    id: 4,
    founder_name: "Mateo Silva",
    conviction_score: 0.7,
    status: "activated",
    detected_at: hoursAgo(28),
    source_channel: "producthunt",
  },
  {
    id: 5,
    founder_name: "Priya Raman",
    conviction_score: 0.91,
    status: "converged",
    detected_at: hoursAgo(40),
    source_channel: "outbound → inbound",
  },
  {
    id: 6,
    founder_name: "Naomi Feld",
    conviction_score: 0.88,
    status: "converged",
    detected_at: hoursAgo(60),
    source_channel: "referral + github",
  },
];

const NEEDS_REVIEW: NeedsReviewRecord[] = [
  {
    raw_record_id: 501,
    source_name: "github",
    payload_preview:
      '{"username":"jsmith","name":"J. Smith","email":"j@nova.io","stars":1200,...}',
    candidate_entities: [
      {
        entity_id: 401,
        canonical_name: "Jordan Smith",
        matched_identifier: "email: j@nova.io",
      },
      {
        entity_id: 402,
        canonical_name: "Julia Smith",
        matched_identifier: "github: jsmith",
      },
    ],
    ingested_at: hoursAgo(3),
  },
  {
    raw_record_id: 502,
    source_name: "hackernews",
    payload_preview:
      '{"user":"karpathy","points":48200,"about":"Founder of ...","company":"eureka.ai",...}',
    candidate_entities: [
      {
        entity_id: 403,
        canonical_name: "Andrej K.",
        matched_identifier: "hackernews: karpathy",
      },
      {
        entity_id: 404,
        canonical_name: "A. Karpathy (Eureka)",
        matched_identifier: "company: eureka.ai",
      },
    ],
    ingested_at: hoursAgo(5),
  },
  {
    raw_record_id: 503,
    source_name: "tavily",
    payload_preview:
      '{"name":"E. Vogt","affiliation":"Lumen AI","emails":["elena@lumen.ai","evogt@stanford.edu"],...}',
    candidate_entities: [
      {
        entity_id: 101,
        canonical_name: "Elena Vogt",
        matched_identifier: "email: elena@lumen.ai",
      },
      {
        entity_id: 405,
        canonical_name: "E. Vogt (Stanford)",
        matched_identifier: "email: evogt@stanford.edu",
      },
    ],
    ingested_at: hoursAgo(7),
  },
];

let THESIS: Thesis = {
  sectors: ["AI infra", "Applied AI", "Developer tools"],
  stage: "Pre-seed / Seed",
  geography: ["EU", "US"],
  check_size_min: 100_000,
  check_size_max: 100_000,
  ownership_target_pct: 5,
  risk_appetite: "High",
  updated_at: hoursAgo(72),
};

const COMPANIES: Company[] = [
  {
    entity_id: 501,
    canonical_name: "Lumen AI, Inc.",
    type: "company",
    identifiers: [
      { type: "cik", value: "0001998421" },
      { type: "domain", value: "lumen.ai" },
      { type: "yc_batch", value: "W23" },
    ],
    data_points: [
      {
        id: 501,
        attribute_name: "incorporation_state",
        value: "Delaware",
        confidence_score: 0.98,
        confidence_tier: "corroborated",
        source_name: "sec_edgar",
        source_reliability: 0.95,
        observed_at: hoursAgo(30),
      },
      {
        id: 502,
        attribute_name: "yc_batch",
        value: "W23",
        confidence_score: 0.99,
        confidence_tier: "corroborated",
        source_name: "ycombinator",
        source_reliability: 0.95,
        observed_at: hoursAgo(48),
      },
      {
        id: 503,
        attribute_name: "last_filing",
        value: "Form D, 2024-11-02",
        confidence_score: 0.9,
        confidence_tier: "corroborated",
        source_name: "sec_edgar",
        source_reliability: 0.95,
        observed_at: hoursAgo(72),
      },
    ],
  },
  {
    entity_id: 502,
    canonical_name: "Ferric Systems Ltd.",
    type: "company",
    identifiers: [
      { type: "opencorporates_id", value: "gb/12938471" },
      { type: "domain", value: "ferric.io" },
    ],
    data_points: [
      {
        id: 511,
        attribute_name: "jurisdiction",
        value: "United Kingdom",
        confidence_score: 0.97,
        confidence_tier: "corroborated",
        source_name: "opencorporates",
        source_reliability: 0.9,
        observed_at: hoursAgo(60),
      },
      {
        id: 512,
        attribute_name: "incorporation_date",
        value: "2022-06-14",
        confidence_score: 0.95,
        confidence_tier: "corroborated",
        source_name: "opencorporates",
        source_reliability: 0.9,
        observed_at: hoursAgo(60),
      },
    ],
  },
  {
    entity_id: 503,
    canonical_name: "Kinesis Robotics",
    type: "company",
    identifiers: [
      { type: "yc_batch", value: "S24" },
      { type: "domain", value: "kinesis.dev" },
    ],
    data_points: [
      {
        id: 521,
        attribute_name: "yc_batch",
        value: "S24",
        confidence_score: 0.99,
        confidence_tier: "corroborated",
        source_name: "ycombinator",
        source_reliability: 0.95,
        observed_at: hoursAgo(24),
      },
      {
        id: 522,
        attribute_name: "headcount",
        value: "6",
        confidence_score: 0.7,
        confidence_tier: "corroborated",
        source_name: "opencorporates",
        source_reliability: 0.85,
        observed_at: hoursAgo(96),
      },
      {
        id: 523,
        attribute_name: "public_filings",
        value: "None on file",
        confidence_score: 0.6,
        confidence_tier: "insufficient_data",
        source_name: "sec_edgar",
        source_reliability: 0.95,
        observed_at: hoursAgo(96),
      },
    ],
  },
];

// --- API surface ---

export const client = {
  async listOpportunities(): Promise<Opportunity[]> {
    return delay([...OPPORTUNITIES]);
  },
  async getOpportunity(id: number): Promise<Opportunity | null> {
    return delay(OPPORTUNITIES.find((o) => o.application_id === id) ?? null);
  },
  async searchOpportunities(
    query: string,
  ): Promise<{ opportunity: Opportunity; matched_attributes: string[] }[]> {
    const q = query.trim().toLowerCase();
    if (!q) return delay([]);
    const terms = q.split(/\s+/).filter(Boolean);
    const results = OPPORTUNITIES.map((o) => {
      const matches = new Set<string>();
      const push = (label: string, hay: string) => {
        for (const t of terms) if (hay.toLowerCase().includes(t)) matches.add(label);
      };
      push("company_name", o.company_name);
      if (o.founder) push("founder", o.founder.canonical_name);
      if (o.thesis_fit) push("thesis_rationale", o.thesis_fit.rationale);
      o.axes?.forEach((a) => push(`axis:${a.axis}`, a.rationale));
      o.founder?.data_points.forEach((d) =>
        push(d.attribute_name, `${d.value} ${d.source_name}`),
      );
      return { opportunity: o, matched_attributes: [...matches] };
    }).filter((r) => r.matched_attributes.length > 0);
    return delay(results);
  },
  async listOutboundSignals(): Promise<OutboundSignal[]> {
    return delay([...OUTBOUND_SIGNALS]);
  },
  async submitApplication(input: {
    company_name: string;
    deck_filename: string;
    founder_email?: string;
    github_username?: string;
  }): Promise<Opportunity> {
    const nowIso = new Date().toISOString();
    const newOpp: Opportunity = {
      application_id: 1000 + OPPORTUNITIES.length,
      origin: "inbound",
      company_name: input.company_name,
      founder: input.founder_email
        ? {
            entity_id: 900 + OPPORTUNITIES.length,
            canonical_name: input.founder_email.split("@")[0],
            founder_score: null,
            score_history: [],
            category_coverage: [
              {
                category: "technical_execution",
                weight: 0.3,
                has_data: false,
                attribute_names: [],
              },
              {
                category: "track_record",
                weight: 0.25,
                has_data: false,
                attribute_names: [],
              },
              {
                category: "recognition",
                weight: 0.25,
                has_data: false,
                attribute_names: [],
              },
              {
                category: "network",
                weight: 0.2,
                has_data: false,
                attribute_names: [],
              },
            ],
            data_points: [],
            contradictions: [],
            identifiers: [
              { type: "email", value: input.founder_email },
              ...(input.github_username
                ? [{ type: "github_username", value: input.github_username }]
                : []),
            ],
          }
        : null,
      status: "submitted",
      screen_reason: null,
      first_signal_at: nowIso,
      submitted_at: nowIso,
      screened_at: null,
      hours_to_screen: null,
      memo_generated_at: null,
      hours_to_decision: null,
      thesis_fit: null,
      axes: null,
      memo: null,
      recommendation: null,
      trust_flags_open: 0,
    };
    OPPORTUNITIES = [newOpp, ...OPPORTUNITIES];
    return delay(newOpp);
  },
  async listNeedsReview(): Promise<NeedsReviewRecord[]> {
    return delay([...NEEDS_REVIEW]);
  },
  async resolveRecord(
    id: number,
    _decision:
      | { type: "merge"; entity_id: number }
      | { type: "create_new" },
  ): Promise<{ ok: true }> {
    const idx = NEEDS_REVIEW.findIndex((r) => r.raw_record_id === id);
    if (idx >= 0) NEEDS_REVIEW.splice(idx, 1);
    return delay({ ok: true });
  },
  async listFounders(): Promise<Founder[]> {
    const seen = new Set<number>();
    const out: Founder[] = [];
    for (const o of OPPORTUNITIES) {
      if (o.founder && !seen.has(o.founder.entity_id)) {
        seen.add(o.founder.entity_id);
        out.push(o.founder);
      }
    }
    return delay(out);
  },
  async listEntities(): Promise<Entity[]> {
    const seen = new Set<number>();
    const founders: Entity[] = [];
    for (const o of OPPORTUNITIES) {
      if (o.founder && !seen.has(o.founder.entity_id)) {
        seen.add(o.founder.entity_id);
        founders.push({ type: "founder", ...o.founder });
      }
    }
    return delay([...founders, ...COMPANIES]);
  },
  async getThesis(): Promise<Thesis> {
    return delay({ ...THESIS });
  },
  async saveThesis(t: Thesis): Promise<Thesis> {
    THESIS = { ...t, updated_at: new Date().toISOString() };
    return delay({ ...THESIS });
  },
  // Founder portal: hardcoded to the cross-source founder (Elena Vogt, entity 101).
  async getFounderPortal(): Promise<{
    founder: Founder;
    opportunity: Opportunity | null;
  }> {
    const entityId = 101;
    const opps = OPPORTUNITIES.filter(
      (o) => o.founder?.entity_id === entityId,
    ).sort(
      (a, b) =>
        new Date(b.submitted_at).getTime() - new Date(a.submitted_at).getTime(),
    );
    return delay({
      founder: founderCrossSource,
      opportunity: opps[0] ?? null,
    });
  },
};

