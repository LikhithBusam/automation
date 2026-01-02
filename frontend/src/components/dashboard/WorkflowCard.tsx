import { motion } from 'framer-motion'
import { Clock, Users, ArrowRight } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import Badge from '../ui/Badge'

interface WorkflowCardProps {
  workflow: {
    id: string
    name: string
    description: string
    icon: LucideIcon
    estimatedTime: string
    agentCount: number
    category: 'quick' | 'comprehensive'
    color: string
  }
  delay?: number
  onClick: () => void
}

export default function WorkflowCard({ workflow, delay = 0, onClick }: WorkflowCardProps) {
  const Icon = workflow.icon

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      whileHover={{ y: -4, scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
      className="group cursor-pointer rounded-2xl border border-[var(--glass-border)] bg-[var(--bg-secondary)] p-5 transition-all duration-300 hover:border-[var(--color-primary-500)]/50 hover:shadow-lg hover:shadow-[var(--color-primary-500)]/10"
    >
      {/* Icon */}
      <div
        className={`mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br ${workflow.color} shadow-lg`}
      >
        <Icon className="h-6 w-6 text-white" />
      </div>

      {/* Content */}
      <h3 className="mb-1 text-lg font-semibold text-[var(--color-gray-100)] group-hover:text-white">
        {workflow.name}
      </h3>
      <p className="mb-4 text-sm text-[var(--color-gray-400)]">{workflow.description}</p>

      {/* Meta Info */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs text-[var(--color-gray-500)]">
            <Clock className="h-3.5 w-3.5" />
            {workflow.estimatedTime}
          </div>
          <div className="flex items-center gap-1.5 text-xs text-[var(--color-gray-500)]">
            <Users className="h-3.5 w-3.5" />
            {workflow.agentCount} agents
          </div>
        </div>
        <ArrowRight className="h-4 w-4 text-[var(--color-gray-500)] transition-transform group-hover:translate-x-1 group-hover:text-[var(--color-primary-400)]" />
      </div>

      {/* Category Badge */}
      {workflow.category === 'quick' && (
        <div className="absolute right-4 top-4">
          <Badge variant="success" size="sm">
            Fast
          </Badge>
        </div>
      )}
    </motion.div>
  )
}
