import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Analysis, Agent, MCPServer, Settings, User } from '../types'

// App Store - Global UI State
interface AppState {
  sidebarOpen: boolean
  sidebarCollapsed: boolean
  theme: 'dark' | 'light' | 'auto'
  notifications: Notification[]
  toggleSidebar: () => void
  toggleSidebarCollapse: () => void
  setTheme: (theme: 'dark' | 'light' | 'auto') => void
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp'>) => void
  removeNotification: (id: string) => void
  clearNotifications: () => void
}

interface Notification {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message: string
  timestamp: string
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      sidebarOpen: true,
      sidebarCollapsed: false,
      theme: 'dark',
      notifications: [],
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      toggleSidebarCollapse: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      setTheme: (theme) => set({ theme }),
      addNotification: (notification) =>
        set((state) => ({
          notifications: [
            {
              ...notification,
              id: crypto.randomUUID(),
              timestamp: new Date().toISOString(),
            },
            ...state.notifications,
          ].slice(0, 50), // Keep only last 50 notifications
        })),
      removeNotification: (id) =>
        set((state) => ({
          notifications: state.notifications.filter((n) => n.id !== id),
        })),
      clearNotifications: () => set({ notifications: [] }),
    }),
    {
      name: 'app-storage',
      partialize: (state) => ({ theme: state.theme, sidebarCollapsed: state.sidebarCollapsed }),
    }
  )
)

// Analysis Store - Current Analysis State
interface AnalysisState {
  currentAnalysis: Analysis | null
  analysisProgress: number
  activeAgents: string[]
  recentAnalyses: Analysis[]
  isRunning: boolean
  setCurrentAnalysis: (analysis: Analysis | null) => void
  setProgress: (progress: number) => void
  setActiveAgents: (agents: string[]) => void
  addRecentAnalysis: (analysis: Analysis) => void
  setIsRunning: (running: boolean) => void
  reset: () => void
}

export const useAnalysisStore = create<AnalysisState>((set) => ({
  currentAnalysis: null,
  analysisProgress: 0,
  activeAgents: [],
  recentAnalyses: [],
  isRunning: false,
  setCurrentAnalysis: (analysis) => set({ currentAnalysis: analysis }),
  setProgress: (progress) => set({ analysisProgress: progress }),
  setActiveAgents: (agents) => set({ activeAgents: agents }),
  addRecentAnalysis: (analysis) =>
    set((state) => ({
      recentAnalyses: [analysis, ...state.recentAnalyses].slice(0, 20),
    })),
  setIsRunning: (running) => set({ isRunning: running }),
  reset: () =>
    set({
      currentAnalysis: null,
      analysisProgress: 0,
      activeAgents: [],
      isRunning: false,
    }),
}))

// Agents Store
interface AgentsState {
  agents: Agent[]
  selectedAgent: Agent | null
  setAgents: (agents: Agent[]) => void
  setSelectedAgent: (agent: Agent | null) => void
  updateAgentStatus: (agentId: string, status: Agent['status']) => void
}

export const useAgentsStore = create<AgentsState>((set) => ({
  agents: [],
  selectedAgent: null,
  setAgents: (agents) => set({ agents }),
  setSelectedAgent: (agent) => set({ selectedAgent: agent }),
  updateAgentStatus: (agentId, status) =>
    set((state) => ({
      agents: state.agents.map((a) => (a.id === agentId ? { ...a, status } : a)),
    })),
}))

// Servers Store
interface ServersState {
  servers: MCPServer[]
  setServers: (servers: MCPServer[]) => void
  updateServerStatus: (serverId: string, status: MCPServer['status']) => void
}

export const useServersStore = create<ServersState>((set) => ({
  servers: [],
  setServers: (servers) => set({ servers }),
  updateServerStatus: (serverId, status) =>
    set((state) => ({
      servers: state.servers.map((s) => (s.id === serverId ? { ...s, status } : s)),
    })),
}))

// User Store
interface UserState {
  user: User | null
  isAuthenticated: boolean
  setUser: (user: User | null) => void
  logout: () => void
}

export const useUserStore = create<UserState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      setUser: (user) => set({ user, isAuthenticated: !!user }),
      logout: () => {
        localStorage.removeItem('auth_token')
        set({ user: null, isAuthenticated: false })
      },
    }),
    {
      name: 'user-storage',
    }
  )
)
