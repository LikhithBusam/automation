import { Link } from 'react-router-dom'
import { Home, Search } from 'lucide-react'
import Button from '../components/ui/Button'

export default function NotFound() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      <div className="text-9xl font-bold text-[var(--color-gray-800)]">404</div>
      <h1 className="mt-4 text-2xl font-bold text-[var(--color-gray-100)]">Page Not Found</h1>
      <p className="mt-2 text-[var(--color-gray-400)]">
        The page you're looking for doesn't exist or has been moved.
      </p>
      <div className="mt-8 flex gap-4">
        <Link to="/">
          <Button leftIcon={<Home className="h-4 w-4" />}>Go Home</Button>
        </Link>
        <Link to="/history">
          <Button variant="secondary" leftIcon={<Search className="h-4 w-4" />}>
            Search History
          </Button>
        </Link>
      </div>
    </div>
  )
}
