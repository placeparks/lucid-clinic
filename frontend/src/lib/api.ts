const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchApi<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${await res.text()}`);
  }
  return res.json();
}

// ── Types ──────────────────────────────────────────────

export interface PatientSummary {
  id: number;
  account_id: string;
  first_name: string | null;
  last_name: string | null;
  called_name: string | null;
  cell_phone: string | null;
  email: string | null;
  last_appt: string | null;
  city: string | null;
  state: string | null;
  is_dnc: boolean;
  ins_carrier: string | null;
  total_visits: number;
  reengagement_score: number;
  tier: string | null;
}

export interface Patient extends PatientSummary {
  account_type: string | null;
  middle_initial: string | null;
  suffix: string | null;
  sex: string | null;
  marital: string | null;
  birthdate: string | null;
  account_created: string | null;
  address: string | null;
  zip: string | null;
  alt_phone: string | null;
  work_phone: string | null;
  pref_contact: string | null;
  ins_plan_type: string | null;
  ins_group: string | null;
  ins_member_id: string | null;
  ins_code: string | null;
  balance: number;
  pat_balance: number;
  total_charges: number;
  total_receipts: number;
  copay: number;
  ref_by: string | null;
  remarks: string | null;
  employment: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface PatientList {
  patients: PatientSummary[];
  total: number;
  page: number;
  per_page: number;
}

export interface QueueItem {
  id: number;
  patient_id: number | null;
  account_id: string | null;
  full_name: string | null;
  called_name: string | null;
  cell_phone: string | null;
  email: string | null;
  last_appt: string | null;
  days_since_appt: number | null;
  tier: string | null;
  score: number;
  has_insurance: boolean | null;
  total_visits: number;
  city: string | null;
  state: string | null;
  status: string;
  contact_attempts: number;
  last_contacted_at: string | null;
  created_at: string | null;
}

export interface QueueList {
  items: QueueItem[];
  total: number;
  page: number;
  per_page: number;
}

export interface TierCount {
  tier: string;
  count: number;
}

export interface AnalyticsOverview {
  total_patients: number;
  queue_size: number;
  dnc_count: number;
  has_email: number;
  has_phone: number;
  tiers: TierCount[];
}

export interface ContactCoverage {
  has_both: number;
  email_only: number;
  phone_only: number;
  no_contact: number;
}

// ── API Functions ──────────────────────────────────────

export function getPatients(params: Record<string, string | number | boolean | undefined> = {}) {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") qs.set(k, String(v));
  }
  return fetchApi<PatientList>(`/api/patients?${qs}`);
}

export function getPatient(id: number) {
  return fetchApi<Patient>(`/api/patients/${id}`);
}

export function getQueue(params: Record<string, string | number | boolean | undefined> = {}) {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") qs.set(k, String(v));
  }
  return fetchApi<QueueList>(`/api/queue?${qs}`);
}

export function updateQueueStatus(id: number, status: string) {
  return fetchApi<QueueItem>(`/api/queue/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export function getAnalyticsOverview() {
  return fetchApi<AnalyticsOverview>("/api/analytics/overview");
}

export function getContactCoverage() {
  return fetchApi<ContactCoverage>("/api/analytics/contact-coverage");
}

// ── Agent Types ────────────────────────────────────────

export interface AgentSession {
  id: number;
  session_type: string | null;
  task_params: string | null;
  started_at: string | null;
  ended_at: string | null;
  status: string | null;
  records_affected: number;
  screenshot_count: number;
  iterations_used: number;
  error_log: string | null;
  result_summary: string | null;
  created_at: string | null;
}

export interface AgentSessionList {
  sessions: AgentSession[];
  total: number;
  page: number;
  per_page: number;
}

export interface AgentStatus {
  mock_mode: boolean;
  vnc_configured: boolean;
  api_key_configured: boolean;
  running_session_id: number | null;
  available_tasks: string[];
}

