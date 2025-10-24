import { useEffect, useState } from 'react'
import { getModels } from '../services/api'
import type { Model } from '../types'

export function Header() {
  const [models, setModels] = useState<Model[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadModels = async () => {
      try {
        const data = await getModels()
        setModels(data)
      } catch (error) {
        console.error('Failed to load models:', error)
      } finally {
        setLoading(false)
      }
    }

    loadModels()
    const interval = setInterval(loadModels, 30000) // Refresh every 30s
    return () => clearInterval(interval)
  }, [])

  const formatValue = (value: number) => {
    return new Intl.NumberFormat('de-DE', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 2,
    }).format(value)
  }

  const formatPercent = (value: number) => {
    const sign = value >= 0 ? '+' : ''
    return `${sign}${value.toFixed(2)}%`
  }

  if (loading) {
    return (
      <header className="bg-dark-surface border-b border-dark-border">
        <div className="flex items-center justify-between px-6 py-4">
          <div className="flex items-center space-x-4">
            <h1 className="text-2xl font-bold">Sentiment Arena</h1>
            <span className="text-sm text-dark-muted">AI Stock Trading Competition</span>
          </div>
        </div>
      </header>
    )
  }

  return (
    <header className="bg-dark-surface border-b border-dark-border">
      <div className="flex items-center justify-between px-6 py-4">
        <div className="flex items-center space-x-4">
          <h1 className="text-2xl font-bold">Sentiment Arena</h1>
          <span className="text-sm text-dark-muted">for Stocks</span>
        </div>
      </div>

      {/* Ticker Bar */}
      <div className="border-t border-dark-border overflow-x-auto">
        <div className="flex">
          {models.slice(0, 6).map((model) => {
            const plPercent = ((model.total_pl / model.starting_balance) * 100)
            const isProfit = model.total_pl >= 0

            return (
              <div key={model.id} className="ticker-item min-w-[180px]">
                <div className="text-xs text-dark-muted mb-1">
                  {model.name.split(' ')[0]}
                </div>
                <div className="text-lg font-semibold">
                  {formatValue(model.total_value)}
                </div>
                <div className={`text-sm ${isProfit ? 'text-profit' : 'text-loss'}`}>
                  {formatPercent(plPercent)}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </header>
  )
}
