import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Search,
  Filter,
  Calendar,
  ChevronRight,
  Clock,
  Code2,
  Shield,
  FileText,
  Rocket,
  LayoutGrid,
  List,
  Trash2,
  Download,
} from 'lucide-react'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import Badge, { StatusBadge, SeverityBadge } from '../components/ui/Badge'
import { formatDate, formatDuration } from '../lib/utils'

// Mock data
const mockAnalyses = [
  {
    id: '1',
    workflowName: 'Quick Code Review',
    workflowIcon: Code2,
    status: 'completed' as const,
    createdAt: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
    duration: 3.2,
    qualityScore: 8.5,
    issuesCount: { critical: 0, high: 1, medium: 3, low: 2 },
    files: ['main.py', 'utils.py'],
  },
  {
    id: '2',
    workflowName: 'Security Audit',
    workflowIcon: Shield,
    status: 'completed' as const,
    createdAt: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
    duration: 45.8,
    qualityScore: 5.2,
    issuesCount: { critical: 2, high: 5, medium: 8, low: 4 },
    files: ['src/', 'api/'],
  },
  {
    id: '3',
    workflowName: 'Generate Docs',
    workflowIcon: FileText,
    status: 'completed' as const,
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
    duration: 12.4,
    qualityScore: 9.1,
    issuesCount: { critical: 0, high: 0, medium: 0, low: 0 },
    files: ['models/'],
  },
  {
    id: '4',
    workflowName: 'Deployment Planning',
    workflowIcon: Rocket,
    status: 'failed' as const,
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 5).toISOString(),
    duration: 23.1,
    qualityScore: 0,
    issuesCount: { critical: 0, high: 0, medium: 0, low: 0 },
    files: ['docker/', 'k8s/'],
  },
  {
    id: '5',
    workflowName: 'Security Audit',
    workflowIcon: Shield,
    status: 'completed' as const,
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(),
    duration: 52.3,
    qualityScore: 7.8,
    issuesCount: { critical: 1, high: 2, medium: 5, low: 3 },
    files: ['backend/'],
  },
]

const filterOptions = [
  { id: 'all', label: 'All' },
  { id: 'code_review', label: 'Code Reviews' },
  { id: 'security', label: 'Security' },
  { id: 'docs', label: 'Documentation' },
  { id: 'deployment', label: 'Deployment' },
]

