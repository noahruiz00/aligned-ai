// Always same-origin: the API is proxied under /api (next.config.mjs) so the HttpOnly session cookies are
// first-party. A cross-origin NEXT_PUBLIC_API_URL would make the browser withhold those cookies (SameSite=Lax):
// starting a discovery would work and every following call would be "no active session". Only a relative
// value is honoured; anything else is ignored.
const configured = process.env.NEXT_PUBLIC_API_URL || "";
const API_URL = configured.startsWith("/") ? configured.replace(/\/$/, "") : "/api";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export type StaffRole = "advisor" | "admin";
export type Sharing = "private" | "pending_share" | "shared_with_advisor" | "legacy";

export type Household = "individual" | "couple" | "family";
export type Stage = "discover" | "harvest" | "architect";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  stage?: Stage;
}

export interface ChatResponse {
  conversation_id: number;
  user_id: number;
  reply: string;
  stage: Stage;
  answered: number;
  ready: boolean;
  demo_mode: boolean;
}

export interface ValuesProfile {
  values: { name: string; why: string }[];
  financial_priorities: string[];
  life_goals: string[];
  family_goals: string[];
  legacy_goals: string[];
  philanthropy: string[];
  emotional_cues: string[];
  money_script: string;
}

export interface Purpose {
  purpose_statement: string;
  core_values: { name: string; meaning: string }[];
  meaningful_life_vision: { summary: string; pillars: string[] };
  wealth_philosophy: string;
  legacy_statement: string;
  accountability_measures: string[];
  guides: { investments: string; estate: string; philanthropy: string; cash_flow: string };
}

export type CategoryKey = "cash_flow" | "investment" | "estate" | "philanthropy" | "risk";

export interface Category {
  score: number;
  label: string;
  question: string;
  explanation: string;
  recommendations: string[];
  weight: number;
}

export interface Portrait {
  spending_on_priorities_pct: number;
  has_spending_plan: boolean;
  values_aligned_allocation_pct: number;
  portfolio_values_review: "yes" | "partly" | "no";
  has_will: boolean;
  has_trust: boolean;
  has_legacy_letter: boolean;
  family_conversations: "regular" | "occasional" | "never";
  annual_giving_pct: number;
  giving_alignment: "intentional" | "somewhat" | "ad_hoc";
  has_giving_vehicle: boolean;
  emergency_reserve_months: number;
  insurance_reviewed_recently: boolean;
  concentrated_position: boolean;
}

export interface Score {
  overall: number;
  categories: Record<CategoryKey, Category>;
  themes: string[];
  weighting_rationale: string[];
  portrait: Portrait;
  created_at: string;
}

export interface PurposeSection {
  title: string;
  text: string;
  insight_ids: number[];
}

export interface PurposeSections {
  vision: PurposeSection;
  money_role: PurposeSection;
  purpose_of_wealth: PurposeSection;
  personal_values: PurposeSection;
  financial_values: PurposeSection;
  meaningful_life: PurposeSection;
  family_legacy: PurposeSection;
  community_philanthropy: PurposeSection;
  money_story: PurposeSection;
}

export interface Dashboard {
  user: { id: number; name: string; household_type: Household; status: ClientStatus };
  sharing: Sharing;
  values: ValuesProfile | null;
  purpose: Purpose | null;
  purpose_sections: PurposeSections | null;
  purpose_status: "draft" | "legacy" | null;
  purpose_created_at: string | null;
  score: Score | null;
}

export type ClientStatus = "discovery" | "statement" | "aligned";

export interface Insights {
  summary: string;
  strengths: string[];
  gaps: string[];
  conversation_starters: string[];
  meeting_agenda: string[];
  generated_by: string;
}

export interface Note {
  id: number;
  body: string;
  created_at: string;
}

export interface AdvisorClientDetail extends Dashboard {
  shared: boolean;
  discovery_status: "active" | "paused" | "complete" | null;
  insights: Insights | null;
  transcript: ChatMessage[];
  notes: Note[];
  qa: { rejected_insight_count: number; extraction_runs: number } | null;
}

export interface AdminQa {
  app_env: string;
  demo_mode: boolean;
  model: string | null;
  sessions: number;
  completed: number;
  abandoned: number;
  shared_with_advisor: number;
  extraction_runs: number;
  rejected_insight_count: number;
  needs_clarification_count: number;
  insights_total: number;
  model_errors: number;
  extraction_failures: number;
  rate_limited: number;
  last: Record<string, { at: number; detail: string }>;
}

export interface ClientSummary {
  id: number;
  name: string;
  household_type: Household;
  status: ClientStatus;
  sharing: Sharing;
  shared: boolean;
  discovery_status: "active" | "paused" | "complete" | null;
  last_activity_at: string;
  purpose: string | null;
  values: string[];
  overall: number | null;
  created_at: string;
}

// --- Progressive discovery (methodology modules) ---------------------------

