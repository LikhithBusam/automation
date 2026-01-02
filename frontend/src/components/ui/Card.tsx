import { cn } from '../../lib/utils'

interface CardProps {
  children: React.ReactNode
  className?: string
  variant?: 'default' | 'glass' | 'glow'
  hover?: boolean
  onClick?: () => void
}

export default function Card({
  children,
  className,
  variant = 'default',
  hover = false,
  onClick,
}: CardProps) {
  const baseStyles = 'rounded-2xl p-6 transition-all duration-300'

  const variants = {
    default:
      'bg-[var(--bg-secondary)] border border-[var(--glass-border)]',
    glass:
      'glass',
    glow:
      'bg-[var(--bg-secondary)] border border-[var(--glass-border)] glow',
  }

  const hoverStyles = hover
    ? 'cursor-pointer hover:border-[var(--color-primary-500)]/50 hover:shadow-lg hover:shadow-[var(--color-primary-500)]/10 hover:-translate-y-1'
    : ''

  return (
    <div
      className={cn(baseStyles, variants[variant], hoverStyles, className)}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      {children}
    </div>
  )
}

// Card Header
interface CardHeaderProps {
  children: React.ReactNode
  className?: string
}

export function CardHeader({ children, className }: CardHeaderProps) {
  return (
    <div className={cn('mb-4 flex items-center justify-between', className)}>
      {children}
    </div>
  )
}

// Card Title
interface CardTitleProps {
  children: React.ReactNode
  className?: string
}

export function CardTitle({ children, className }: CardTitleProps) {
  return (
    <h3 className={cn('text-lg font-semibold text-[var(--color-gray-100)]', className)}>
      {children}
    </h3>
  )
}

// Card Description
interface CardDescriptionProps {
  children: React.ReactNode
  className?: string
}

export function CardDescription({ children, className }: CardDescriptionProps) {
  return (
    <p className={cn('text-sm text-[var(--color-gray-400)]', className)}>{children}</p>
  )
}

// Card Content
interface CardContentProps {
  children: React.ReactNode
  className?: string
}

export function CardContent({ children, className }: CardContentProps) {
  return <div className={cn('', className)}>{children}</div>
}

// Card Footer
interface CardFooterProps {
  children: React.ReactNode
  className?: string
}

export function CardFooter({ children, className }: CardFooterProps) {
  return (
    <div className={cn('mt-4 flex items-center gap-3 pt-4 border-t border-[var(--glass-border)]', className)}>
      {children}
    </div>
  )
}
