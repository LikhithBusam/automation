import { getScoreColor } from '../../lib/utils'

interface ScoreCircleProps {
  score: number
  label?: string
  size?: 'sm' | 'md' | 'lg' | number
}

export default function ScoreCircle({ score, label, size = 'md' }: ScoreCircleProps) {
  const circumference = 2 * Math.PI * 40
  const strokeDashoffset = circumference - (score / 10) * circumference
  const color = getScoreColor(score)

  const sizePresets = {
    sm: { container: 'w-16 h-16', text: 'text-lg', label: 'text-xs' },
    md: { container: 'w-24 h-24', text: 'text-2xl', label: 'text-xs' },
    lg: { container: 'w-32 h-32', text: 'text-3xl', label: 'text-sm' },
  }

  // Handle number size (convert to closest preset)
  const getSizePreset = () => {
    if (typeof size === 'number') {
      if (size <= 64) return 'sm'
      if (size <= 96) return 'md'
      return 'lg'
    }
    return size
  }

  const sizeStyle = sizePresets[getSizePreset()]

  return (
    <div className="flex flex-col items-center">
      <div className={`relative ${sizeStyle.container}`}>
        <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
          {/* Background Circle */}
          <circle
            cx="50"
            cy="50"
            r="40"
            fill="none"
            stroke="var(--bg-tertiary)"
            strokeWidth="8"
          />
          {/* Progress Circle */}
          <circle
            cx="50"
            cy="50"
            r="40"
            fill="none"
            stroke={color}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            className="transition-all duration-1000 ease-out"
            style={{
              filter: `drop-shadow(0 0 8px ${color}40)`,
            }}
          />
        </svg>
        {/* Score Text */}
        <div className="absolute inset-0 flex items-center justify-center">
          <span
            className={`font-bold ${sizeStyle.text}`}
            style={{ color }}
          >
            {score.toFixed(1)}
          </span>
        </div>
      </div>
      {label && (
        <span className={`mt-2 text-[var(--color-gray-400)] ${sizeStyle.label}`}>
          {label}
        </span>
      )}
    </div>
  )
}