export interface MethodologyQuestion {
  id: number;
  module_id: number;
  key: string;
  section: string;
  prompt: string;
  follow_up_guidance: string;
  classification: Classification;
  required: boolean;
  max_follow_ups: number;
  order: number;
  active: boolean;
  answer_count?: number;
  flags?: string[]; // review notes: duplicates, possible typos (advisor decides)
}

export type Classification = "core" | "follow_up" | "optional" | "inactive";

export interface MethodologyModule {
  id: number;
  key: string;
  title: string;
  description: string;
  intro: string;
  order: number;
  session_group: number;
  follow_up_mode: "pool" | "compose";
  active: boolean;
  counts?: Record<Classification, number>;
  questions: MethodologyQuestion[];
}

export interface ExchangeAnswer {
  id: number;
  text: string;
  skipped: boolean;
  declined: boolean; // "prefer not to answer"
  reflection: string | null;
  created_at: string;
}

export interface Exchange {
  question_id: number;
  key: string;
  section: string;
  classification: Classification;
  prompt: string;
  answer: ExchangeAnswer;
  follow_up: { prompt: string; question_id: number | null; answer: ExchangeAnswer | null } | null;
}

export type StepStatus = "completed" | "in_progress" | "upcoming";

export interface Step {
  key: string;
  title: string;
  kind: "module" | "review" | "purpose";
  status: StepStatus;
  session_group: number | null;
  total: number;
  answered: number;
  index: number;
  optional_available: number;
}

export interface ModuleReflection {
  summary: string;
  themes: { name: string; note: string }[];
  feedback: "yes" | "partly" | "edit" | null;
  correction: string | null;
  generated_by: string;
  created_at: string;
}

export interface DiscoveryCurrent {
  module: { key: string; title: string; intro: string; description: string; session_group: number; session_label: string; index: number };
  question: { id: number; key: string; section: string; classification: Classification; prompt: string; required: boolean; position: number; total: number };
  existing_answer: ExchangeAnswer | null;
  pending_follow_up: { parent_answer_id: number; prompt: string } | null;
  exchanges: Exchange[];
  is_first: boolean;
}

export interface DiscoveryState {
  session: {
    id: number;
    user_id: number;
    name: string;
    household_type: Household;
    status: "active" | "paused" | "complete";
    resume_token: string; // only ever returned to the session's owner
    sharing: Sharing;
    started_at: string;
    last_activity_at: string;
    completed_at: string | null;
  };
  demo_mode: boolean;
  progress_pct: number;
  steps: Step[];
  sessions: { group: number; label: string }[];
  current: DiscoveryCurrent | null;
  modules: { key: string; title: string; exchanges: Exchange[] }[];
  module_reflections: Record<string, ModuleReflection>;
  can_complete: boolean;
}

// --- Structured understanding ------------------------------------------------

export type InsightType =
  | "wealth_purpose" | "personal_values" | "financial_values" | "goals" | "meaningful_life_themes" | "money_role"
  | "money_story" | "money_beliefs" | "family_context" | "legacy_themes" | "community_priorities" | "philanthropic_interests"
  | "work_themes" | "service_themes" | "emotional_themes" | "tensions" | "open_questions" | "uncertainties" | "declined_topic";

export type InsightStatus = "ai_detected" | "needs_clarification" | "client_confirmed" | "client_corrected" | "advisor_confirmed";
export type InsightBasis = "client_fact" | "client_statement" | "ai_interpretation";
export type InsightFeedbackKind = "accurate" | "partly" | "edit" | "clarify";

export interface Evidence {
  id: number;
  question_id: number;
  answer_id: number;
  module: string;
  section: string;
  excerpt: string;
}

export interface Insight {
  id: number;
  client_id: number;
  type: InsightType;
  label: string;
  summary: string;
  basis: InsightBasis;
  confidence: number;
  status: InsightStatus;
  module_key: string;
  primary: boolean; // shown first on the review page; the rest stay available under "show more"
  rank: number | null;
  client_feedback: InsightFeedbackKind | null;
  client_correction: string | null;
  original: { label: string; summary: string; basis: InsightBasis; confidence: number };
  evidence: Evidence[];
  history: { event: string; before: unknown; after: unknown; at: string }[];
  created_at: string;
  updated_at: string;
}

export interface Turn {
  reflection: string | null;
  follow_up: string | null;
  module_completed: string | null;
  suggest_pause: boolean;
  next_module: { key: string; title: string } | null;
  optional_available: number;
}

export interface TurnResponse {
  turn: Turn;
  state: DiscoveryState;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    credentials: "include",
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(body.detail || `Request failed (${res.status})`, res.status);
  }
  return res.json();
}

const post = <T,>(path: string, body: unknown) => request<T>(path, { method: "POST", body: JSON.stringify(body) });
const put = <T,>(path: string, body: unknown) => request<T>(path, { method: "PUT", body: JSON.stringify(body) });
const del = <T,>(path: string) => request<T>(path, { method: "DELETE" });

