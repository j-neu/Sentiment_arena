import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getModels, getPerformance, getPortfolio } from '../services/api'
import type { Model, Performance, Portfolio } from '../types'
import clsx from 'clsx'
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts'

export function Models() {
  const { modelId } = useParams<{ modelId: string }>()
  const [models, setModels] = useState<Model[]>([])
  const [selectedModel, setSelectedModel] = useState<Model | null>(null)
  const [performance, setPerformance] = useState<Performance | null>(null)
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadModels = async () => {
      try {
        const data = await getModels()
        setModels(data)
        if (modelId) {
          const model = data.find((m) => m.id === parseInt(modelId))
          if (model) {
            setSelectedModel(model)
            loadModelDetails(model.id)
          }
        } else if (data.length > 0) {
          setSelectedModel(data[0])
          loadModelDetails(data[0].id)
        }
      } catch (error) {
        console.error('Failed to load models:', error)
      } finally {
        setLoading(false)
      }
    }

    loadModels()
  }, [modelId])

  const loadModelDetails = async (id: number) => {
    try {
      const [perfData, portData] = await Promise.all([
        getPerformance(id),
        getPortfolio(id),
      ])
      setPerformance(perfData)
      setPortfolio(portData)
    } catch (error) {
      console.error('Failed to load model details:', error)
    }
  }

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
        <h1 className="text-3xl font-bold mb-2">Models</h1>
        <p className="text-dark-muted">Detailed view of AI trading models</p>
      </div>

      <div className="grid grid-cols-12 gap-6">
        {/* Model List */}
        <div className="col-span-3">
          <div className="card">
            <h3 className="text-lg font-semibold mb-4">All Models</h3>
            <div className="space-y-2">
              {models.map((model) => (
                <button
                  key={model.id}
                  onClick={() => {
                    setSelectedModel(model)
                    loadModelDetails(model.id)
                  }}
                  className={clsx(
                    'w-full text-left p-3 rounded transition-colors',
                    selectedModel?.id === model.id
                      ? 'bg-primary text-white'
                      : 'hover:bg-dark-bg'
                  )}
                >
                  <div className="font-semibold">{model.name}</div>
                  <div className="text-xs opacity-75">
                    {formatCurrency(model.total_value)}
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Model Details */}
        <div className="col-span-9">
          {selectedModel && performance && portfolio && (
            <div className="space-y-6">
              {/* Header */}
              <div className="card">
                <h2 className="text-2xl font-bold mb-2">{selectedModel.name}</h2>
                <p className="text-dark-muted mb-4">{selectedModel.api_identifier}</p>
                <div className="grid grid-cols-4 gap-4">
                  <div>
                    <div className="text-dark-muted text-sm mb-1">Portfolio Value</div>
                    <div className="text-2xl font-bold">
                      {formatCurrency(performance.total_value)}
                    </div>
                  </div>
                  <div>
                    <div className="text-dark-muted text-sm mb-1">Total P&L</div>
                    <div
                      className={clsx(
                        'text-2xl font-bold',
                        performance.total_pl >= 0 ? 'text-profit' : 'text-loss'
                      )}
                    >
                      {formatPercent(performance.total_pl_pct)}
                    </div>
                  </div>
                  <div>
                    <div className="text-dark-muted text-sm mb-1">Win Rate</div>
                    <div className="text-2xl font-bold">
                      {performance.win_rate.toFixed(1)}%
                    </div>
                  </div>
                  <div>
                    <div className="text-dark-muted text-sm mb-1">Total Trades</div>
                    <div className="text-2xl font-bold">{performance.total_trades}</div>
                  </div>
                </div>
              </div>

              {/* Portfolio Composition */}
              {portfolio.positions.length > 0 && (
                <div className="card">
                  <h3 className="text-lg font-semibold mb-4">Portfolio Composition</h3>
                  <div className="h-80">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={[
                            { name: 'Cash', value: performance.current_balance },
                            ...portfolio.positions.map(p => ({
                              name: p.symbol,
                              value: p.position_value
                            }))
                          ]}
                          cx="50%"
                          cy="50%"
                          labelLine={false}
                          label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                          outerRadius={100}
                          fill="#8884d8"
                          dataKey="value"
                        >
                          {[
                            { name: 'Cash', value: performance.current_balance },
                            ...portfolio.positions.map(p => ({
                              name: p.symbol,
                              value: p.position_value
                            }))
                          ].map((entry, index) => {
                            const COLORS = ['#10b981', '#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#ef4444', '#06b6d4', '#6366f1']
                            return <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                          })}
                        </Pie>
                        <Tooltip
                          contentStyle={{
                            backgroundColor: '#1a1a1a',
                            border: '1px solid #333',
                            borderRadius: '8px',
                            color: '#e5e5e5'
                          }}
                          formatter={(value: number) => formatCurrency(value)}
                        />
                        <Legend
                          wrapperStyle={{ color: '#9ca3af' }}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="mt-4 text-sm text-dark-muted text-center">
                    Total Portfolio Value: {formatCurrency(performance.total_value)}
                  </div>
                </div>
              )}

              {/* Performance Metrics */}
              <div className="card">
                <h3 className="text-lg font-semibold mb-4">Performance Metrics</h3>
                <div className="grid grid-cols-3 gap-6">
                  <div>
                    <div className="text-dark-muted text-sm mb-2">Starting Balance</div>
                    <div className="font-semibold">
                      {formatCurrency(performance.starting_balance)}
                    </div>
                  </div>
                  <div>
                    <div className="text-dark-muted text-sm mb-2">Current Balance</div>
                    <div className="font-semibold">
                      {formatCurrency(performance.current_balance)}
                    </div>
                  </div>
                  <div>
                    <div className="text-dark-muted text-sm mb-2">ROI</div>
                    <div
                      className={clsx(
                        'font-semibold',
                        performance.roi >= 0 ? 'text-profit' : 'text-loss'
                      )}
                    >
                      {formatPercent(performance.roi)}
                    </div>
                  </div>
                  <div>
                    <div className="text-dark-muted text-sm mb-2">Realized P&L</div>
                    <div className="font-semibold">
                      {formatCurrency(performance.realized_pl)}
                    </div>
                  </div>
                  <div>
                    <div className="text-dark-muted text-sm mb-2">Unrealized P&L</div>
                    <div className="font-semibold">
                      {formatCurrency(performance.unrealized_pl)}
                    </div>
                  </div>
                  <div>
                    <div className="text-dark-muted text-sm mb-2">Total Fees</div>
                    <div className="font-semibold">
                      {formatCurrency(performance.total_fees_paid)}
                    </div>
                  </div>
                  <div>
                    <div className="text-dark-muted text-sm mb-2">Winning Trades</div>
                    <div className="font-semibold text-profit">
                      {performance.winning_trades}
                    </div>
                  </div>
                  <div>
                    <div className="text-dark-muted text-sm mb-2">Losing Trades</div>
                    <div className="font-semibold text-loss">
                      {performance.losing_trades}
                    </div>
                  </div>
                  <div>
                    <div className="text-dark-muted text-sm mb-2">Open Positions</div>
                    <div className="font-semibold">{performance.num_positions}</div>
                  </div>
                </div>
              </div>

              {/* Current Positions */}
              <div className="card">
                <h3 className="text-lg font-semibold mb-4">Current Positions</h3>
                {portfolio.positions.length === 0 ? (
                  <div className="text-center text-dark-muted py-8">No open positions</div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-dark-border">
                          <th className="text-left py-3 px-4 text-sm font-semibold text-dark-muted">
                            SYMBOL
                          </th>
                          <th className="text-right py-3 px-4 text-sm font-semibold text-dark-muted">
                            QUANTITY
                          </th>
                          <th className="text-right py-3 px-4 text-sm font-semibold text-dark-muted">
                            AVG PRICE
                          </th>
                          <th className="text-right py-3 px-4 text-sm font-semibold text-dark-muted">
                            CURRENT PRICE
                          </th>
                          <th className="text-right py-3 px-4 text-sm font-semibold text-dark-muted">
                            VALUE
                          </th>
                          <th className="text-right py-3 px-4 text-sm font-semibold text-dark-muted">
                            P&L
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {portfolio.positions.map((position) => {
                          const isProfit = position.unrealized_pl >= 0
                          return (
                            <tr
                              key={position.id}
                              className="border-b border-dark-border hover:bg-dark-bg transition-colors"
                            >
                              <td className="py-3 px-4 font-semibold">{position.symbol}</td>
                              <td className="py-3 px-4 text-right">{position.quantity}</td>
                              <td className="py-3 px-4 text-right">
                                {formatCurrency(position.avg_price)}
                              </td>
                              <td className="py-3 px-4 text-right">
                                {formatCurrency(position.current_price)}
                              </td>
                              <td className="py-3 px-4 text-right">
                                {formatCurrency(position.position_value)}
                              </td>
                              <td className="py-3 px-4 text-right">
                                <span
                                  className={clsx(
                                    'font-semibold',
                                    isProfit ? 'text-profit' : 'text-loss'
                                  )}
                                >
                                  {isProfit ? '+' : ''}
                                  {formatCurrency(position.unrealized_pl)}
                                  <span className="text-xs ml-1">
                                    ({formatPercent(position.unrealized_pl_pct)})
                                  </span>
                                </span>
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
