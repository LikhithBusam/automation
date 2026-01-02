import { useState } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import {
  Code2,
  Shield,
  FileText,
  Rocket,
  Clock,
  ChevronRight,
  Filter,
} from 'lucide-react'
import Card, { CardHeader, CardTitle, CardContent } from '../ui/Card'
import Badge, { StatusBadge, SeverityBadge } from '../ui/Badge'
import Button from '../ui/Button'
import { formatDate, formatDuration } from '../../lib/utils'

// Mock data - replace with API call
const recentAnalyses = [
  {
    id: '1',
    workflowName: 'Quick Code Review',
    workflowIcon: Code2,
    status: 'completed' as const,
    createdAt: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
    duration: 3.2,
    issuesCount: { critical: 0, high: 1, medium: 3, low: 2 },
    qualityScore: 8.5,
    files: ['main.py', 'utils.py'],
  },
  {
    id: '2',
    workflowName: 'Security Audit',
    workflowIcon: Shield,
    status: 'completed' as const,
    createdAt: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
    duration: 45.8,
    issuesCount: { critical: 2, high: 5, medium: 8, low: 4 },
    qualityScore: 5.2,
    files: ['src/', 'api/'],
  },
  {
    id: '3',
    workflowName: 'Generate Docs',
    workflowIcon: FileText,
    status: 'completed' as const,
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
    duration: 12.4,
    issuesCount: { critical: 0, high: 0, medium: 0, low: 0 },
    qualityScore: 9.1,
    files: ['models/'],
  },
  {
    id: '4',
    workflowName: 'Deployment Planning',
    workflowIcon: Rocket,
    status: 'running' as const,
    createdAt: new Date(Date.now() - 1000 * 60 * 2).toISOString(),
    duration: 0,
    issuesCount: { critical: 0, high: 0, medium: 0, low: 0 },
    qualityScore: 0,
    files: ['docker/', 'k8s/'],
  },
]

const filterOptions = ['All', 'Code Reviews', 'Security', 'Documentation', 'Deployment']

export default function RecentActivity() {
  const navigate = useNavigate()
  const [activeFilter, setActiveFilter] = useState('All')

  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle>Recent Activity</CardTitle>
          <p className="text-sm text-[var(--color-gray-400)]">Your last 20 analyses</p>
        </div>
        <Button variant="ghost" size="sm" rightIcon={<ChevronRight className="h-4 w-4" />}>
          View All
        </Button>
      </CardHeader>

      {/* Filters */}
      <div className="mb-4 flex flex-wrap gap-2">
        {filterOptions.map((filter) => (
          <button
            key={filter}
            onClick={() => setActiveFilter(filter)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
              activeFilter === filter
                ? 'bg-[var(--color-primary-500)]/20 text-[var(--color-primary-400)]'
                : 'bg-[var(--bg-tertiary)] text-[var(--color-gray-400)] hover:text-[var(--color-gray-100)]'
            }`}
          >
            {filter}
          </button>
        ))}
      </div>

      <CardContent>
        <div className="space-y-3">
          {recentAnalyses.map((analysis, index) => {
            const Icon = analysis.workflowIcon
            const totalIssues =
              analysis.issuesCount.critical +
              analysis.issuesCount.high +
              analysis.issuesCount.medium +
              analysis.issuesCount.low

            return (
              <motion.div
                key={analysis.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                onClick={() => navigate(`/analysis/${analysis.id}`)}
                className="group flex cursor-pointer items-center gap-4 rounded-xl border border-transparent bg-[var(--bg-tertiary)] p-4 transition-all hover:border-[var(--color-primary-500)]/30 hover:bg-[var(--bg-elevated)]"
              >
                {/* Icon */}
                <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-[var(--bg-elevated)]">
                  <Icon className="h-5 w-5 text-[var(--color-primary-400)]" />
                </div>

                {/* Content */}
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <h4 className="font-medium text-[var(--color-gray-100)]">
                      {analysis.workflowName}
                    </h4>
                    <StatusBadge status={analysis.status} />
                  </div>
                  <p className="mt-0.5 truncate text-sm text-[var(--color-gray-500)]">
                    {analysis.files.join(', ')}
                  </p>
                </div>

                {/* Issues */}
                {analysis.status === 'completed' && totalIssues > 0 && (
                  <div className="hidden items-center gap-1.5 sm:flex">
                    {analysis.issuesCount.critical > 0 && (
                      <span className="rounded bg-[var(--color-danger-500)]/20 px-1.5 py-0.5 text-xs font-medium text-[var(--color-danger-400)]">
                        {analysis.issuesCount.critical} critical
                      </span>
                    )}
                    {analysis.issuesCount.high > 0 && (
                      <span className="rounded bg-[var(--color-warning-500)]/20 px-1.5 py-0.5 text-xs font-medium text-[var(--color-warning-400)]">
                        {analysis.issuesCount.high} high
                      </span>
                    )}
                  </div>
                )}

                {/* Score */}
                {analysis.status === 'completed' && analysis.qualityScore > 0 && (
                  <div className="hidden text-right lg:block">
                    <div
                      className={`text-lg font-bold ${
                        analysis.qualityScore >= 8
                          ? 'text-[var(--color-success-400)]'
                          : analysis.qualityScore >= 6
                          ? 'text-[var(--color-warning-400)]'
                          : 'text-[var(--color-danger-400)]'
                      }`}
                    >
                      {analysis.qualityScore.toFixed(1)}
                    </div>
                    <div className="text-xs text-[var(--color-gray-500)]">Score</div>
                  </div>
                )}

                {/* Meta */}
                <div className="flex flex-shrink-0 flex-col items-end gap-1">
                  <div className="flex items-center gap-1 text-xs text-[var(--color-gray-500)]">
                    <Clock className="h-3 w-3" />
                    {formatDate(analysis.createdAt)}
                  </div>
                  {analysis.duration > 0 && (
                    <div className="text-xs text-[var(--color-gray-600)]">
                      {formatDuration(analysis.duration)}
                    </div>
                  )}
                </div>

                {/* Arrow */}
                <ChevronRight className="h-4 w-4 flex-shrink-0 text-[var(--color-gray-600)] transition-transform group-hover:translate-x-1 group-hover:text-[var(--color-primary-400)]" />
              </motion.div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