export default function History() {
  const navigate = useNavigate()
  const [searchQuery, setSearchQuery] = useState('')
  const [activeFilter, setActiveFilter] = useState('all')
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('list')
  const [selectedItems, setSelectedItems] = useState<string[]>([])

  const filteredAnalyses = mockAnalyses.filter((analysis) => {
    const matchesSearch =
      analysis.workflowName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      analysis.files.some((f) => f.toLowerCase().includes(searchQuery.toLowerCase()))
    return matchesSearch
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-[var(--color-gray-100)]">Analysis History</h1>
        <p className="text-[var(--color-gray-400)]">
          Browse, search, and compare your past analyses
        </p>
      </div>

      {/* Search and Filters */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        {/* Search */}
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-gray-500)]" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by workflow name, files..."
            className="w-full rounded-xl border border-[var(--glass-border)] bg-[var(--bg-tertiary)] py-2.5 pl-10 pr-4 text-sm text-[var(--color-gray-100)] placeholder-[var(--color-gray-500)] outline-none focus:border-[var(--color-primary-500)]"
          />
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          {selectedItems.length > 0 && (
            <>
              <Button variant="danger" size="sm" leftIcon={<Trash2 className="h-4 w-4" />}>
                Delete ({selectedItems.length})
              </Button>
              <Button variant="secondary" size="sm" leftIcon={<Download className="h-4 w-4" />}>
                Export
              </Button>
            </>
          )}
          <div className="flex rounded-lg border border-[var(--glass-border)] bg-[var(--bg-tertiary)]">
            <button
              onClick={() => setViewMode('list')}
              className={`p-2 ${
                viewMode === 'list'
                  ? 'text-[var(--color-primary-400)]'
                  : 'text-[var(--color-gray-500)]'
              }`}
            >
              <List className="h-4 w-4" />
            </button>
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 ${
                viewMode === 'grid'
                  ? 'text-[var(--color-primary-400)]'
                  : 'text-[var(--color-gray-500)]'
              }`}
            >
              <LayoutGrid className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2 overflow-x-auto pb-2">
        {filterOptions.map((filter) => (
          <button
            key={filter.id}
            onClick={() => setActiveFilter(filter.id)}
            className={`flex-shrink-0 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
              activeFilter === filter.id
                ? 'bg-[var(--color-primary-500)]/20 text-[var(--color-primary-400)]'
                : 'bg-[var(--bg-tertiary)] text-[var(--color-gray-400)] hover:text-[var(--color-gray-100)]'
            }`}
          >
            {filter.label}
          </button>
        ))}
      </div>

      {/* Results */}
      {viewMode === 'list' ? (
        <div className="space-y-3">
          {filteredAnalyses.map((analysis, index) => {
            const Icon = analysis.workflowIcon
            const totalIssues =
              analysis.issuesCount.critical +
              analysis.issuesCount.high +
              analysis.issuesCount.medium +
              analysis.issuesCount.low

            return (
              <motion.div
                key={analysis.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.03 }}
              >
                <Card
                  hover
                  onClick={() => navigate(`/analysis/${analysis.id}`)}
                  className="flex items-center gap-4 p-4"
                >
                  {/* Checkbox */}
                  <input
                    type="checkbox"
                    checked={selectedItems.includes(analysis.id)}
                    onChange={(e) => {
                      e.stopPropagation()
                      setSelectedItems((prev) =>
                        prev.includes(analysis.id)
                          ? prev.filter((id) => id !== analysis.id)
                          : [...prev, analysis.id]
                      )
                    }}
                    className="h-4 w-4 rounded border-[var(--glass-border)] bg-[var(--bg-tertiary)]"
                  />

                  {/* Icon */}
                  <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-[var(--bg-tertiary)]">
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
                    <div className="hidden items-center gap-1.5 lg:flex">
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
                    <div className="hidden text-right sm:block">
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
                    <div className="text-xs text-[var(--color-gray-600)]">
                      {formatDuration(analysis.duration)}
                    </div>
                  </div>

                  <ChevronRight className="h-4 w-4 flex-shrink-0 text-[var(--color-gray-600)]" />
                </Card>
              </motion.div>
            )
          })}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredAnalyses.map((analysis, index) => {
            const Icon = analysis.workflowIcon
            return (
              <motion.div
                key={analysis.id}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: index * 0.03 }}
              >
                <Card hover onClick={() => navigate(`/analysis/${analysis.id}`)}>
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--bg-tertiary)]">
                      <Icon className="h-5 w-5 text-[var(--color-primary-400)]" />
                    </div>
                    <div>
                      <h4 className="font-medium text-[var(--color-gray-100)]">
                        {analysis.workflowName}
                      </h4>
                      <StatusBadge status={analysis.status} />
                    </div>
                  </div>
                  <p className="mt-3 truncate text-sm text-[var(--color-gray-500)]">
                    {analysis.files.join(', ')}
                  </p>
                  <div className="mt-4 flex items-center justify-between text-xs text-[var(--color-gray-500)]">
                    <span>{formatDate(analysis.createdAt)}</span>
                    {analysis.qualityScore > 0 && (
                      <span
                        className={`font-bold ${
                          analysis.qualityScore >= 8
                            ? 'text-[var(--color-success-400)]'
                            : analysis.qualityScore >= 6
                            ? 'text-[var(--color-warning-400)]'
                            : 'text-[var(--color-danger-400)]'
                        }`}
                      >
                        {analysis.qualityScore.toFixed(1)}/10
                      </span>
                    )}
                  </div>
                </Card>
              </motion.div>
            )
          })}
        </div>
      )}

      {/* Empty State */}
      {filteredAnalyses.length === 0 && (
        <Card className="py-12 text-center">
          <Search className="mx-auto h-12 w-12 text-[var(--color-gray-600)]" />
          <h3 className="mt-4 font-semibold text-[var(--color-gray-100)]">No analyses found</h3>
          <p className="mt-2 text-sm text-[var(--color-gray-400)]">
            Try adjusting your search or filter criteria
          </p>
        </Card>
      )}
    </div>
  )
}
