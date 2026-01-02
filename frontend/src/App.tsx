import { Routes, Route } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { Suspense, lazy } from 'react'
import { ErrorBoundary } from './components/ErrorBoundary'

// Lazy load components
const Layout = lazy(() => import('./components/Layout/Layout'))
const Dashboard = lazy(() => import('./pages/Dashboard'))
const NewAnalysis = lazy(() => import('./pages/NewAnalysis'))
const Results = lazy(() => import('./pages/Results'))
const History = lazy(() => import('./pages/History'))
const Agents = lazy(() => import('./pages/Agents'))
const Settings = lazy(() => import('./pages/Settings'))
const NotFound = lazy(() => import('./pages/NotFound'))

// Loading fallback
function LoadingFallback() {
  return (
    <div className="flex h-screen w-screen items-center justify-center bg-[#0a0a0f]">
      <div className="text-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent mx-auto"></div>
        <p className="mt-4 text-gray-400">Loading...</p>
      </div>
    </div>
  )
}

function App() {
  return (
    <>
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#1f2937',
            color: '#f3f4f6',
            border: '1px solid rgba(255, 255, 255, 0.1)',
          },
          success: {
            iconTheme: {
              primary: '#22c55e',
              secondary: '#f3f4f6',
            },
          },
          error: {
            iconTheme: {
              primary: '#ef4444',
              secondary: '#f3f4f6',
            },
          },
        }}
      />
      <ErrorBoundary>
        <Suspense fallback={<LoadingFallback />}>
          <Routes>
            <Route path="/" element={<Layout />}>
              <Route index element={<Dashboard />} />
              <Route path="analysis/new" element={<NewAnalysis />} />
              <Route path="analysis/:id" element={<Results />} />
              <Route path="history" element={<History />} />
              <Route path="agents" element={<Agents />} />
              <Route path="settings" element={<Settings />} />
              <Route path="*" element={<NotFound />} />
            </Route>
          </Routes>
        </Suspense>
      </ErrorBoundary>
    </>
  )
}

export default App
