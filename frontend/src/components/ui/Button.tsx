import type { ButtonHTMLAttributes } from 'react'
import { forwardRef } from 'react'
import { Loader2 } from 'lucide-react'
import { cn } from '../../lib/utils'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'success'
  size?: 'sm' | 'md' | 'lg'
  isLoading?: boolean
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = 'primary',
      size = 'md',
      isLoading,
      leftIcon,
      rightIcon,
      children,
      disabled,
      ...props
    },
    ref
  ) => {
    const baseStyles =
      'inline-flex items-center justify-center font-medium rounded-xl transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-[var(--bg-primary)] disabled:opacity-50 disabled:cursor-not-allowed'

    const variants = {
      primary:
        'bg-gradient-to-r from-[var(--color-primary-600)] to-[var(--color-primary-500)] text-white hover:from-[var(--color-primary-500)] hover:to-[var(--color-primary-400)] focus:ring-[var(--color-primary-500)] shadow-lg shadow-[var(--color-primary-500)]/25',
      secondary:
        'bg-[var(--bg-tertiary)] text-[var(--color-gray-100)] border border-[var(--glass-border)] hover:bg-[var(--bg-elevated)] hover:border-[var(--color-gray-600)] focus:ring-[var(--color-gray-500)]',
      ghost:
        'bg-transparent text-[var(--color-gray-300)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--color-gray-100)] focus:ring-[var(--color-gray-500)]',
      danger:
        'bg-gradient-to-r from-[var(--color-danger-600)] to-[var(--color-danger-500)] text-white hover:from-[var(--color-danger-500)] hover:to-[var(--color-danger-400)] focus:ring-[var(--color-danger-500)] shadow-lg shadow-[var(--color-danger-500)]/25',
      success:
        'bg-gradient-to-r from-[var(--color-success-600)] to-[var(--color-success-500)] text-white hover:from-[var(--color-success-500)] hover:to-[var(--color-success-400)] focus:ring-[var(--color-success-500)] shadow-lg shadow-[var(--color-success-500)]/25',
    }

    const sizes = {
      sm: 'px-3 py-1.5 text-sm gap-1.5',
      md: 'px-4 py-2.5 text-sm gap-2',
      lg: 'px-6 py-3 text-base gap-2.5',
    }

    return (
      <button
        ref={ref}
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        disabled={disabled || isLoading}
        {...props}
      >
        {isLoading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : leftIcon ? (
          leftIcon
        ) : null}
        {children}
        {rightIcon && !isLoading && rightIcon}
      </button>
    )
  }
)

Button.displayName = 'Button'

export default Button
