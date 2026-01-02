import { NavLink, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  LayoutDashboard,
  PlusCircle,
  History,
  Bot,
  Settings,
  HelpCircle,
  ChevronLeft,
  ChevronRight,
  Zap,
} from 'lucide-react'
import { useAppStore } from '../../stores'

const navItems = [
  { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/analysis/new', icon: PlusCircle, label: 'New Analysis' },
  { path: '/history', icon: History, label: 'History' },
  { path: '/agents', icon: Bot, label: 'Agents' },
  { path: '/settings', icon: Settings, label: 'Settings' },
]

export default function Sidebar() {
  const location = useLocation()
  const { sidebarCollapsed, toggleSidebarCollapse } = useAppStore()

  return (
    <motion.aside
      initial={false}
      animate={{ width: sidebarCollapsed ? 80 : 256 }}
      transition={{ duration: 0.3, ease: 'easeInOut' }}
      className="fixed left-0 top-0 z-40 h-screen border-r border-[var(--glass-border)] bg-[var(--bg-secondary)]"
    >
      <div className="flex h-full flex-col">
        {/* Logo */}
        <div className="flex h-16 items-center justify-between border-b border-[var(--glass-border)] px-4">
          <NavLink to="/" className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-[var(--color-primary-500)] to-[var(--color-accent-500)]">
              <Zap className="h-5 w-5 text-white" />
            </div>
            {!sidebarCollapsed && (
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="text-lg font-bold gradient-text"
              >
                AutoGen
              </motion.span>
            )}
          </NavLink>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 p-3">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={`group flex items-center gap-3 rounded-xl px-3 py-3 transition-all duration-200 ${
                  isActive
                    ? 'bg-[var(--color-primary-600)]/20 text-[var(--color-primary-400)]'
                    : 'text-[var(--color-gray-400)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--color-gray-100)]'
                }`}
              >
                <item.icon
                  className={`h-5 w-5 flex-shrink-0 ${
                    isActive ? 'text-[var(--color-primary-400)]' : ''
                  }`}
                />
                {!sidebarCollapsed && (
                  <motion.span
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="font-medium"
                  >
                    {item.label}
                  </motion.span>
                )}
                {isActive && (
                  <motion.div
                    layoutId="activeNav"
                    className="absolute left-0 h-8 w-1 rounded-r-full bg-[var(--color-primary-500)]"
                  />
                )}
              </NavLink>
            )
          })}
        </nav>

        {/* Help Link */}
        <div className="border-t border-[var(--glass-border)] p-3">
          <a
            href="/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-3 rounded-xl px-3 py-3 text-[var(--color-gray-400)] transition-all duration-200 hover:bg-[var(--bg-tertiary)] hover:text-[var(--color-gray-100)]"
          >
            <HelpCircle className="h-5 w-5 flex-shrink-0" />
            {!sidebarCollapsed && <span className="font-medium">Help & Docs</span>}
          </a>
        </div>

        {/* Collapse Toggle */}
        <div className="border-t border-[var(--glass-border)] p-3">
          <button
            onClick={toggleSidebarCollapse}
            className="flex w-full items-center justify-center rounded-xl py-2 text-[var(--color-gray-400)] transition-all duration-200 hover:bg-[var(--bg-tertiary)] hover:text-[var(--color-gray-100)]"
          >
            {sidebarCollapsed ? (
              <ChevronRight className="h-5 w-5" />
            ) : (
              <ChevronLeft className="h-5 w-5" />
            )}
          </button>
        </div>
      </div>
    </motion.aside>
  )
}
