import { motion } from 'framer-motion'
import type { LucideIcon } from 'lucide-react'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import Card from '../ui/Card'

interface StatsCardProps {
  title: string
  value: string
  change: string
  changeType: 'positive' | 'negative' | 'neutral'
  icon: LucideIcon
  delay?: number
}

export default function StatsCard({
  title,
  value,
  change,
  changeType,
  icon: Icon,
  delay = 0,
}: StatsCardProps) {
  const changeColors = {
    positive: 'text-[var(--color-success-400)]',
    negative: 'text-[var(--color-danger-400)]',
    neutral: 'text-[var(--color-gray-400)]',
  }

  const ChangeIcon = {
    positive: TrendingUp,
    negative: TrendingDown,
    neutral: Minus,
  }[changeType]

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
    >
      <Card className="relative overflow-hidden">
        {/* Background Gradient */}
        <div className="absolute -right-6 -top-6 h-24 w-24 rounded-full bg-gradient-to-br from-[var(--color-primary-500)]/10 to-transparent blur-2xl" />

        <div className="relative">
          <div className="flex items-center justify-between">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--bg-tertiary)]">
              <Icon className="h-5 w-5 text-[var(--color-primary-400)]" />
            </div>
            <div className={`flex items-center gap-1 text-sm ${changeColors[changeType]}`}>
              <ChangeIcon className="h-4 w-4" />
              {change}
            </div>
          </div>

          <div className="mt-4">
            <p className="text-sm text-[var(--color-gray-400)]">{title}</p>
            <p className="mt-1 text-2xl font-bold text-[var(--color-gray-100)]">{value}</p>
          </div>
        </div>
      </Card>
    </motion.div>
  )
}
