// Workflow Types
export interface Workflow {
  id: string
  name: string
  description: string
  type: 'two_agent' | 'groupchat' | 'nested_chat'
  agentCount: number
  estimatedTime: string
  icon: string
  category: 'quick' | 'comprehensive'
}

// Analysis Types
export interface Analysis {
  id: string
  workflowId: string
  workflowName: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  createdAt: string
  completedAt?: string
  duration?: number
  files: string[]
  focusAreas: string[]
  results?: AnalysisResults
}

export interface AnalysisResults {
  qualityScore: number
  securityScore: number
  summary: string
  recommendations: string[]
  issues: Issue[]
  agentContributions: AgentContribution[]
  metrics: AnalysisMetrics
}

export interface Issue {
  id: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  category: string
  title: string
  description: string
  file: string
  line: number
  code?: string
  suggestion?: string
  owaspCategory?: string
  resolved: boolean
}

export interface AgentContribution {
  agentId: string
  agentName: string
  agentIcon: string
  timestamp: string
  duration: number
  findings: number
  message: string
}

export interface AnalysisMetrics {
  linesAnalyzed: number
  filesReviewed: number
  issuesFound: number
  criticalIssues: number
  highIssues: number
  mediumIssues: number
  lowIssues: number
  timeSaved: string
}

// Agent Types
export interface Agent {
  id: string
  name: string
  role: string
  description: string
  specializations: string[]
  tools: string[]
  model: string
  status: 'active' | 'idle' | 'offline'
  stats: AgentStats
  icon: string
  color: string
}

export interface AgentStats {
  totalAnalyses: number
  avgResponseTime: number
  successRate: number
}

// MCP Server Types
export interface MCPServer {
  id: string
  name: string
  port: number
  status: 'running' | 'stopped' | 'error'
  lastHealthCheck: string
  description: string
}

// Settings Types
export interface Settings {
  theme: 'dark' | 'light' | 'auto'
  language: string
  timezone: string
  defaultWorkflow: string
  apiKeys: {
    openrouter?: string
    groq?: string
    gemini?: string
  }
  notifications: {
    emailOnComplete: boolean
    emailOnCritical: boolean
    inAppNotifications: boolean
  }
  security: {
    allowedPaths: string[]
    blockedPaths: string[]
    rateLimit: {
      requestsPerMinute: number
      requestsPerHour: number
    }
  }
}

// WebSocket Event Types
export interface WSEvent {
  type: 'agent_started' | 'agent_completed' | 'analysis_progress' | 'analysis_complete' | 'error'
  data: unknown
  timestamp: string
}

export interface AgentStartedEvent {
  type: 'agent_started'
  agent: string
  agentIcon: string
  timestamp: string
}

export interface AgentCompletedEvent {
  type: 'agent_completed'
  agent: string
  findings: number
  duration: number
}

export interface AnalysisProgressEvent {
  type: 'analysis_progress'
  percentage: number
  currentStep: string
  activeAgents: string[]
}

export interface AnalysisCompleteEvent {
  type: 'analysis_complete'
  analysisId: string
  resultsUrl: string
}

// API Response Types
export interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
  message?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
  hasMore: boolean
}

// User Types
export interface User {
  id: string
  email: string
  name: string
  avatar?: string
  role: 'admin' | 'user'
  apiUsage: {
    requestsToday: number
    requestsThisMonth: number
    costThisMonth: number
  }
}
