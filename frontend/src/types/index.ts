// User and Auth types
export interface User {
  id: string;
  email: string;
  name: string;
  role: "admin" | "tenant_admin" | "tenant_user";
  tenant_id?: string;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

// Tenant types
export interface Tenant {
  id: string;
  name: string;
  plan: "free" | "starter" | "professional" | "enterprise";
  status: "active" | "suspended" | "cancelled";
  created_at: string;
}

// Agent types
export interface Agent {
  id: string;
  tenant_id: string;
  name: string;
  description?: string;
  system_prompt?: string;
  model: string;
  status: "active" | "inactive" | "archived";
  created_at: string;
  updated_at: string;
}

// Chat types
export interface Message {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  tokens_used?: number;
  created_at: string;
}

export interface Conversation {
  id: string;
  agent_id: string;
  title?: string;
  messages: Message[];
  created_at: string;
  updated_at: string;
}

export interface ChatCompletionRequest {
  agent_id: string;
  conversation_id?: string;
  message: string;
  temperature?: number;
  max_tokens?: number;
  stream?: boolean;
}

// Document types
export interface Document {
  id: string;
  agent_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: "pending" | "processing" | "completed" | "failed";
  chunk_count: number;
  summary?: string;
  created_at: string;
}

export interface SearchResult {
  document_id: string;
  chunk_id: string;
  filename: string;
  content: string;
  summary?: string;
  relevance_score: number;
  highlight?: string;
}

// Usage types
export interface UsageQuota {
  tenant_id: string;
  plan: string;
  tokens_limit: number;
  tokens_used: number;
  tokens_remaining: number;
  usage_percentage: number;
  reset_date: string;
  is_exceeded: boolean;
}

export interface UsageSummary {
  tenant_id: string;
  period: string;
  start_date: string;
  end_date: string;
  total_requests: number;
  total_tokens: number;
  estimated_cost_usd: number;
}

// Subscription types
export interface Plan {
  plan: string;
  name: string;
  price_clp: number;
  tokens_monthly: number;
  agents_limit: number;
  documents_limit: number;
  features: string[];
}

export interface Subscription {
  tenant_id: string;
  plan: string;
  plan_details: Plan;
  tokens_used: number;
  tokens_remaining: number;
  agents_count: number;
  documents_count: number;
  current_period_start: string;
  current_period_end: string;
  is_active: boolean;
}

// API Response types
export interface ApiError {
  detail: string;
  status_code?: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
