import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  ArrowLeft,
  Download,
  Share2,
  RefreshCw,
  AlertTriangle,
  FileText,
  Shield,
  Code2,
  Lightbulb,
  Bot,
  Loader2,
} from 'lucide-react'
import Card, { CardHeader, CardTitle, CardContent } from '../components/ui/Card'
import Button from '../components/ui/Button'
import { StatusBadge } from '../components/ui/Badge'
import { formatDuration } from '../lib/utils'
import AgentTimeline from '../components/results/AgentTimeline'
import IssueCard from '../components/results/IssueCard'
import ScoreCircle from '../components/results/ScoreCircle'
import { workflowsApi, type AnalysisResult } from '../lib/api'
import toast from 'react-hot-toast'

const tabs = [
  { id: 'overview', label: 'Overview', icon: FileText },
  { id: 'security', label: 'Security Issues', icon: Shield },
  { id: 'quality', label: 'Code Quality', icon: Code2 },
  { id: 'logs', label: 'Agent Logs', icon: Bot },
]

export default function Results() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('overview')
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Fetch analysis data
  const fetchAnalysis = useCallback(async () => {
    if (!id) return
    
    try {
      const response = await workflowsApi.getAnalysis(id)
      setAnalysis(response.data)
      setError(null)
      
      // If still running, poll again
      if (response.data.status === 'pending' || response.data.status === 'running') {
        setTimeout(fetchAnalysis, 2000) // Poll every 2 seconds
      }
    } catch (err) {
      console.error('Failed to fetch analysis:', err)
      setError('Failed to load analysis. Make sure the backend is running on port 8000.')
      toast.error('Failed to load analysis')
    } finally {
      setIsLoading(false)
    }
  }, [id])

  useEffect(() => {
    fetchAnalysis()
  }, [fetchAnalysis])

  // Loading state
  if (isLoading) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <div className="text-center">
          <Loader2 className="mx-auto h-12 w-12 animate-spin text-[var(--color-primary-400)]" />
          <p className="mt-4 text-[var(--color-gray-400)]">Loading analysis...</p>
        </div>
      </div>
    )
  }

  // Error state
  if (error || !analysis) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <Card className="max-w-md p-8 text-center">
          <AlertTriangle className="mx-auto h-12 w-12 text-[var(--color-danger-400)]" />
          <h2 className="mt-4 text-xl font-semibold text-[var(--color-gray-100)]">
            Analysis Not Found
          </h2>
          <p className="mt-2 text-[var(--color-gray-400)]">
            {error || 'The analysis you requested could not be found.'}
          </p>
          <Button className="mt-6" onClick={() => navigate('/')}>
            Go to Dashboard
          </Button>
        </Card>
      </div>
    )
  }

  // Running state
  if (analysis.status === 'pending' || analysis.status === 'running') {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <Card className="max-w-md p-8 text-center">
          <Loader2 className="mx-auto h-12 w-12 animate-spin text-[var(--color-primary-400)]" />
          <h2 className="mt-4 text-xl font-semibold text-[var(--color-gray-100)]">
            Analysis in Progress
          </h2>
          <p className="mt-2 text-[var(--color-gray-400)]">
            {analysis.workflowName} is running. This page will update automatically.
          </p>
          <StatusBadge status={analysis.status} className="mt-4" />
        </Card>
      </div>
    )
  }

  // Get results or use defaults
  const results = analysis.results || {
    qualityScore: 0,
    securityScore: 0,
    summary: 'No results available',
    recommendations: [],
    issues: [],
    agentContributions: [],
    rawMessages: [],
    metrics: {
      linesAnalyzed: 0,
      filesReviewed: 0,
      issuesFound: 0,
      criticalIssues: 0,
      highIssues: 0,
      mediumIssues: 0,
      lowIssues: 0,
      timeSaved: '0 minutes'
    }
  }

  // Filter issues by tab
  const filteredIssues = (results.issues || []).filter((issue) => {
    if (activeTab === 'security') {
      return issue.category?.toLowerCase().includes('security') || 
             issue.category?.toLowerCase().includes('sql') ||
             issue.category?.toLowerCase().includes('injection')
    }
    if (activeTab === 'quality') {
      return issue.category?.toLowerCase().includes('quality') ||
             issue.category?.toLowerCase().includes('code')
    }
    return true
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            leftIcon={<ArrowLeft className="h-4 w-4" />}
            onClick={() => navigate('/')}
          >
            Back
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-[var(--color-gray-100)]">
                {analysis.workflowName}
              </h1>
              <StatusBadge status={analysis.status} />
            </div>
            <p className="text-sm text-[var(--color-gray-400)]">
              Completed in {formatDuration(analysis.duration || 0)} • {results.metrics.filesReviewed} files analyzed
            </p>
          </div>
        </div>

        <div className="flex gap-2">
          <Button variant="ghost" size="sm" leftIcon={<RefreshCw className="h-4 w-4" />} onClick={fetchAnalysis}>
            Refresh
          </Button>
          <Button variant="ghost" size="sm" leftIcon={<Share2 className="h-4 w-4" />}>
            Share
          </Button>
          <Button variant="secondary" size="sm" leftIcon={<Download className="h-4 w-4" />}>
            Export
          </Button>
        </div>
      </div>

      {/* Scores */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Quality Score */}
        <Card>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[var(--color-gray-400)]">Quality Score</p>
              <p className="mt-1 text-3xl font-bold text-[var(--color-gray-100)]">
                {results.qualityScore.toFixed(1)}
              </p>
            </div>
            <ScoreCircle score={results.qualityScore} size={80} />
          </div>
        </Card>

        {/* Security Score */}
        <Card>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[var(--color-gray-400)]">Security Score</p>
              <p className="mt-1 text-3xl font-bold text-[var(--color-gray-100)]">
                {results.securityScore.toFixed(1)}
              </p>
            </div>
            <ScoreCircle score={results.securityScore} size={80} />
          </div>
        </Card>

        {/* Metrics */}
        <Card>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-2xl font-bold text-[var(--color-danger-400)]">
                {results.metrics.criticalIssues}
              </p>
              <p className="text-xs text-[var(--color-gray-500)]">Critical</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-[var(--color-warning-400)]">
                {results.metrics.highIssues}
              </p>
              <p className="text-xs text-[var(--color-gray-500)]">High</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-[var(--color-gray-100)]">
                {results.metrics.linesAnalyzed.toLocaleString()}
              </p>
              <p className="text-xs text-[var(--color-gray-500)]">Lines Analyzed</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-[var(--color-success-400)]">
                {results.metrics.timeSaved}
              </p>
              <p className="text-xs text-[var(--color-gray-500)]">Time Saved</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-2 border-b border-[var(--glass-border)]">
        {tabs.map((tab) => {
          const Icon = tab.icon
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? 'border-[var(--color-primary-500)] text-[var(--color-primary-400)]'
                  : 'border-transparent text-[var(--color-gray-500)] hover:text-[var(--color-gray-300)]'
              }`}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Executive Summary */}
          <Card>
            <CardHeader>
              <CardTitle>Executive Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-[var(--color-gray-300)] whitespace-pre-wrap">{results.summary}</p>
            </CardContent>
          </Card>

          {/* Agent Timeline */}
          {results.agentContributions && results.agentContributions.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Bot className="h-5 w-5 text-[var(--color-primary-400)]" />
                  Agent Collaboration Timeline
                </CardTitle>
              </CardHeader>
              <CardContent>
                <AgentTimeline contributions={results.agentContributions} />
              </CardContent>
            </Card>
          )}

          {/* Recommendations */}
          {results.recommendations && results.recommendations.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Lightbulb className="h-5 w-5 text-[var(--color-warning-400)]" />
                  Recommendations
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ol className="list-inside list-decimal space-y-2">
                  {results.recommendations.map((rec, index) => (
                    <li key={index} className="text-[var(--color-gray-300)]">
                      {rec}
                    </li>
                  ))}
                </ol>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Security/Quality Issues Tab */}
      {(activeTab === 'security' || activeTab === 'quality') && (
        <div className="space-y-3">
          {filteredIssues.length > 0 ? (
            filteredIssues.map((issue, index) => (
              <motion.div
                key={issue.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
              >
                <IssueCard issue={issue} />
              </motion.div>
            ))
          ) : (
            <Card className="py-8 text-center">
              <p className="text-[var(--color-gray-400)]">No issues found in this category</p>
            </Card>
          )}
        </div>
      )}

      {/* Agent Logs Tab */}
      {activeTab === 'logs' && (
        <Card>
          <CardHeader>
            <CardTitle>Agent Messages</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4 max-h-[600px] overflow-y-auto">
              {(results.rawMessages || []).map((msg, index) => (
                <div
                  key={index}
                  className="rounded-lg bg-[var(--bg-tertiary)] p-4 border border-[var(--glass-border)]"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <Bot className="h-4 w-4 text-[var(--color-primary-400)]" />
                    <span className="text-sm font-medium text-[var(--color-primary-400)]">
                      {msg.name || msg.role || 'Agent'}
                    </span>
                  </div>
                  <pre className="text-sm text-[var(--color-gray-300)] whitespace-pre-wrap font-mono">
                    {msg.content || '(empty message)'}
                  </pre>
                </div>
              ))}
              {(!results.rawMessages || results.rawMessages.length === 0) && (
                <p className="text-[var(--color-gray-400)] text-center py-8">
                  No agent messages available
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
