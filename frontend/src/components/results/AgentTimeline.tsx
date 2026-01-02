import { motion } from 'framer-motion'
import { useState } from 'react'
import { formatDuration } from '../../lib/utils'

interface AgentContribution {
  agentId: string
  agentName: string
  agentIcon?: string
  timestamp: string
  duration: number
  findings: number
  message: string
}

interface AgentTimelineProps {
  contributions: AgentContribution[]
}

// Default icons for different agent types
const getAgentIcon = (agentId: string, agentIcon?: string): string => {
  if (agentIcon) return agentIcon
  
  const id = agentId.toLowerCase()
  if (id.includes('code') || id.includes('analyzer')) return '🔍'
  if (id.includes('security')) return '🛡️'
  if (id.includes('doc')) return '📝'
  if (id.includes('deploy')) return '🚀'
  if (id.includes('research')) return '🔬'
  if (id.includes('manager') || id.includes('project')) return '📋'
  if (id.includes('executor') || id.includes('proxy')) return '⚡'
  return '🤖'
}

// Component for expandable message
function ExpandableMessage({ message }: { message: string }) {
  const [expanded, setExpanded] = useState(false)
  const isLong = message.length > 300
  
  if (!message || message.trim() === '') {
    return <p className="text-sm text-[var(--color-gray-500)] italic">No content</p>
  }
  
  return (
    <div>
      <div className={`text-sm text-[var(--color-gray-400)] whitespace-pre-wrap ${!expanded && isLong ? 'line-clamp-4' : ''}`}>
        {message}
      </div>
      {isLong && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-2 text-xs text-[var(--color-primary-400)] hover:text-[var(--color-primary-300)] transition-colors"
        >
          {expanded ? '▲ Show less' : '▼ Show full content'}
        </button>
      )}
    </div>
  )
}

export default function AgentTimeline({ contributions }: AgentTimelineProps) {
  return (
    <div className="rounded-2xl border border-[var(--glass-border)] bg-[var(--bg-secondary)] p-6">
      <h3 className="mb-4 font-semibold text-[var(--color-gray-100)]">
        🤖 Agent Collaboration Timeline
      </h3>
      <div className="relative">
        {/* Timeline Line */}
        <div className="absolute left-6 top-0 h-full w-0.5 bg-gradient-to-b from-[var(--color-primary-500)] via-[var(--color-accent-500)] to-[var(--color-success-500)]" />

        {/* Contributions */}
        <div className="space-y-6">
          {contributions.map((contribution, index) => (
            <motion.div
              key={contribution.agentId}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
              className="relative flex gap-4 pl-14"
            >
              {/* Agent Avatar */}
              <div className="absolute left-0 flex h-12 w-12 items-center justify-center rounded-full border-4 border-[var(--bg-secondary)] bg-[var(--bg-tertiary)] text-xl shadow-lg">
                {getAgentIcon(contribution.agentId, contribution.agentIcon)}
              </div>

              {/* Content */}
              <div className="flex-1 rounded-xl bg-[var(--bg-tertiary)] p-4">
                <div className="mb-2 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-[var(--color-gray-100)]">
                      {contribution.agentName}
                    </span>
                    {contribution.findings > 0 && (
                      <span className="rounded-full bg-[var(--color-primary-500)]/20 px-2 py-0.5 text-xs text-[var(--color-primary-400)]">
                        {contribution.findings} findings
                      </span>
                    )}
                  </div>
                  <span className="text-xs text-[var(--color-gray-500)]">
                    {formatDuration(contribution.duration)}
                  </span>
                </div>
                <ExpandableMessage message={contribution.message} />
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  )
}
