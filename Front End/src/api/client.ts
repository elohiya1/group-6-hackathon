// Single source of truth for data access.
// All components import from here; nothing else in the app calls fetch()
// directly. Backend is a FastAPI app -- see /api in the repo root.

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
  category: string;
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

export type Entity = ({ type: "founder" } & Founder) | Company;

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

// --- transport -----------------------------------------------------------

const API_BASE = (
  (import.meta.env.VITE_API_BASE_URL as string | undefined) || "http://localhost:8000"
).replace(/\/$/, "");

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (typeof init.body === "string" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  } catch {
    throw new ApiError("Could not reach the server. Make sure the backend is running.", 0);
  }

  if (!res.ok) {
    let detail = res.statusText || `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      // response wasn't JSON -- fall back to statusText
    }
    throw new ApiError(detail, res.status);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// The founder portal has no accounts, so "my application" is whichever
// application_id this browser last submitted from the Founder > Apply form.
const FOUNDER_APPLICATION_KEY = "vcbrain_founder_application_id";

function rememberFounderApplication(applicationId: number) {
  try {
    window.localStorage.setItem(FOUNDER_APPLICATION_KEY, String(applicationId));
  } catch {
    // localStorage unavailable (e.g. private mode) -- founder portal will
    // just show the empty state instead of throwing.
  }
}

function getRememberedFounderApplicationId(): number | null {
  try {
    const raw = window.localStorage.getItem(FOUNDER_APPLICATION_KEY);
    return raw ? Number(raw) : null;
  } catch {
    return null;
  }
}

// --- API surface -----------------------------------------------------------

export const client = {
  async listOpportunities(): Promise<Opportunity[]> {
    return request<Opportunity[]>("/api/opportunities");
  },

  async getOpportunity(id: number): Promise<Opportunity | null> {
    try {
      return await request<Opportunity>(`/api/opportunities/${id}`);
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) return null;
      throw e;
    }
  },

  async searchOpportunities(
    query: string,
  ): Promise<{ opportunity: Opportunity; matched_attributes: string[] }[]> {
    if (!query.trim()) return [];
    return request(`/api/opportunities/search?q=${encodeURIComponent(query)}`);
  },

  async listOutboundSignals(): Promise<OutboundSignal[]> {
    return request<OutboundSignal[]>("/api/outbound-signals");
  },

  async submitApplication(input: {
    company_name: string;
    deck: File;
    founder_email?: string;
    github_username?: string;
  }): Promise<Opportunity> {
    const form = new FormData();
    form.append("company_name", input.company_name);
    form.append("deck", input.deck);
    if (input.founder_email) form.append("founder_email", input.founder_email);
    if (input.github_username) form.append("github_username", input.github_username);
    return request<Opportunity>("/api/applications", { method: "POST", body: form });
  },

  async listNeedsReview(): Promise<NeedsReviewRecord[]> {
    return request<NeedsReviewRecord[]>("/api/needs-review");
  },

  async resolveRecord(
    id: number,
    decision: { type: "merge"; entity_id: number } | { type: "create_new" },
  ): Promise<{ ok: true }> {
    return request(`/api/needs-review/${id}/resolve`, {
      method: "POST",
      body: JSON.stringify(decision),
    });
  },

  async listFounders(): Promise<Founder[]> {
    return request<Founder[]>("/api/founders");
  },

  async listEntities(): Promise<Entity[]> {
    return request<Entity[]>("/api/entities");
  },

  async getThesis(): Promise<Thesis> {
    return request<Thesis>("/api/thesis");
  },

  async saveThesis(t: Thesis): Promise<Thesis> {
    return request<Thesis>("/api/thesis", { method: "PUT", body: JSON.stringify(t) });
  },

  // Founder portal: no accounts, so this reads whichever application_id was
  // remembered locally the last time this browser submitted one via Apply.
  async getFounderPortal(): Promise<{
    founder: Founder | null;
    opportunity: Opportunity | null;
  }> {
    const applicationId = getRememberedFounderApplicationId();
    if (applicationId === null) return { founder: null, opportunity: null };
    try {
      return await request(`/api/founder-portal?application_id=${applicationId}`);
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) return { founder: null, opportunity: null };
      throw e;
    }
  },

  rememberFounderApplication,
};
