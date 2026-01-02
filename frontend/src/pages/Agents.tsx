import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Bot,
  Code2,
  Shield,
  FileText,
  Rocket,
  Search,
  TrendingUp,
  Cpu,
  Users,
  Zap,
  Clock,
  CheckCircle2,
  Settings,
  Play,
  BarChart3,
} from 'lucide-react'
import Card, { CardHeader, CardTitle, CardContent } from '../components/ui/Card'
import Button from '../components/ui/Button'
import Badge, { StatusBadge } from '../components/ui/Badge'

const agents = [
  {
    id: 'code_analyzer',
    name: 'Code Analyzer',
    role: 'Code review & quality analysis',
    icon: Code2,
    color: 'from-blue-500 to-cyan-500',
    status: 'active' as const,
    description:
      'Expert code reviewer specializing in best practices, refactoring suggestions, and identifying code smells.',
    specializations: ['Python', 'JavaScript', 'TypeScript', 'Code Quality', 'Refactoring'],
    tools: ['filesystem_read_file', 'codebasebuddy_search_code', 'memory_store_conversation'],
    model: 'openai/gpt-oss-120b',
    stats: {
      totalAnalyses: 342,
      avgResponseTime: 3.2,
      successRate: 98.5,
    },
  },
  {
    id: 'security_auditor',
    name: 'Security Auditor',
    role: 'Vulnerability assessment',
    icon: Shield,
    color: 'from-red-500 to-orange-500',
    status: 'active' as const,
    description:
      'Security specialist following OWASP Top 10 guidelines. Identifies SQL injection, XSS, authentication issues, and more.',
    specializations: ['OWASP Top 10', 'CVE Detection', 'SQL Injection', 'XSS', 'Authentication'],
    tools: ['filesystem_read_file', 'codebasebuddy_semantic_search', 'github_search_code'],
    model: 'openai/gpt-oss-120b',
    stats: {
      totalAnalyses: 156,
      avgResponseTime: 25.4,
      successRate: 99.1,
    },
  },
  {
    id: 'documentation_agent',
    name: 'Documentation Agent',
    role: 'Doc generation & updates',
    icon: FileText,
    color: 'from-green-500 to-emerald-500',
    status: 'active' as const,
    description:
      'Creates and maintains README files, API documentation, inline comments, and technical guides.',
    specializations: ['README', 'API Docs', 'Inline Comments', 'Technical Writing'],
    tools: ['filesystem_read_file', 'filesystem_write_file', 'codebasebuddy_find_definition'],
    model: 'openai/gpt-oss-120b',
    stats: {
      totalAnalyses: 89,
      avgResponseTime: 12.1,
      successRate: 97.8,
    },
  },
  {
    id: 'deployment_agent',
    name: 'Deployment Agent',
    role: 'CI/CD automation',
    icon: Rocket,
    color: 'from-purple-500 to-pink-500',
    status: 'idle' as const,
    description:
      'Plans deployment strategies, generates Docker configurations, Kubernetes manifests, and CI/CD pipelines.',
    specializations: ['Docker', 'Kubernetes', 'CI/CD', 'Infrastructure', 'DevOps'],
    tools: ['filesystem_read_file', 'filesystem_write_file', 'github_create_pr'],
    model: 'openai/gpt-oss-120b',
    stats: {
      totalAnalyses: 45,
      avgResponseTime: 18.7,
      successRate: 96.2,
    },
  },
  {
    id: 'research_agent',
    name: 'Research Agent',
    role: 'Technology research',
    icon: Search,
    color: 'from-amber-500 to-yellow-500',
    status: 'active' as const,
    description:
      'Researches best practices, framework recommendations, and latest technology trends for your project.',
    specializations: ['Best Practices', 'Framework Comparison', 'Tech Trends', 'Architecture'],
    tools: ['codebasebuddy_search_code', 'memory_search_memory'],
    model: 'openai/gpt-oss-120b',
    stats: {
      totalAnalyses: 67,
      avgResponseTime: 22.3,
      successRate: 95.8,
    },
  },
  {
    id: 'project_manager',
    name: 'Project Manager',
    role: 'Orchestration & planning',
    icon: Users,
    color: 'from-indigo-500 to-blue-500',
    status: 'active' as const,
    description:
      'Coordinates tasks between agents, manages dependencies, and creates project plans.',
    specializations: ['Task Breakdown', 'Dependency Management', 'Sprint Planning', 'Coordination'],
    tools: ['memory_store_conversation', 'memory_get_context'],
    model: 'openai/gpt-oss-120b',
    stats: {
      totalAnalyses: 234,
      avgResponseTime: 5.1,
      successRate: 99.5,
    },
  },
  {
    id: 'executor',
    name: 'Executor',
    role: 'Code execution & testing',
    icon: Cpu,
    color: 'from-cyan-500 to-teal-500',
    status: 'active' as const,
    description:
      'Executes code, runs tests, and performs file operations. The workhorse of the agent team.',
    specializations: ['Code Execution', 'Testing', 'File Operations', 'Tool Invocation'],
    tools: ['filesystem_read_file', 'filesystem_write_file', 'filesystem_list_directory'],
    model: 'UserProxyAgent',
    stats: {
      totalAnalyses: 512,
      avgResponseTime: 1.2,
      successRate: 99.9,
    },
  },
  {
    id: 'user_proxy',
    name: 'User Proxy',
    role: 'Human-in-the-loop',
    icon: Bot,
    color: 'from-gray-500 to-slate-500',
    status: 'idle' as const,
    description:
      'Handles interactive reviews, approval workflows, and human feedback integration.',
    specializations: ['Interactive Review', 'Approval Workflows', 'Human Feedback'],
    tools: [],
    model: 'UserProxyAgent',
    stats: {
      totalAnalyses: 78,
      avgResponseTime: 0.5,
      successRate: 100,
    },
  },
]

