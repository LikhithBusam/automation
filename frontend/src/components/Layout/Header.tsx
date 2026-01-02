import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, Bell, User, Command, X } from 'lucide-react'
import { useAppStore } from '../../stores'

export default function Header() {
  const [searchOpen, setSearchOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const { notifications, removeNotification } = useAppStore()

  const unreadCount = notifications.length

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-[var(--glass-border)] bg-[var(--bg-secondary)]/80 px-6 backdrop-blur-xl">
      {/* Search Bar */}
      <div className="flex flex-1 items-center">
        <div className="relative w-full max-w-md">
          <button
            onClick={() => setSearchOpen(true)}
            className="flex w-full items-center gap-3 rounded-xl border border-[var(--glass-border)] bg-[var(--bg-tertiary)] px-4 py-2.5 text-[var(--color-gray-400)] transition-all duration-200 hover:border-[var(--color-primary-500)]/50 hover:bg-[var(--bg-elevated)]"
          >
            <Search className="h-4 w-4" />
            <span className="text-sm">Search analyses, agents, docs...</span>
            <div className="ml-auto flex items-center gap-1 rounded-md bg-[var(--bg-primary)] px-2 py-1 text-xs">
              <Command className="h-3 w-3" />
              <span>K</span>
            </div>
          </button>
        </div>
      </div>

      {/* Right Side */}
      <div className="flex items-center gap-4">
        {/* Notifications */}
        <div className="relative">
          <button
            onClick={() => setNotificationsOpen(!notificationsOpen)}
            className="relative flex h-10 w-10 items-center justify-center rounded-xl text-[var(--color-gray-400)] transition-all duration-200 hover:bg-[var(--bg-tertiary)] hover:text-[var(--color-gray-100)]"
          >
            <Bell className="h-5 w-5" />
            {unreadCount > 0 && (
              <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-[var(--color-danger-500)] text-xs font-bold text-white">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </button>

          {/* Notifications Dropdown */}
          <AnimatePresence>
            {notificationsOpen && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 10 }}
                className="absolute right-0 top-full mt-2 w-80 rounded-xl border border-[var(--glass-border)] bg-[var(--bg-secondary)] p-2 shadow-lg"
              >
                <div className="mb-2 flex items-center justify-between px-3 py-2">
                  <h3 className="font-semibold text-[var(--color-gray-100)]">Notifications</h3>
                  <button
                    onClick={() => setNotificationsOpen(false)}
                    className="text-[var(--color-gray-400)] hover:text-[var(--color-gray-100)]"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
                {notifications.length === 0 ? (
                  <div className="px-3 py-6 text-center text-sm text-[var(--color-gray-500)]">
                    No notifications yet
                  </div>
                ) : (
                  <div className="max-h-80 space-y-1 overflow-auto">
                    {notifications.slice(0, 5).map((notification) => (
                      <div
                        key={notification.id}
                        className="flex items-start gap-3 rounded-lg p-3 transition-colors hover:bg-[var(--bg-tertiary)]"
                      >
                        <div className="flex-1">
                          <p className="text-sm font-medium text-[var(--color-gray-100)]">
                            {notification.title}
                          </p>
                          <p className="text-xs text-[var(--color-gray-400)]">
                            {notification.message}
                          </p>
                        </div>
                        <button
                          onClick={() => removeNotification(notification.id)}
                          className="text-[var(--color-gray-500)] hover:text-[var(--color-gray-300)]"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* User Menu */}
        <button className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-[var(--color-primary-500)] to-[var(--color-accent-500)]">
          <User className="h-5 w-5 text-white" />
        </button>
      </div>

      {/* Search Modal */}
      <AnimatePresence>
        {searchOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-start justify-center bg-black/60 pt-24 backdrop-blur-sm"
            onClick={() => setSearchOpen(false)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="w-full max-w-2xl rounded-2xl border border-[var(--glass-border)] bg-[var(--bg-secondary)] p-4 shadow-2xl"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center gap-3 border-b border-[var(--glass-border)] pb-4">
                <Search className="h-5 w-5 text-[var(--color-gray-400)]" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search analyses, agents, documentation..."
                  className="flex-1 bg-transparent text-lg text-[var(--color-gray-100)] placeholder-[var(--color-gray-500)] outline-none"
                  autoFocus
                />
                <kbd className="rounded-md bg-[var(--bg-tertiary)] px-2 py-1 text-xs text-[var(--color-gray-400)]">
                  ESC
                </kbd>
              </div>
              <div className="py-4 text-center text-sm text-[var(--color-gray-500)]">
                Start typing to search...
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  )
}
