import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  Server,
  RefreshCw,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Github,
  FolderOpen,
  Brain,
  Code2,
} from 'lucide-react'
import Card, { CardHeader, CardTitle, CardContent } from '../ui/Card'
import Button from '../ui/Button'
import { StatusBadge } from '../ui/Badge'

// Mock data - replace with API call
const mockServers = [
  {
    id: 'github',
    name: 'GitHub Server',
    port: 3000,
    status: 'running' as const,
    icon: Github,
    description: 'GitHub API operations',
  },
  {
    id: 'filesystem',
    name: 'Filesystem Server',
    port: 3001,
    status: 'running' as const,
    icon: FolderOpen,
    description: 'Local file access',
  },
  {
    id: 'memory',
    name: 'Memory Server',
    port: 3002,
    status: 'running' as const,
    icon: Brain,
    description: 'Semantic memory',
  },
  {
    id: 'codebasebuddy',
    name: 'CodeBaseBuddy',
    port: 3004,
    status: 'running' as const,
    icon: Code2,
    description: 'Code search',
  },
]

const mockApiProviders = [
  { id: 'openrouter', name: 'OpenRouter', status: 'connected' as const },
  { id: 'groq', name: 'Groq', status: 'connected' as const },
  { id: 'gemini', name: 'Gemini', status: 'disconnected' as const },
]

export default function SystemHealth() {
  const [servers, setServers] = useState(mockServers)
  const [isRefreshing, setIsRefreshing] = useState(false)

  const handleRefresh = async () => {
    setIsRefreshing(true)
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000))
    setIsRefreshing(false)
  }

  const allServersHealthy = servers.every((s) => s.status === 'running')
  const runningCount = servers.filter((s) => s.status === 'running').length

  return (
    <Card className="h-full">
      <CardHeader>
        <div>
          <CardTitle>System Health</CardTitle>
          <p className="text-sm text-[var(--color-gray-400)]">
            {runningCount}/{servers.length} services running
          </p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleRefresh}
          isLoading={isRefreshing}
          leftIcon={<RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />}
        >
          Refresh
        </Button>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Overall Status */}
        <div
          className={`flex items-center gap-3 rounded-xl p-3 ${
            allServersHealthy
              ? 'bg-[var(--color-success-500)]/10'
              : 'bg-[var(--color-warning-500)]/10'
          }`}
        >
          {allServersHealthy ? (
            <CheckCircle2 className="h-5 w-5 text-[var(--color-success-400)]" />
          ) : (
            <AlertCircle className="h-5 w-5 text-[var(--color-warning-400)]" />
          )}
          <span
            className={`text-sm font-medium ${
              allServersHealthy
                ? 'text-[var(--color-success-400)]'
                : 'text-[var(--color-warning-400)]'
            }`}
          >
            {allServersHealthy ? 'All systems operational' : 'Some services need attention'}
          </span>
        </div>

        {/* MCP Servers */}
        <div>
          <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-[var(--color-gray-500)]">
            MCP Servers
          </h4>
          <div className="space-y-2">
            {servers.map((server, index) => {
              const Icon = server.icon
              return (
                <motion.div
                  key={server.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className="flex items-center justify-between rounded-lg bg-[var(--bg-tertiary)] p-3"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--bg-elevated)]">
                      <Icon className="h-4 w-4 text-[var(--color-gray-400)]" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-[var(--color-gray-200)]">
                        {server.name}
                      </p>
                      <p className="text-xs text-[var(--color-gray-500)]">Port {server.port}</p>
                    </div>
                  </div>
                  <div
                    className={`h-2.5 w-2.5 rounded-full ${
                      server.status === 'running'
                        ? 'bg-[var(--color-success-400)] shadow-lg shadow-[var(--color-success-400)]/50'
                        : 'bg-[var(--color-danger-400)]'
                    }`}
                  />
                </motion.div>
              )
            })}
          </div>
        </div>

        {/* API Providers */}
        <div>
          <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-[var(--color-gray-500)]">
            API Providers
          </h4>
          <div className="flex flex-wrap gap-2">
            {mockApiProviders.map((provider) => (
              <div
                key={provider.id}
                className={`flex items-center gap-2 rounded-lg px-3 py-2 ${
                  provider.status === 'connected'
                    ? 'bg-[var(--color-success-500)]/10'
                    : 'bg-[var(--color-gray-700)]/50'
                }`}
              >
                <div
                  className={`h-1.5 w-1.5 rounded-full ${
                    provider.status === 'connected'
                      ? 'bg-[var(--color-success-400)]'
                      : 'bg-[var(--color-gray-500)]'
                  }`}
                />
                <span
                  className={`text-xs font-medium ${
                    provider.status === 'connected'
                      ? 'text-[var(--color-success-400)]'
                      : 'text-[var(--color-gray-500)]'
                  }`}
                >
                  {provider.name}
                </span>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