export default function Agents() {
  const [selectedAgent, setSelectedAgent] = useState<typeof agents[0] | null>(null)

  const activeCount = agents.filter((a) => a.status === 'active').length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-gray-100)]">AI Agents</h1>
          <p className="text-[var(--color-gray-400)]">
            {activeCount} of {agents.length} agents active
          </p>
        </div>
        <Button variant="secondary" leftIcon={<BarChart3 className="h-4 w-4" />}>
          Performance Dashboard
        </Button>
      </div>

      {/* Agent Grid */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        {agents.map((agent, index) => {
          const Icon = agent.icon
          return (
            <motion.div
              key={agent.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
            >
              <Card
                hover
                onClick={() => setSelectedAgent(agent)}
                className="relative overflow-hidden"
              >
                {/* Status Indicator */}
                <div className="absolute right-4 top-4">
                  <div
                    className={`h-2.5 w-2.5 rounded-full ${
                      agent.status === 'active'
                        ? 'bg-[var(--color-success-400)] shadow-lg shadow-[var(--color-success-400)]/50'
                        : 'bg-[var(--color-gray-500)]'
                    }`}
                  />
                </div>

                {/* Icon */}
                <div
                  className={`mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-gradient-to-br ${agent.color} shadow-lg`}
                >
                  <Icon className="h-7 w-7 text-white" />
                </div>

                {/* Content */}
                <h3 className="font-semibold text-[var(--color-gray-100)]">{agent.name}</h3>
                <p className="mt-1 text-sm text-[var(--color-gray-400)]">{agent.role}</p>

                {/* Stats */}
                <div className="mt-4 flex items-center gap-4 text-xs text-[var(--color-gray-500)]">
                  <span className="flex items-center gap-1">
                    <Zap className="h-3 w-3" />
                    {agent.stats.totalAnalyses}
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {agent.stats.avgResponseTime}s
                  </span>
                  <span className="flex items-center gap-1">
                    <CheckCircle2 className="h-3 w-3" />
                    {agent.stats.successRate}%
                  </span>
                </div>
              </Card>
            </motion.div>
          )
        })}
      </div>

      {/* Agent Detail Modal */}
      {selectedAgent && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
          onClick={() => setSelectedAgent(null)}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="w-full max-w-2xl rounded-2xl border border-[var(--glass-border)] bg-[var(--bg-secondary)] p-6 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-start gap-4">
              <div
                className={`flex h-16 w-16 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br ${selectedAgent.color} shadow-lg`}
              >
                <selectedAgent.icon className="h-8 w-8 text-white" />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-3">
                  <h2 className="text-xl font-bold text-[var(--color-gray-100)]">
                    {selectedAgent.name}
                  </h2>
                  <StatusBadge status={selectedAgent.status} />
                </div>
                <p className="text-[var(--color-gray-400)]">{selectedAgent.role}</p>
              </div>
              <button
                onClick={() => setSelectedAgent(null)}
                className="text-[var(--color-gray-500)] hover:text-[var(--color-gray-300)]"
              >
                ✕
              </button>
            </div>

            {/* Description */}
            <p className="mt-4 text-sm text-[var(--color-gray-400)]">{selectedAgent.description}</p>

            {/* Specializations */}
            <div className="mt-6">
              <h4 className="mb-2 text-sm font-medium text-[var(--color-gray-300)]">
                Specializations
              </h4>
              <div className="flex flex-wrap gap-2">
                {selectedAgent.specializations.map((spec) => (
                  <Badge key={spec} variant="primary" size="sm">
                    {spec}
                  </Badge>
                ))}
              </div>
            </div>

            {/* Tools */}
            <div className="mt-4">
              <h4 className="mb-2 text-sm font-medium text-[var(--color-gray-300)]">
                Available Tools
              </h4>
              <div className="flex flex-wrap gap-2">
                {selectedAgent.tools.length > 0 ? (
                  selectedAgent.tools.map((tool) => (
                    <Badge key={tool} variant="default" size="sm">
                      {tool}
                    </Badge>
                  ))
                ) : (
                  <span className="text-sm text-[var(--color-gray-500)]">No tools assigned</span>
                )}
              </div>
            </div>

            {/* Stats */}
            <div className="mt-6 grid grid-cols-3 gap-4">
              <div className="rounded-xl bg-[var(--bg-tertiary)] p-4 text-center">
                <p className="text-2xl font-bold text-[var(--color-gray-100)]">
                  {selectedAgent.stats.totalAnalyses}
                </p>
                <p className="text-xs text-[var(--color-gray-500)]">Total Analyses</p>
              </div>
              <div className="rounded-xl bg-[var(--bg-tertiary)] p-4 text-center">
                <p className="text-2xl font-bold text-[var(--color-gray-100)]">
                  {selectedAgent.stats.avgResponseTime}s
                </p>
                <p className="text-xs text-[var(--color-gray-500)]">Avg Response</p>
              </div>
              <div className="rounded-xl bg-[var(--bg-tertiary)] p-4 text-center">
                <p className="text-2xl font-bold text-[var(--color-success-400)]">
                  {selectedAgent.stats.successRate}%
                </p>
                <p className="text-xs text-[var(--color-gray-500)]">Success Rate</p>
              </div>
            </div>

            {/* Model Info */}
            <div className="mt-4 flex items-center gap-2 text-sm text-[var(--color-gray-500)]">
              <Cpu className="h-4 w-4" />
              <span>Powered by: {selectedAgent.model}</span>
            </div>

            {/* Actions */}
            <div className="mt-6 flex gap-3">
              <Button variant="primary" leftIcon={<Play className="h-4 w-4" />}>
                Test Agent
              </Button>
              <Button variant="secondary" leftIcon={<Settings className="h-4 w-4" />}>
                Configure
              </Button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </div>
  )
}
