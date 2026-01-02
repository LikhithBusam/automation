import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ChevronDown,
  ChevronRight,
  Copy,
  Check,
  ExternalLink,
  FileCode,
  Lightbulb,
} from 'lucide-react'
import { SeverityBadge } from '../ui/Badge'
import Button from '../ui/Button'
import type { Issue } from '../../types'

interface IssueCardProps {
  issue: Issue
}

export default function IssueCard({ issue }: IssueCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [copied, setCopied] = useState(false)

  const handleCopy = async (text: string) => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div
      className={`rounded-2xl border transition-all duration-300 ${
        issue.severity === 'critical'
          ? 'border-[var(--color-danger-500)]/30 bg-[var(--color-danger-500)]/5'
          : issue.severity === 'high'
          ? 'border-[var(--color-warning-500)]/30 bg-[var(--color-warning-500)]/5'
          : 'border-[var(--glass-border)] bg-[var(--bg-secondary)]'
      }`}
    >
      {/* Header - Always visible */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex w-full items-center gap-4 p-4 text-left"
      >
        <div
          className={`flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg ${
            isExpanded ? 'bg-[var(--bg-elevated)]' : 'bg-[var(--bg-tertiary)]'
          }`}
        >
          {isExpanded ? (
            <ChevronDown className="h-4 w-4 text-[var(--color-gray-400)]" />
          ) : (
            <ChevronRight className="h-4 w-4 text-[var(--color-gray-400)]" />
          )}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3">
            <SeverityBadge severity={issue.severity} />
            <span className="rounded bg-[var(--bg-tertiary)] px-2 py-0.5 text-xs text-[var(--color-gray-400)]">
              {issue.category}
            </span>
          </div>
          <h4 className="mt-1 font-medium text-[var(--color-gray-100)]">{issue.title}</h4>
        </div>

        <div className="flex flex-shrink-0 items-center gap-2 text-xs text-[var(--color-gray-500)]">
          <FileCode className="h-3.5 w-3.5" />
          <span>
            {issue.file}:{issue.line}
          </span>
        </div>
      </button>

      {/* Expanded Content */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="space-y-4 border-t border-[var(--glass-border)] p-4">
              {/* Description */}
              <div>
                <h5 className="mb-2 text-sm font-medium text-[var(--color-gray-300)]">
                  Why this is dangerous
                </h5>
                <p className="text-sm text-[var(--color-gray-400)]">{issue.description}</p>
              </div>

              {/* OWASP Category */}
              {issue.owaspCategory && (
                <div className="flex items-center gap-2">
                  <span className="rounded-lg bg-[var(--color-danger-500)]/10 px-3 py-1.5 text-xs font-medium text-[var(--color-danger-400)]">
                    {issue.owaspCategory}
                  </span>
                  <a
                    href={`https://owasp.org/Top10/`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-xs text-[var(--color-primary-400)] hover:underline"
                  >
                    Learn more <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
              )}

              {/* Problematic Code */}
              {issue.code && (
                <div>
                  <h5 className="mb-2 text-sm font-medium text-[var(--color-danger-400)]">
                    ❌ Problematic Code
                  </h5>
                  <div className="relative rounded-lg bg-[var(--bg-primary)] p-4">
                    <pre className="overflow-x-auto text-sm text-[var(--color-gray-300)] font-code">
                      <code>{issue.code}</code>
                    </pre>
                    <button
                      onClick={() => handleCopy(issue.code!)}
                      className="absolute right-2 top-2 rounded-lg bg-[var(--bg-tertiary)] p-2 text-[var(--color-gray-400)] hover:text-[var(--color-gray-200)]"
                    >
                      {copied ? (
                        <Check className="h-4 w-4 text-[var(--color-success-400)]" />
                      ) : (
                        <Copy className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                </div>
              )}

              {/* Suggested Fix */}
              {issue.suggestion && (
                <div>
                  <h5 className="mb-2 flex items-center gap-2 text-sm font-medium text-[var(--color-success-400)]">
                    <Lightbulb className="h-4 w-4" />
                    How to fix it
                  </h5>
                  <div className="relative rounded-lg bg-[var(--color-success-500)]/5 border border-[var(--color-success-500)]/20 p-4">
                    <pre className="overflow-x-auto text-sm text-[var(--color-gray-300)] font-code">
                      <code>{issue.suggestion}</code>
                    </pre>
                    <button
                      onClick={() => handleCopy(issue.suggestion!)}
                      className="absolute right-2 top-2 rounded-lg bg-[var(--bg-tertiary)] p-2 text-[var(--color-gray-400)] hover:text-[var(--color-gray-200)]"
                    >
                      {copied ? (
                        <Check className="h-4 w-4 text-[var(--color-success-400)]" />
                      ) : (
                        <Copy className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex items-center gap-2 pt-2">
                <Button variant="success" size="sm">
                  Apply Fix
                </Button>
                <Button variant="secondary" size="sm">
                  Mark as Resolved
                </Button>
                <Button variant="ghost" size="sm">
                  Create Issue
                </Button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
