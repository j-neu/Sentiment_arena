import type { Model } from '../types'
import clsx from 'clsx'

interface ModelCardProps {
  model: Model
  isSelected: boolean
  onToggle: (id: number) => void
}

const MODEL_COLORS = [
  'bg-blue-500',
  'bg-purple-500',
  'bg-pink-500',
  'bg-red-500',
  'bg-orange-500',
  'bg-green-500',
  'bg-cyan-500',
  'bg-indigo-500',
]

export function ModelCard({ model, isSelected, onToggle }: ModelCardProps) {
  const plPercent = ((model.total_pl / model.starting_balance) * 100)
  const isProfit = model.total_pl >= 0

  const formatValue = (value: number) => {
    return new Intl.NumberFormat('de-DE', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 2,
    }).format(value)
  }

  return (
    <button
      onClick={() => onToggle(model.id)}
      className={clsx(
        'card p-3 text-left transition-all duration-200 cursor-pointer',
        isSelected ? 'ring-2 ring-primary' : 'opacity-60 hover:opacity-100'
      )}
    >
      <div className="flex items-center justify-between mb-2">
        <div
          className={clsx(
            'w-3 h-3 rounded-full',
            MODEL_COLORS[(model.id - 1) % MODEL_COLORS.length]
          )}
        />
        <span className="text-xs text-dark-muted">
          {model.num_positions} positions
        </span>
      </div>

      <div className="text-sm font-semibold mb-1 truncate" title={model.name}>
        {model.name}
      </div>

      <div className="text-lg font-bold mb-1">
        {formatValue(model.total_value)}
      </div>

      <div className={clsx('text-sm font-semibold', isProfit ? 'text-profit' : 'text-loss')}>
        {isProfit ? '+' : ''}{plPercent.toFixed(2)}%
      </div>
    </button>
  )
}
