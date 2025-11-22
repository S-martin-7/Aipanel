import axios, { AxiosInstance, AxiosError } from "axios";
import type {
  AuthResponse,
  User,
  Agent,
  Conversation,
  Message,
  Document,
  SearchResult,
  UsageQuota,
  UsageSummary,
  Subscription,
  Plan,
  ChatCompletionRequest,
} from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// Create axios instance
const api: AxiosInstance = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Token management
let accessToken: string | null = null;

export const setAccessToken = (token: string | null) => {
  accessToken = token;
  if (token) {
    localStorage.setItem("access_token", token);
  } else {
    localStorage.removeItem("access_token");
  }
};

export const getAccessToken = (): string | null => {
  if (accessToken) return accessToken;
  if (typeof window !== "undefined") {
    accessToken = localStorage.getItem("access_token");
  }
  return accessToken;
};

// Request interceptor
api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor for token refresh
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Token expired - try refresh or redirect to login
      setAccessToken(null);
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  login: async (email: string, password: string): Promise<AuthResponse> => {
    const { data } = await api.post<AuthResponse>("/auth/login", { email, password });
    setAccessToken(data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    return data;
  },

  register: async (email: string, password: string, name: string): Promise<AuthResponse> => {
    const { data } = await api.post<AuthResponse>("/auth/register", { email, password, name });
    setAccessToken(data.access_token);
    return data;
  },

  logout: async (): Promise<void> => {
    try {
      await api.post("/auth/logout");
    } finally {
      setAccessToken(null);
      localStorage.removeItem("refresh_token");
    }
  },

  me: async (): Promise<User> => {
    const { data } = await api.get<User>("/auth/me");
    return data;
  },

  refresh: async (): Promise<AuthResponse> => {
    const refreshToken = localStorage.getItem("refresh_token");
    const { data } = await api.post<AuthResponse>("/auth/refresh", { refresh_token: refreshToken });
    setAccessToken(data.access_token);
    return data;
  },
};

// Agents API
export const agentsApi = {
  list: async (): Promise<Agent[]> => {
    const { data } = await api.get<Agent[]>("/agents");
    return data;
  },

  get: async (id: string): Promise<Agent> => {
    const { data } = await api.get<Agent>(`/agents/${id}`);
    return data;
  },

  create: async (agent: Partial<Agent>): Promise<Agent> => {
    const { data } = await api.post<Agent>("/agents", agent);
    return data;
  },

  update: async (id: string, agent: Partial<Agent>): Promise<Agent> => {
    const { data } = await api.patch<Agent>(`/agents/${id}`, agent);
    return data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/agents/${id}`);
  },
};

// Chat API
export const chatApi = {
  createCompletion: async (request: ChatCompletionRequest): Promise<{ conversation_id: string; message: Message }> => {
    const { data } = await api.post("/chat/completions", request);
    return data;
  },

  streamCompletion: async function* (request: ChatCompletionRequest): AsyncGenerator<string> {
    const response = await fetch(`${API_URL}/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${getAccessToken()}`,
      },
      body: JSON.stringify(request),
    });

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) throw new Error("No response body");

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split("\n");

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = line.slice(6);
          if (data === "[DONE]") return;
          try {
            const parsed = JSON.parse(data);
            if (parsed.delta) yield parsed.delta;
          } catch {
            // Skip invalid JSON
          }
        }
      }
    }
  },

  listConversations: async (agentId?: string): Promise<Conversation[]> => {
    const params = agentId ? { agent_id: agentId } : {};
    const { data } = await api.get("/chat/conversations", { params });
    return data;
  },

  getConversation: async (id: string): Promise<Conversation> => {
    const { data } = await api.get<Conversation>(`/chat/conversations/${id}`);
    return data;
  },

  deleteConversation: async (id: string): Promise<void> => {
    await api.delete(`/chat/conversations/${id}`);
  },
};

// Documents API
export const documentsApi = {
  list: async (agentId?: string): Promise<{ documents: Document[]; total: number }> => {
    const params = agentId ? { agent_id: agentId } : {};
    const { data } = await api.get("/documents", { params });
    return data;
  },

  upload: async (file: File, agentId: string): Promise<Document> => {
    const formData = new FormData();
    formData.append("file", file);
    const { data } = await api.post(`/documents/upload?agent_id=${agentId}`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  },

  get: async (id: string): Promise<Document> => {
    const { data } = await api.get<Document>(`/documents/${id}`);
    return data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/documents/${id}`);
  },

  search: async (query: string, agentId?: string): Promise<{ results: SearchResult[]; total: number }> => {
    const { data } = await api.post("/documents/search", { query, agent_id: agentId });
    return data;
  },
};

// Usage API
export const usageApi = {
  getQuota: async (): Promise<UsageQuota> => {
    const { data } = await api.get<UsageQuota>("/usage/quota");
    return data;
  },

  getSummary: async (period?: string): Promise<UsageSummary> => {
    const params = period ? { period } : {};
    const { data } = await api.get<UsageSummary>("/usage/summary", { params });
    return data;
  },

  getChart: async (days?: number): Promise<{ data_points: { date: string; tokens: number; requests: number }[] }> => {
    const params = days ? { days } : {};
    const { data } = await api.get("/usage/chart", { params });
    return data;
  },
};

// Payments API
export const paymentsApi = {
  getPlans: async (): Promise<Plan[]> => {
    const { data } = await api.get<Plan[]>("/payments/plans");
    return data;
  },

  getSubscription: async (): Promise<Subscription> => {
    const { data } = await api.get<Subscription>("/payments/subscription");
    return data;
  },

  createCheckout: async (plan: string, returnUrl: string): Promise<{ redirect_url: string }> => {
    const { data } = await api.post("/payments/checkout", { plan, return_url: returnUrl });
    return data;
  },

  getHistory: async (): Promise<{ payments: any[]; total: number }> => {
    const { data } = await api.get("/payments/history");
    return data;
  },
};

export default api;
