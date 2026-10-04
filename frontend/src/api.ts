/**
 * Typed client for the AI Virtual Office API.
 *
 * Holds the bearer token in localStorage, attaches it to every request, and
 * raises a typed ApiError so callers can render real messages instead of
 * "something went wrong".
 */

const BASE_URL = "http://localhost:8000/api";

const TOKEN_KEY = "avo.token";

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export const tokenStore = {
  get: (): string | null => {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set: (token: string) => {
    try {
      localStorage.setItem(TOKEN_KEY, token);
    } catch {
      /* private mode - session-only auth is an acceptable degradation */
    }
  },
  clear: () => {
    try {
      localStorage.removeItem(TOKEN_KEY);
    } catch {
      /* ignore */
    }
  },
};

/** Called when the server rejects our token, so the app can bounce to login. */
let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler;
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  { auth = true }: { auth?: boolean } = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  if (!(init.body instanceof FormData) && init.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }
  if (auth) {
    const token = tokenStore.get();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }

  let response: Response;
  try {
    response = await fetch(BASE_URL + path, { ...init, headers });
  } catch {
    throw new ApiError(0, "Cannot reach the API. Is the backend running on port 8000?");
  }

  if (response.status === 401 && auth) {
    tokenStore.clear();
    onUnauthorized?.();
    throw new ApiError(401, "Your session has expired. Please sign in again.");
  }

  if (response.status === 204) return undefined as T;

  const text = await response.text();
  const body = text ? safeParse(text) : null;

  if (!response.ok) {
    throw new ApiError(response.status, extractMessage(body, response.status), body);
  }
  return body as T;
}

function safeParse(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function extractMessage(body: unknown, status: number): string {
  if (typeof body === "string" && body) return body;
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    // FastAPI validation errors arrive as an array of {loc, msg}.
    if (Array.isArray(detail) && detail.length) {
      const first = detail[0] as { msg?: string; loc?: unknown[] };
      const field = Array.isArray(first.loc) ? first.loc[first.loc.length - 1] : null;
      return field ? `${field}: ${first.msg ?? "invalid"}` : (first.msg ?? "Invalid request");
    }
  }
  return `Request failed (${status})`;
}

const get = <T,>(path: string) => request<T>(path);
const post = <T,>(path: string, body?: unknown, opts?: { auth?: boolean }) =>
  request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) }, opts);
const patch = <T,>(path: string, body: unknown) =>
  request<T>(path, { method: "PATCH", body: JSON.stringify(body) });
