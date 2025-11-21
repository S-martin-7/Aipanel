// Tipos compartidos entre Backend y Frontend
// AIPanel - Multi-tenant AI Agent Management System

// ============================================
// ENUMS
// ============================================

export enum UserRole {
  SUPER_ADMIN = 'SUPER_ADMIN',
  ADMIN = 'ADMIN',
  USER = 'USER',
}

export enum ServerStatus {
  ACTIVE = 'ACTIVE',
  SUSPENDED = 'SUSPENDED',
  BLOCKED = 'BLOCKED',
}

export enum TenantStatus {
  ACTIVE = 'ACTIVE',
  SUSPENDED = 'SUSPENDED',
  TRIAL = 'TRIAL',
  BLOCKED = 'BLOCKED',
}

export enum PaymentStatus {
  PAID = 'PAID',
  PENDING = 'PENDING',
  OVERDUE = 'OVERDUE',
  CANCELLED = 'CANCELLED',
}

export enum AIModel {
  // OpenAI GPT-5 Series
  GPT5 = 'GPT5',
  GPT5_MINI = 'GPT5_MINI',
  GPT5_NANO = 'GPT5_NANO',

  // OpenAI O-Series (Reasoning)
  O1 = 'O1',
  O1_MINI = 'O1_MINI',
  O3 = 'O3',
  O3_MINI = 'O3_MINI',
  O3_PRO = 'O3_PRO',
  O4_MINI = 'O4_MINI',

  // OpenAI Realtime
  GPT_REALTIME_MINI = 'GPT_REALTIME_MINI',

  // Claude Series
  CLAUDE_SONNET_4_5 = 'CLAUDE_SONNET_4_5',
  CLAUDE_SONNET_4 = 'CLAUDE_SONNET_4',
  CLAUDE_OPUS_4 = 'CLAUDE_OPUS_4',
  CLAUDE_HAIKU_4 = 'CLAUDE_HAIKU_4',

  // Legacy
  GPT4O = 'GPT4O',
  GPT4_TURBO = 'GPT4_TURBO',
}

export enum AgentStatus {
  ACTIVE = 'ACTIVE',
  PAUSED = 'PAUSED',
  ERROR = 'ERROR',
}

export enum DataSourceType {
  PDF = 'PDF',
  WEBPAGE = 'WEBPAGE',
  DOCUMENT = 'DOCUMENT',
  API = 'API',
  IMAGE = 'IMAGE',
  VIDEO = 'VIDEO',
}

export enum DataSourceStatus {
  PENDING = 'PENDING',
  PROCESSING = 'PROCESSING',
  READY = 'READY',
  ERROR = 'ERROR',
}

export enum TransactionType {
  CHARGE = 'CHARGE',
  PAYMENT = 'PAYMENT',
  REFUND = 'REFUND',
  CREDIT = 'CREDIT',
}

export enum BillingPlan {
  FREE = 'FREE',
  STARTER = 'STARTER',
  PROFESSIONAL = 'PROFESSIONAL',
  BUSINESS = 'BUSINESS',
  ENTERPRISE = 'ENTERPRISE',
}

export enum PaymentMethodType {
  CREDIT_CARD = 'CREDIT_CARD',
  DEBIT_CARD = 'DEBIT_CARD',
  BANK_TRANSFER = 'BANK_TRANSFER',
  CRYPTO = 'CRYPTO',
}

// ============================================
// INTERFACES
// ============================================

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  isActive: boolean;
  createdAt: Date;
  updatedAt: Date;
  lastLoginAt?: Date;
}

export interface Server {
  id: string;
  name: string;
  description?: string;
  apiKey: string;
  status: ServerStatus;
  maxTenants: number;
  tenants?: Tenant[];
  createdAt: Date;
  updatedAt: Date;
}

