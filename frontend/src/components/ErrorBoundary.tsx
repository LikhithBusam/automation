import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
  errorInfo: ErrorInfo | null
}

/**
 * Error Boundary component to catch JavaScript errors anywhere in child component tree.
 * Displays a fallback UI instead of crashing the whole app.
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
    this.setState({ errorInfo })
    
    // You can log to an error reporting service here
    // logErrorToService(error, errorInfo)
  }

  handleRetry = (): void => {
    this.setState({ hasError: false, error: null, errorInfo: null })
  }

  render(): ReactNode {
    if (this.state.hasError) {
      // Custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div className="flex min-h-[400px] flex-col items-center justify-center rounded-2xl border border-red-500/20 bg-red-500/5 p-8">
          <div className="mb-4 text-4xl">⚠️</div>
          <h2 className="mb-2 text-xl font-semibold text-red-400">
            Something went wrong
          </h2>
          <p className="mb-4 max-w-md text-center text-[var(--color-gray-400)]">
            An unexpected error occurred. Please try again or refresh the page.
          </p>
          
          {this.state.error && (
            <details className="mb-4 max-w-lg rounded-lg bg-[var(--bg-tertiary)] p-4">
              <summary className="cursor-pointer text-sm text-[var(--color-gray-500)]">
                Error details
              </summary>
              <pre className="mt-2 overflow-auto whitespace-pre-wrap text-xs text-red-300">
                {this.state.error.message}
                {this.state.errorInfo?.componentStack}
              </pre>
            </details>
          )}

          <div className="flex gap-3">
            <button
              onClick={this.handleRetry}
              className="rounded-lg bg-[var(--color-primary-500)] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[var(--color-primary-600)]"
            >
              Try Again
            </button>
            <button
              onClick={() => window.location.reload()}
              className="rounded-lg bg-[var(--bg-tertiary)] px-4 py-2 text-sm font-medium text-[var(--color-gray-300)] transition-colors hover:bg-[var(--bg-secondary)]"
            >
              Refresh Page
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

/**
 * HOC to wrap any component with error boundary
 */
export function withErrorBoundary<P extends object>(
  WrappedComponent: React.ComponentType<P>,
  fallback?: ReactNode
): React.FC<P> {
  return function WithErrorBoundaryWrapper(props: P) {
    return (
      <ErrorBoundary fallback={fallback}>
        <WrappedComponent {...props} />
      </ErrorBoundary>
    )
  }
}

export default ErrorBoundary
