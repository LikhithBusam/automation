import { Outlet } from 'react-router-dom'
import { motion } from 'framer-motion'
import Sidebar from './Sidebar'
import Header from './Header'
import { useAppStore } from '../../stores'

export default function Layout() {
  const { sidebarCollapsed } = useAppStore()

  return (
    <div className="flex h-screen overflow-hidden bg-[var(--bg-primary)]">
      {/* Sidebar */}
      <Sidebar />

      {/* Main Content */}
      <div
        className={`flex flex-1 flex-col transition-all duration-300 ${
          sidebarCollapsed ? 'ml-20' : 'ml-64'
        }`}
      >
        {/* Header */}
        <Header />

        {/* Page Content */}
        <main className="flex-1 overflow-auto p-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="mx-auto max-w-7xl"
          >
            <Outlet />
          </motion.div>
        </main>
      </div>
    </div>
  )
}