export interface Tenant {
  id: string;
  serverId: string;
  name: string;
  email: string;
  companyName?: string;
  apiKey: string;
  status: TenantStatus;
  paymentStatus: PaymentStatus;
  billingPlan: BillingPlan;
  balance: number;
  creditBalance: number;
  billingCycle: string;
  nextBillingDate?: Date;
  monthlyTokenLimit: number;
  currentMonthUsage: number;
  autoSuspendOnOverage: boolean;
  autoSuspendOnNonPayment: boolean;
  gracePeriodDays: number;
  server?: Server;
  agents?: Agent[];
  createdAt: Date;
  updatedAt: Date;
}

export interface ModelConfig {
  model: AIModel;

  // Parámetros GPT-5
  reasoningLevel?: 'minimal' | 'low' | 'medium' | 'high';

  // Parámetros O-Series
  reasoningEffort?: 'low' | 'medium' | 'high';
  verbosity?: 'low' | 'medium' | 'high';

  // Parámetros tradicionales (solo modelos no-reasoning)
  temperature?: number;
  maxTokens?: number;

  // Parámetros reasoning models
  maxCompletionTokens?: number;

  // Context
  contextWindow?: number;
}

export interface Agent {
  id: string;
  tenantId: string;
  name: string;
  description?: string;
  model: AIModel;
  systemPrompt: string;

  // Configuración del modelo
  reasoningLevel?: string;
  reasoningEffort?: string;
  verbosity?: string;
  temperature?: number;
  maxTokens?: number;
  maxCompletionTokens?: number;
  contextWindow: number;

  // Características
  memoryEnabled: boolean;
  autoLearn: boolean;

  // Estado
  status: AgentStatus;
  totalInteractions: number;
  averageTokensUsed: number;
  totalCost: number;

  tenant?: Tenant;
  dataSources?: DataSource[];
  createdAt: Date;
  updatedAt: Date;
}

export interface DataSource {
  id: string;
  tenantId: string;
  agentId?: string;
  type: DataSourceType;
  name: string;
  description?: string;
  url?: string;
  fileUrl?: string;
  s3Key?: string;
  fileSize?: number;
  mimeType?: string;
  status: DataSourceStatus;
  processedAt?: Date;
  errorMessage?: string;
  vectorStoreId?: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface Conversation {
  id: string;
  agentId: string;
  sessionId: string;
  title?: string;
  messages?: Message[];
  createdAt: Date;
  updatedAt: Date;
}

export interface Message {
  id: string;
  conversationId: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  inputTokens?: number;
  outputTokens?: number;
  reasoningTokens?: number;
  createdAt: Date;
}

export interface Payment {
  id: string;
  tenantId: string;
  amount: number;
  currency: string;
  status: string;
  paymentMethod: PaymentMethodType;
  stripePaymentId?: string;
  stripeCustomerId?: string;
  description?: string;
  metadata?: Record<string, any>;
  createdAt: Date;
  updatedAt: Date;
}

export interface Transaction {
  id: string;
  tenantId: string;
  type: TransactionType;
  amount: number;
  description: string;
  balanceAfter: number;
  metadata?: Record<string, any>;
  createdAt: Date;
}

export interface UsageMetric {
  id: string;
  tenantId: string;
  agentId?: string;
  apiCalls: number;
  inputTokens: number;
  outputTokens: number;
  reasoningTokens: number;
  totalTokens: number;
  inputCost: number;
  outputCost: number;
  reasoningCost: number;
  totalCost: number;
  model: AIModel;
  date: Date;
  errors: number;
  createdAt: Date;
}

export interface Alert {
  id: string;
  type: string;
  severity: 'info' | 'warning' | 'critical';
  title: string;
  message: string;
  targetType: string;
  targetId: string;
  isRead: boolean;
  isResolved: boolean;
  metadata?: Record<string, any>;
  createdAt: Date;
  resolvedAt?: Date;
}

// ============================================
// DTOs (Data Transfer Objects)
// ============================================

export interface CreateServerDto {
  name: string;
  description?: string;
  maxTenants?: number;
}

export interface UpdateServerDto {
  name?: string;
  description?: string;
  status?: ServerStatus;
  maxTenants?: number;
}

export interface CreateTenantDto {
  serverId: string;
  name: string;
  email: string;
  companyName?: string;
  billingPlan?: BillingPlan;
  monthlyTokenLimit?: number;
}

export interface UpdateTenantDto {
  name?: string;
  email?: string;
  companyName?: string;
  status?: TenantStatus;
  billingPlan?: BillingPlan;
  monthlyTokenLimit?: number;
  autoSuspendOnOverage?: boolean;
  autoSuspendOnNonPayment?: boolean;
  gracePeriodDays?: number;
}

export interface CreateAgentDto {
  tenantId: string;
  name: string;
  description?: string;
  model: AIModel;
  systemPrompt: string;
  modelConfig?: Partial<ModelConfig>;
  memoryEnabled?: boolean;
  autoLearn?: boolean;
}

export interface UpdateAgentDto {
  name?: string;
  description?: string;
  model?: AIModel;
  systemPrompt?: string;
  status?: AgentStatus;
  memoryEnabled?: boolean;
  autoLearn?: boolean;
  temperature?: number;
  maxTokens?: number;
  reasoningLevel?: string;
  reasoningEffort?: string;
}

export interface CreateDataSourceDto {
  tenantId: string;
  agentId?: string;
  type: DataSourceType;
  name: string;
  description?: string;
  url?: string;
  file?: File;
}

export interface ChatMessageDto {
  agentId: string;
  sessionId?: string;
  message: string;
  contextFiles?: string[];
}

export interface ChatResponseDto {
  conversationId: string;
  sessionId: string;
  message: string;
  inputTokens: number;
  outputTokens: number;
  reasoningTokens?: number;
  totalTokens: number;
  cost: number;
  model: AIModel;
}

// ============================================
// DASHBOARD METRICS
// ============================================

export interface DashboardMetrics {
  totalServers: number;
  activeServers: number;
  suspendedServers: number;

