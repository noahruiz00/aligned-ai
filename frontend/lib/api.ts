const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

export interface Dashboard {
  user: { id: number; name: string; household_type: Household; status: ClientStatus };
  values: ValuesProfile | null;
  purpose: Purpose | null;
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
  insights: Insights | null;
  transcript: ChatMessage[];
  notes: Note[];
}

export interface ClientSummary {
  id: number;
  name: string;
  household_type: Household;
  status: ClientStatus;
  purpose: string | null;
  values: string[];
  overall: number | null;
  created_at: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

const post = <T,>(path: string, body: unknown) => request<T>(path, { method: "POST", body: JSON.stringify(body) });

export const api = {
  health: () => request<{ ok: boolean; demo_mode: boolean; model: string | null }>("/health"),
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
};
