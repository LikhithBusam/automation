import { cn } from '../../lib/utils'

type BadgeVariant = 'default' | 'primary' | 'success' | 'warning' | 'danger' | 'info'
type BadgeSize = 'sm' | 'md' | 'lg'

interface BadgeProps {
  children: React.ReactNode
  variant?: BadgeVariant
  size?: BadgeSize
  className?: string
  dot?: boolean
  pulse?: boolean
}

export default function Badge({
  children,
  variant = 'default',
  size = 'md',
  className,
  dot = false,
  pulse = false,
}: BadgeProps) {
  const baseStyles =
    'inline-flex items-center font-medium rounded-full transition-colors'

  const variants: Record<BadgeVariant, string> = {
    default: 'bg-[var(--bg-tertiary)] text-[var(--color-gray-300)] border border-[var(--glass-border)]',
    primary: 'bg-[var(--color-primary-500)]/20 text-[var(--color-primary-400)] border border-[var(--color-primary-500)]/30',
    success: 'bg-[var(--color-success-500)]/20 text-[var(--color-success-400)] border border-[var(--color-success-500)]/30',
    warning: 'bg-[var(--color-warning-500)]/20 text-[var(--color-warning-400)] border border-[var(--color-warning-500)]/30',
    danger: 'bg-[var(--color-danger-500)]/20 text-[var(--color-danger-400)] border border-[var(--color-danger-500)]/30',
    info: 'bg-[var(--color-accent-500)]/20 text-[var(--color-accent-400)] border border-[var(--color-accent-500)]/30',
  }

  const sizes: Record<BadgeSize, string> = {
    sm: 'px-2 py-0.5 text-xs gap-1',
    md: 'px-2.5 py-1 text-xs gap-1.5',
    lg: 'px-3 py-1.5 text-sm gap-2',
  }

  const dotColors: Record<BadgeVariant, string> = {
    default: 'bg-[var(--color-gray-400)]',
    primary: 'bg-[var(--color-primary-400)]',
    success: 'bg-[var(--color-success-400)]',
    warning: 'bg-[var(--color-warning-400)]',
    danger: 'bg-[var(--color-danger-400)]',
    info: 'bg-[var(--color-accent-400)]',
  }

  return (
    <span className={cn(baseStyles, variants[variant], sizes[size], className)}>
      {dot && (
        <span
          className={cn(
            'h-1.5 w-1.5 rounded-full',
            dotColors[variant],
            pulse && 'animate-pulse'
          )}
        />
      )}
      {children}
    </span>
  )
}

// Severity Badge - specifically for issue severity
interface SeverityBadgeProps {
  severity: 'critical' | 'high' | 'medium' | 'low'
  className?: string
  showIcon?: boolean
}

export function SeverityBadge({ severity, className, showIcon = true }: SeverityBadgeProps) {
  const config: Record<string, { variant: BadgeVariant; label: string; icon: string }> = {
    critical: { variant: 'danger', label: 'Critical', icon: '🔴' },
    high: { variant: 'warning', label: 'High', icon: '🟠' },
    medium: { variant: 'info', label: 'Medium', icon: '🟡' },
    low: { variant: 'default', label: 'Low', icon: '⚪' },
  }

  const { variant, label, icon } = config[severity]

  return (
    <Badge variant={variant} size="sm" className={className}>
      {showIcon && <span>{icon}</span>}
      {label}
    </Badge>
  )
}

// Status Badge - for agent/server status
interface StatusBadgeProps {
  status: 'running' | 'active' | 'idle' | 'offline' | 'stopped' | 'error' | 'completed' | 'pending' | 'failed'
  className?: string
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config: Record<string, { variant: BadgeVariant; label: string }> = {
    running: { variant: 'success', label: 'Running' },
    active: { variant: 'success', label: 'Active' },
    completed: { variant: 'success', label: 'Completed' },
    idle: { variant: 'default', label: 'Idle' },
    pending: { variant: 'info', label: 'Pending' },
    offline: { variant: 'danger', label: 'Offline' },
    stopped: { variant: 'danger', label: 'Stopped' },
    error: { variant: 'danger', label: 'Error' },
    failed: { variant: 'danger', label: 'Failed' },
  }

  const { variant, label } = config[status] || { variant: 'default', label: status }

  return (
    <Badge variant={variant} size="sm" dot pulse={status === 'running' || status === 'active'} className={className}>
      {label}
    </Badge>
  )
}
