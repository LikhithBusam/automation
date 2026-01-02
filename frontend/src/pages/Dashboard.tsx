import { motion } from 'framer-motion'
import {
  Code2,
  Shield,
  FileText,
  Rocket,
  Search,
  Zap,
  Clock,
  Users,
  TrendingUp,
  Activity,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import Card, { CardHeader, CardTitle, CardContent } from '../components/ui/Card'
import Button from '../components/ui/Button'
import Badge, { StatusBadge } from '../components/ui/Badge'
import WorkflowCard from '../components/dashboard/WorkflowCard'
import StatsCard from '../components/dashboard/StatsCard'
import RecentActivity from '../components/dashboard/RecentActivity'
import SystemHealth from '../components/dashboard/SystemHealth'

const workflows = [
  {
    id: 'quick_code_review',
    name: 'Quick Code Review',
    description: 'Fast code review for small changes',
    icon: Code2,
    estimatedTime: '3-5s',
    agentCount: 2,
    category: 'quick' as const,
    color: 'from-blue-500 to-cyan-500',
  },
  {
    id: 'security_audit',
    name: 'Security Audit',
    description: 'Deep vulnerability assessment (OWASP)',
    icon: Shield,
    estimatedTime: '30-90s',
    agentCount: 3,
    category: 'comprehensive' as const,
    color: 'from-red-500 to-orange-500',
  },
  {
    id: 'documentation_generation',
    name: 'Generate Docs',
    description: 'Generate/update project documentation',
    icon: FileText,
    estimatedTime: '10-30s',
    agentCount: 2,
    category: 'quick' as const,
    color: 'from-green-500 to-emerald-500',
  },
  {
    id: 'deployment',
    name: 'Deployment Planning',
    description: 'Deployment planning and automation',
    icon: Rocket,
    estimatedTime: '15-45s',
    agentCount: 2,
    category: 'comprehensive' as const,
    color: 'from-purple-500 to-pink-500',
  },
  {
    id: 'code_analysis',
    name: 'Code Analysis',
    description: 'Comprehensive analysis with security',
    icon: Search,
    estimatedTime: '20-60s',
    agentCount: 3,
    category: 'comprehensive' as const,
    color: 'from-indigo-500 to-blue-500',
  },
  {
    id: 'research',
    name: 'Tech Research',
    description: 'Technology research and recommendations',
    icon: TrendingUp,
    estimatedTime: '20-60s',
    agentCount: 2,
    category: 'comprehensive' as const,
    color: 'from-amber-500 to-yellow-500',
  },
]

const stats = [
  {
    title: 'Total Analyses',
    value: '1,247',
    change: '+12%',
    changeType: 'positive' as const,
    icon: Activity,
  },
  {
    title: 'Avg Response Time',
    value: '4.2s',
    change: '-0.8s',
    changeType: 'positive' as const,
    icon: Clock,
  },
  {
    title: 'Issues Found',
    value: '89',
    change: '+23',
    changeType: 'neutral' as const,
    icon: AlertTriangle,
  },
  {
    title: 'Issues Resolved',
    value: '76',
    change: '+18',
    changeType: 'positive' as const,
    icon: CheckCircle2,
  },
]

export default function Dashboard() {
  const navigate = useNavigate()

  return (
    <div className="space-y-8">
      {/* Welcome Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-3xl font-bold text-[var(--color-gray-100)]">
            Welcome back! 👋
          </h1>
          <p className="mt-2 text-[var(--color-gray-400)]">
            Your development command center is ready. What would you like to analyze?
          </p>
        </div>
        <Button
          size="lg"
          leftIcon={<Zap className="h-5 w-5" />}
          onClick={() => navigate('/analysis/new')}
        >
          New Analysis
        </Button>
      </motion.div>

      {/* Stats Grid */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4"
      >
        {stats.map((stat, index) => (
          <StatsCard key={stat.title} {...stat} delay={index * 0.05} />
        ))}
      </motion.div>

      {/* Quick Workflows Section */}
      <motion.section
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-[var(--color-gray-100)]">
              Quick Workflows
            </h2>
            <p className="text-sm text-[var(--color-gray-400)]">
              Start an analysis in seconds
            </p>
          </div>
          <Badge variant="primary" size="sm">
            <Zap className="h-3 w-3" />
            Lightning Fast
          </Badge>
        </div>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {workflows.map((workflow, index) => (
            <WorkflowCard
              key={workflow.id}
              workflow={workflow}
              delay={index * 0.05}
              onClick={() => navigate(`/analysis/new?workflow=${workflow.id}`)}
            />
          ))}
        </div>
      </motion.section>

      {/* Bottom Grid: Recent Activity & System Health */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="lg:col-span-2"
        >
          <RecentActivity />
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <SystemHealth />
        </motion.div>
      </div>
    </div>
  )
}