export interface Screenshot {
  filename: string;
  path: string;
  step: number;
  action: string;
  size_bytes: number;
  timestamp: string;
}

// ── Agent API Functions ────────────────────────────────

export function getAgentStatus() {
  return fetchApi<AgentStatus>("/api/agent/status");
}

export function getAgentSessions(params: Record<string, string | number | undefined> = {}) {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") qs.set(k, String(v));
  }
  return fetchApi<AgentSessionList>(`/api/agent/sessions?${qs}`);
}

export function getAgentSession(id: number) {
  return fetchApi<AgentSession>(`/api/agent/sessions/${id}`);
}

export function getSessionScreenshots(sessionId: number) {
  return fetchApi<Screenshot[]>(`/api/agent/sessions/${sessionId}/screenshots`);
}

export function submitAgentTask(taskType: string, params: Record<string, unknown> = {}, confirmed = false) {
  return fetchApi<AgentSession>("/api/agent/tasks", {
    method: "POST",
    body: JSON.stringify({ task_type: taskType, params, confirmed }),
  });
}

export function confirmAgentTask(sessionId: number) {
  return fetchApi<AgentSession>(`/api/agent/tasks/${sessionId}/confirm`, {
    method: "POST",
  });
}

export function cancelAgentTask(sessionId: number) {
  return fetchApi<AgentSession>(`/api/agent/tasks/${sessionId}/cancel`, {
    method: "POST",
  });
}

export function getScreenshotUrl(sessionId: number, filename: string) {
  return `${API_URL}/api/agent/sessions/${sessionId}/screenshots/${filename}`;
}

// ── Campaign Types ────────────────────────────────────

export interface Campaign {
  id: number;
  name: string;
  channel: string;
  tier_filter: string | null;
  score_min: number;
  message_template: string;
  subject: string | null;
  status: string;
  total_recipients: number;
  sent_count: number;
  failed_count: number;
  responded_count: number;
  booked_count: number;
  created_at: string | null;
  sent_at: string | null;
}

export interface CampaignList {
  campaigns: Campaign[];
  total: number;
  page: number;
  per_page: number;
}

export interface OutreachMessage {
  id: number;
  campaign_id: number;
  queue_item_id: number | null;
  patient_id: number | null;
  channel: string | null;
  recipient: string | null;
  message_body: string | null;
  subject: string | null;
  status: string;
  external_id: string | null;
  error_message: string | null;
  sent_at: string | null;
  delivered_at: string | null;
  response_text: string | null;
  responded_at: string | null;
  is_opt_out: boolean;
}

export interface MessageList {
  messages: OutreachMessage[];
  total: number;
  page: number;
  per_page: number;
}

export interface CommsStatus {
  mock_mode: boolean;
  twilio_configured: boolean;
  resend_configured: boolean;
}

// ── Campaign API Functions ────────────────────────────

export function getCommsStatus() {
  return fetchApi<CommsStatus>("/api/campaigns/status");
}

export function getCampaigns(params: Record<string, string | number | undefined> = {}) {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") qs.set(k, String(v));
  }
  return fetchApi<CampaignList>(`/api/campaigns?${qs}`);
}

export function getCampaign(id: number) {
  return fetchApi<Campaign>(`/api/campaigns/${id}`);
}

export function createCampaign(data: {
  name: string;
  channel: string;
  tier_filter?: string;
  score_min?: number;
  message_template: string;
  subject?: string;
}) {
  return fetchApi<Campaign>("/api/campaigns", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function sendCampaign(id: number) {
  return fetchApi<Campaign>(`/api/campaigns/${id}/send`, {
    method: "POST",
  });
}

export function getCampaignMessages(campaignId: number, params: Record<string, string | number | undefined> = {}) {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") qs.set(k, String(v));
  }
  return fetchApi<MessageList>(`/api/campaigns/${campaignId}/messages?${qs}`);
}