  totalTenants: number;
  activeTenants: number;
  suspendedTenants: number;

  monthlyRevenue: number;
  pendingPayments: number;
  overdueAccounts: number;

  totalAPICallsToday: number;
  totalTokensToday: number;
  totalCostToday: number;

  usageByModel: {
    model: AIModel;
    calls: number;
    tokens: number;
    cost: number;
  }[];

  recentAlerts: Alert[];
  tenantsNearLimit: Tenant[];
}

export interface TenantDashboard {
  tenant: Tenant;
  currentUsage: {
    tokensUsed: number;
    tokensLimit: number;
    percentageUsed: number;
    estimatedCost: number;
  };
  balance: {
    current: number;
    credit: number;
    total: number;
  };
  agents: {
    total: number;
    active: number;
    paused: number;
  };
  recentTransactions: Transaction[];
  usageChart: {
    date: string;
    tokens: number;
    cost: number;
  }[];
}

// ============================================
// PRICING CONFIGURATION
// ============================================

export interface ModelPricing {
  model: AIModel;
  input: number;  // por 1K tokens
  output: number; // por 1K tokens
  reasoning?: number; // por 1K tokens (solo modelos reasoning)
}

export const MODEL_PRICING: Record<AIModel, ModelPricing> = {
  [AIModel.GPT5]: {
    model: AIModel.GPT5,
    input: 0.03,
    output: 0.06,
    reasoning: 0.12,
  },
  [AIModel.GPT5_MINI]: {
    model: AIModel.GPT5_MINI,
    input: 0.01,
    output: 0.02,
    reasoning: 0.04,
  },
  [AIModel.GPT5_NANO]: {
    model: AIModel.GPT5_NANO,
    input: 0.005,
    output: 0.01,
    reasoning: 0.02,
  },
  [AIModel.O3]: {
    model: AIModel.O3,
    input: 0.015,
    output: 0.03,
    reasoning: 0.06,
  },
  [AIModel.O3_MINI]: {
    model: AIModel.O3_MINI,
    input: 0.008,
    output: 0.016,
    reasoning: 0.032,
  },
  [AIModel.O4_MINI]: {
    model: AIModel.O4_MINI,
    input: 0.01,
    output: 0.02,
    reasoning: 0.04,
  },
  [AIModel.GPT_REALTIME_MINI]: {
    model: AIModel.GPT_REALTIME_MINI,
    input: 0.032,  // Audio input
    output: 0.032, // Audio output
  },
  [AIModel.CLAUDE_SONNET_4_5]: {
    model: AIModel.CLAUDE_SONNET_4_5,
    input: 0.003,
    output: 0.015,
  },
  [AIModel.CLAUDE_OPUS_4]: {
    model: AIModel.CLAUDE_OPUS_4,
    input: 0.015,
    output: 0.075,
  },
  [AIModel.CLAUDE_HAIKU_4]: {
    model: AIModel.CLAUDE_HAIKU_4,
    input: 0.0008,
    output: 0.004,
  },
  [AIModel.GPT4O]: {
    model: AIModel.GPT4O,
    input: 0.005,
    output: 0.015,
  },
  [AIModel.GPT4_TURBO]: {
    model: AIModel.GPT4_TURBO,
    input: 0.01,
    output: 0.03,
  },
  [AIModel.O1]: {
    model: AIModel.O1,
    input: 0.015,
    output: 0.03,
    reasoning: 0.06,
  },
  [AIModel.O1_MINI]: {
    model: AIModel.O1_MINI,
    input: 0.008,
    output: 0.016,
    reasoning: 0.032,
  },
  [AIModel.O3_PRO]: {
    model: AIModel.O3_PRO,
    input: 0.02,
    output: 0.04,
    reasoning: 0.08,
  },
};

// ============================================
// PLAN CONFIGURATION
// ============================================

export interface PlanConfig {
  plan: BillingPlan;
  name: string;
  price: number;
  tokensIncluded: number;
  maxAgents: number;
  features: string[];
}

export const PLAN_CONFIGS: Record<BillingPlan, PlanConfig> = {
  [BillingPlan.FREE]: {
    plan: BillingPlan.FREE,
    name: 'Free',
    price: 0,
    tokensIncluded: 1000,
    maxAgents: 1,
    features: ['1 Agent', '1K tokens/mes', 'Soporte por email'],
  },
  [BillingPlan.STARTER]: {
    plan: BillingPlan.STARTER,
    name: 'Starter',
    price: 29,
    tokensIncluded: 100000,
    maxAgents: 5,
    features: ['5 Agentes', '100K tokens/mes', 'Soporte prioritario', 'Analytics básico'],
  },
  [BillingPlan.PROFESSIONAL]: {
    plan: BillingPlan.PROFESSIONAL,
    name: 'Professional',
    price: 99,
    tokensIncluded: 500000,
    maxAgents: 20,
    features: ['20 Agentes', '500K tokens/mes', 'Soporte 24/7', 'Analytics avanzado', 'API access'],
  },
  [BillingPlan.BUSINESS]: {
    plan: BillingPlan.BUSINESS,
    name: 'Business',
    price: 299,
    tokensIncluded: 2000000,
    maxAgents: 100,
    features: ['100 Agentes', '2M tokens/mes', 'Soporte dedicado', 'Analytics custom', 'SLA 99.9%'],
  },
  [BillingPlan.ENTERPRISE]: {
    plan: BillingPlan.ENTERPRISE,
    name: 'Enterprise',
    price: 0, // Custom pricing
    tokensIncluded: -1, // Unlimited
    maxAgents: -1, // Unlimited
    features: ['Agentes ilimitados', 'Tokens ilimitados', 'Soporte enterprise', 'On-premise option', 'Custom SLA'],
  },
};