const del = (path: string) => request<void>(path, { method: "DELETE" });

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */
export interface User {
  id: string;
  email: string;
  full_name: string;
  role: "OWNER" | "ADMIN" | "MEMBER" | "VIEWER";
  company_id: string;
  last_login_at: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Company {
  id: string;
  name: string;
  slug: string;
  industry: string | null;
  target_market: string | null;
  core_services: string | null;
  primary_goal: string | null;
  currency: string;
  headcount: number | null;
  onboarding_complete: boolean;
}

export interface Agent {
  id: string;
  key: string;
  name: string;
  role: string;
  department: string;
  focus: string;
  responsibilities: string[];
  status: "online" | "working" | "idle" | "blocked";
  health: number;
  is_synthesizer: boolean;
  enabled: boolean;
}

export interface AgentTask {
  id: string;
  agent_key: string;
  status: string;
  finding: string | null;
  evidence: string[];
  risks: string[];
  opportunities: string[];
  recommended_action: string | null;
  confidence: number;
  duration_ms: number;
  error: string | null;
}

export interface Citation {
  document_id: string;
  filename: string;
  chunk: number;
  score: number;
  excerpt: string;
}

export interface WorkOrder {
  id: string;
  command: string;
  status: string;
  progress: number;
  mode: string;
  engine: string;
  target_agent_key: string | null;
  document_id?: string | null;
  category?: string | null;
  headline: string | null;
  summary: string | null;
  recommendation: string | null;
  artifact_title: string | null;
  artifact_body: string | null;
  confidence: number;
  risks: string[];
  opportunities: string[];
  next_actions: string[];
  citations: Citation[];
  consulted_agent_keys: string[];
  requires_approval: boolean;
  error: string | null;
  duration_ms: number;
  tokens_used: number;
  created_at: string;
  completed_at: string | null;
  tasks: AgentTask[];
}

export interface WorkOrderSummary {
  id: string;
  command: string;
  status: string;
  progress: number;
  engine: string;
  confidence: number;
  document_id?: string | null;
  category?: string | null;
  headline: string | null;
  recommendation: string | null;
  consulted_agent_keys: string[];
  requires_approval: boolean;
  created_at: string;
}

export interface DocumentRecord {
  id: string;
  filename: string;
  content_type: string | null;
  size_bytes: number;
  status: string;
  classification: string;
  chunk_count: number;
  word_count: number;
  summary: string | null;
  error: string | null;
  created_at: string;
}

export interface Fact {
  id: string;
  category: string;
  title: string;
  statement: string;
  value: string | null;
  classification: "known" | "derived" | "assumption" | "unknown";
  source: string;
  confidence: number;
  document_id: string | null;
  created_at: string;
}

export interface SearchHit {
  chunk_id: string;
  document_id: string;
  filename: string;
  position: number;
  score: number;
  excerpt: string;
}

export interface Kpi {
  key: string;
  label: string;
  value: number;
  display: string;
  unit: string;
  change_pct: number | null;
  direction: "up" | "down" | "flat";
  /** Whether the movement is good news - rising churn is "up" but "bad". */
  sentiment: "good" | "bad" | "neutral";
}

export interface Series {
  key: string;
  label: string;
  unit: string;
  periods: string[];
  values: number[];
}

export interface Analytics {
  currency: string;
  kpis: Kpi[];
  series: Series[];
  health_score: number;
  work_order_stats: Record<string, number>;
}

export interface Metric {
  id: string;
  key: string;
  label: string;
  period: string;
  value: number;
  unit: string;
  department: string | null;
}

export interface Approval {
  id: string;
  work_order_id: string | null;
  title: string;
  description: string | null;
  risk: "Low" | "Medium" | "High";
  owner: string;
  expected_impact: string | null;
  status: "PENDING" | "APPROVED" | "REJECTED" | "CHANGES" | "NONE";
  comment: string | null;
  created_at: string;
  decided_at: string | null;
}

export interface Report {
  id: string;
  code: string;
  title: string;
  date: string;
  summary: string;
  recommendation: string | null;
  health_score: number;
  status: string;
  engine: string;
  findings: { department: string; agent: string; text: string; confidence: number }[];
  risks: string[];
  opportunities: string[];
  next_actions: string[];
  citations: Citation[];
}

export interface AuditEvent {
  id: string;
  actor_label: string;
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  detail: Record<string, unknown>;
  at: string;
}

export interface SystemStatus {
  status: string;
  version: string;
  environment: string;
  database: string;
  llm_enabled: boolean;
  llm_model: string | null;
  engine: string;
}

export interface RoutingPreview {
  command: string;
  agents: { key: string; name: string; department: string }[];
  requires_approval: boolean;
}

/* ------------------------------------------------------------------ */
/* Endpoints                                                           */
/* ------------------------------------------------------------------ */
export const api = {
  // auth
  register: (data: {
    email: string;
    password: string;
    full_name: string;
    company_name: string;
    industry?: string;
  }) => post<AuthResponse>("/auth/register", data, { auth: false }),
  login: (email: string, password: string) =>
    post<AuthResponse>("/auth/login", { email, password }, { auth: false }),
  me: () => get<User>("/auth/me"),

  // system
  systemStatus: () =>
    request<SystemStatus>("/system/status", {}, { auth: false }),

  // company
  getCompany: () => get<Company>("/company"),
  updateCompany: (data: Partial<Company>) => patch<Company>("/company", data),

  // agents
  getAgents: () => get<Agent[]>("/agents"),
  getAgent: (key: string) => get<Agent>(`/agents/${key}`),
  getAgentTasks: (key: string) =>
    get<
      {
        id: string;
        work_order_id: string;
        command: string;
        status: string;
        finding: string | null;
        recommended_action: string | null;
        confidence: number;
        evidence: string[];
        duration_ms: number;
        created_at: string;
      }[]
    >(`/agents/${key}/tasks`),
  updateAgent: (key: string, data: Partial<Agent>) => patch<Agent>(`/agents/${key}`, data),

  // work orders
  getWorkOrders: (params?: { agent_key?: string; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.agent_key) q.set("agent_key", params.agent_key);
    if (params?.limit) q.set("limit", String(params.limit));
    const suffix = q.toString() ? `?${q}` : "";
    return get<WorkOrderSummary[]>(`/work-orders${suffix}`);
  },
  getWorkOrder: (id: string) => get<WorkOrder>(`/work-orders/${id}`),
  createWorkOrder: (
    command: string,
    agent_key?: string,
    options?: { document_id?: string; category?: string },
  ) =>
    post<WorkOrder>("/work-orders", {
      command,
      agent_key: agent_key ?? null,
      document_id: options?.document_id ?? null,
      category: options?.category ?? null,
    }),
  previewRouting: (command: string) =>
    get<RoutingPreview>(`/work-orders/preview?command=${encodeURIComponent(command)}`),

  // knowledge
  getDocuments: () => get<DocumentRecord[]>("/knowledge/documents"),
  getDocument: (id: string) =>
    get<DocumentRecord & { chunks: { id: string; position: number; content: string; tokens: number }[] }>(
      `/knowledge/documents/${id}`,
    ),
  deleteDocument: (id: string) => del(`/knowledge/documents/${id}`),
  uploadDocument: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<DocumentRecord>("/knowledge/documents", { method: "POST", body: form });
  },
  search: (q: string, topK = 8) =>
    get<{ query: string; hits: SearchHit[] }>(
      `/knowledge/search?q=${encodeURIComponent(q)}&top_k=${topK}`,
    ),
  getFacts: () => get<Fact[]>("/knowledge/facts"),
  createFact: (data: Partial<Fact> & { statement: string }) => post<Fact>("/knowledge/facts", data),
  deleteFact: (id: string) => del(`/knowledge/facts/${id}`),

  // analytics
  getAnalytics: () => get<Analytics>("/analytics"),
  getMetrics: () => get<Metric[]>("/metrics"),
  upsertMetric: (data: {
    key: string;
    label: string;
    period: string;
    value: number;
    unit: string;
    department?: string | null;
  }) => post<Metric>("/metrics", data),
  deleteMetric: (id: string) => del(`/metrics/${id}`),

  // approvals
  getApprovals: (status?: string) =>
    get<Approval[]>(`/approvals${status ? `?status=${status}` : ""}`),
  decideApproval: (id: string, decision: "approve" | "reject" | "changes", comment?: string) =>
    post<Approval>(`/approvals/${id}/decision`, { decision, comment: comment ?? null }),

  // reports
  getReports: () => get<Report[]>("/reports"),
  getReport: (id: string) => get<Report>(`/reports/${id}`),
  exportReportUrl: (id: string) => `${BASE_URL}/reports/${id}/export`,

  // audit
  getAuditEvents: (limit = 100) => get<AuditEvent[]>(`/audit?limit=${limit}`),
};
