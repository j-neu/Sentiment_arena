import { useEffect, useState } from 'react'
import { getLeaderboard } from '../services/api'
import type { LeaderboardEntry } from '../types'
import clsx from 'clsx'

export function Leaderboard() {
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadLeaderboard = async () => {
      try {
        const data = await getLeaderboard()
        setLeaderboard(data)
      } catch (error) {
        console.error('Failed to load leaderboard:', error)
      } finally {
        setLoading(false)
      }
    }

    loadLeaderboard()
    const interval = setInterval(loadLeaderboard, 30000) // Refresh every 30s
    return () => clearInterval(interval)
  }, [])

  const formatCurrency = (value: number) => {
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
      <div className="flex items-center justify-center h-full">
        <div className="text-dark-muted">Loading...</div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-6 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Leaderboard</h1>
        <p className="text-dark-muted">AI models ranked by performance</p>
      </div>

      <div className="card">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-dark-border">
                <th className="text-left py-4 px-4 text-sm font-semibold text-dark-muted">
                  RANK
                </th>
                <th className="text-left py-4 px-4 text-sm font-semibold text-dark-muted">
                  MODEL
                </th>
                <th className="text-right py-4 px-4 text-sm font-semibold text-dark-muted">
                  PORTFOLIO VALUE
                </th>
                <th className="text-right py-4 px-4 text-sm font-semibold text-dark-muted">
                  TOTAL P&L
                </th>
                <th className="text-right py-4 px-4 text-sm font-semibold text-dark-muted">
                  P&L %
                </th>
                <th className="text-right py-4 px-4 text-sm font-semibold text-dark-muted">
                  REALIZED P&L
                </th>
                <th className="text-right py-4 px-4 text-sm font-semibold text-dark-muted">
                  POSITIONS
                </th>
                <th className="text-right py-4 px-4 text-sm font-semibold text-dark-muted">
                  TRADES
                </th>
              </tr>
            </thead>
            <tbody>
              {leaderboard.map((entry) => {
                const isProfit = entry.total_pl >= 0
                const isTop3 = entry.rank <= 3

                return (
                  <tr
                    key={entry.model_id}
                    className={clsx(
                      'border-b border-dark-border hover:bg-dark-bg transition-colors',
                      isTop3 && 'bg-dark-bg/50'
                    )}
                  >
                    <td className="py-4 px-4">
                      <div
                        className={clsx(
                          'w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm',
                          entry.rank === 1 && 'bg-yellow-500 text-black',
                          entry.rank === 2 && 'bg-gray-400 text-black',
                          entry.rank === 3 && 'bg-orange-600 text-white',
                          entry.rank > 3 && 'bg-dark-border text-dark-muted'
                        )}
                      >
                        {entry.rank}
                      </div>
                    </td>
                    <td className="py-4 px-4">
                      <div className="font-semibold">{entry.model_name}</div>
                      <div className="text-xs text-dark-muted">{entry.api_identifier}</div>
                    </td>
                    <td className="py-4 px-4 text-right font-semibold">
                      {formatCurrency(entry.total_value)}
                    </td>
                    <td className="py-4 px-4 text-right">
                      <span className={clsx('font-semibold', isProfit ? 'text-profit' : 'text-loss')}>
                        {isProfit ? '+' : ''}
                        {formatCurrency(entry.total_pl)}
                      </span>
                    </td>
                    <td className="py-4 px-4 text-right">
                      <span className={clsx('font-semibold', isProfit ? 'text-profit' : 'text-loss')}>
                        {formatPercent(entry.total_pl_pct)}
                      </span>
                    </td>
                    <td className="py-4 px-4 text-right">
                      {formatCurrency(entry.realized_pl)}
                    </td>
                    <td className="py-4 px-4 text-right text-dark-muted">
                      {entry.num_positions}
                    </td>
                    <td className="py-4 px-4 text-right text-dark-muted">
                      {entry.num_trades}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