export const api = {
  health: () => request<{ ok: boolean; demo_mode: boolean; model: string | null; app_env: string }>("/health"),
  login: (password: string) => post<{ role: StaffRole }>("/auth/login", { password }),
  logout: () => post<{ ok: boolean }>("/auth/logout", {}),
  me: () => request<{ role: StaffRole }>("/auth/me"),
  adminQa: () => request<AdminQa>("/admin/qa"),
  adminRevokeToken: (clientId: number) => post<{ client_id: number; resume_link_path: string }>(`/admin/clients/${clientId}/revoke-token`, {}),
  adminDeleteClient: (clientId: number, confirm_name: string) =>
    request<{ deleted: boolean; removed: Record<string, number> }>(`/admin/clients/${clientId}`, { method: "DELETE", body: JSON.stringify({ confirm_name }) }),
  startChat: (name: string, household_type: Household) => post<ChatResponse>("/chat", { name, household_type }),
  sendChat: (conversation_id: number, message: string) => post<ChatResponse>("/chat", { conversation_id, message }),
  analyzeValues: (conversation_id: number) =>
    post<{ user_id: number; values: ValuesProfile }>("/analyze-values", { conversation_id }),
  generatePurpose: (user_id: number) => post<{ user_id: number; purpose: Purpose }>("/generate-purpose", { user_id }),
  calculateScore: (user_id: number, portrait: Portrait) => post<Score>("/calculate-score", { user_id, portrait }),
  dashboard: (user_id: number) => request<Dashboard>(`/client-dashboard?user_id=${user_id}`),
  clients: () => request<ClientSummary[]>("/advisor/clients"),
  client: (id: number) => request<AdvisorClientDetail>(`/advisor/clients/${id}`),
  addNote: (id: number, body: string) => post<Note>(`/advisor/clients/${id}/notes`, { body }),

  // Progressive discovery
  methodology: () => request<MethodologyModule[]>("/methodology"),
  // The session is identified by its HttpOnly cookie; no id travels in the URL.
  startDiscovery: (name: string, household_type: Household) => post<DiscoveryState>("/discovery/start", { name, household_type }),
  resumeDiscovery: (token: string) => post<DiscoveryState>("/discovery/resume", { token }),
  forgetDiscovery: () => post<{ ok: boolean }>("/discovery/forget", {}),
  discovery: () => request<DiscoveryState>("/discovery/me"),
  answer: (body: { question_id: number; text: string; parent_answer_id?: number; input_mode?: "text" | "voice" }) =>
    post<TurnResponse>("/discovery/me/answer", body),
  skip: (body: { question_id: number; parent_answer_id?: number; reason?: "skip" | "prefer_not" }) => post<TurnResponse>("/discovery/me/skip", body),
  back: () => post<DiscoveryState>("/discovery/me/back", {}),
  next: () => post<DiscoveryState>("/discovery/me/next", {}),
  goto: (question_id: number) => post<DiscoveryState>("/discovery/me/goto", { question_id }),
  pause: () => post<DiscoveryState>("/discovery/me/pause", {}),
  deeper: (module_key: string) => post<DiscoveryState>("/discovery/me/deeper", { module_key }),
  share: (sharing: "shared_with_advisor" | "private") => post<DiscoveryState>("/discovery/me/share", { sharing }),
  reflectionFeedback: (moduleKey: string, feedback: "yes" | "partly" | "edit", correction?: string) =>
    post<DiscoveryState>(`/discovery/me/reflections/${moduleKey}/feedback`, { feedback, correction }),
  completeDiscovery: () => post<{ user_id: number; conversation_id: number }>("/discovery/me/complete", {}),
  insights: () => request<{ client_id: number; primary_limit: number; insights: Insight[] }>("/discovery/me/insights"),
  insightFeedback: (insightId: number, feedback: InsightFeedbackKind, text?: string) =>
    post<Insight>(`/discovery/me/insights/${insightId}/feedback`, { feedback, text }),
  refreshInsights: () => post<{ insights: Insight[] }>("/discovery/me/insights/refresh", {}),

  // Methodology admin
  adminMethodology: () => request<MethodologyModule[]>("/admin/methodology"),
  createModule: (body: Partial<MethodologyModule>) => post<MethodologyModule>("/admin/methodology/modules", body),
  updateModule: (id: number, body: Partial<MethodologyModule>) => put<MethodologyModule>(`/admin/methodology/modules/${id}`, body),
  deleteModule: (id: number) => del<{ deleted: boolean; deactivated: boolean }>(`/admin/methodology/modules/${id}`),
  createQuestion: (body: Partial<MethodologyQuestion>) => post<MethodologyQuestion>("/admin/methodology/questions", body),
  updateQuestion: (id: number, body: Partial<MethodologyQuestion>) => put<MethodologyQuestion>(`/admin/methodology/questions/${id}`, body),
  deleteQuestion: (id: number) => del<{ deleted: boolean; deactivated: boolean }>(`/admin/methodology/questions/${id}`),
  reorder: (kind: "modules" | "questions", ids: number[]) => post<{ ok: boolean }>("/admin/methodology/reorder", { kind, ids }),
};
