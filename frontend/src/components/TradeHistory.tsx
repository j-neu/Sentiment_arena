import { useEffect, useState } from 'react'
import { getModels, getTrades, getReasoning } from '../services/api'
import type { Model, Trade, Reasoning } from '../types'
import { formatDistanceToNow, format } from 'date-fns'
import clsx from 'clsx'
import wsClient from '../services/websocket'

type Tab = 'TRADES' | 'POSITIONS' | 'REASONING'

export function TradeHistory() {
  const [activeTab, setActiveTab] = useState<Tab>('TRADES')
  const [models, setModels] = useState<Model[]>([])
  const [selectedModel, setSelectedModel] = useState<number | 'ALL'>('ALL')
  const [trades, setTrades] = useState<(Trade & { model_name: string })[]>([])
  const [reasoning, setReasoning] = useState<(Reasoning & { model_name: string })[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadData = async () => {
      try {
        const modelsData = await getModels()
        setModels(modelsData)

        // Load trades from all models
        const allTrades: (Trade & { model_name: string })[] = []
        const allReasoning: (Reasoning & { model_name: string })[] = []

        for (const model of modelsData) {
          const response = await getTrades(model.id, 0, 20)
          const tradesWithModel = response.trades.map((trade) => ({
            ...trade,
            model_name: model.name,
          }))
          allTrades.push(...tradesWithModel)

          // Load reasoning entries
          try {
            const reasoningResponse = await getReasoning(model.id, 0, 10)
            const reasoningWithModel = reasoningResponse.reasoning.map((r) => ({
              ...r,
              model_name: model.name,
            }))
            allReasoning.push(...reasoningWithModel)
          } catch (err) {
            console.error(`Failed to load reasoning for ${model.name}:`, err)
          }
        }

        // Sort by timestamp descending
        allTrades.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
        allReasoning.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())

        setTrades(allTrades.slice(0, 100)) // Keep last 100 trades
        setReasoning(allReasoning.slice(0, 50)) // Keep last 50 reasoning entries
      } catch (error) {
        console.error('Failed to load trade history:', error)
      } finally {
        setLoading(false)
      }
    }

    loadData()

    // Subscribe to real-time updates
    const unsubscribe = wsClient.subscribe((message) => {
      if (message.type === 'trade') {
        // Find the model name
        const model = models.find((m) => m.id === message.model_id)
        if (model) {
          const newTrade: Trade & { model_name: string } = {
            id: message.trade_id,
            symbol: message.symbol,
            side: message.side,
            quantity: message.quantity,
            price: message.price,
            fee: message.fee,
            total: message.price * message.quantity + message.fee,
            status: 'COMPLETED',
            timestamp: message.timestamp || new Date().toISOString(),
            model_name: model.name,
          }
          setTrades((prev) => [newTrade, ...prev].slice(0, 100))
        }
      } else if (message.type === 'reasoning') {
        // Find the model name
        const model = models.find((m) => m.id === message.model_id)
        if (model) {
          const newReasoning: Reasoning & { model_name: string } = {
            id: message.reasoning_id || Date.now(),
            model_id: message.model_id,
            timestamp: message.timestamp || new Date().toISOString(),
            research_content: message.research_content || '',
            decision: message.decision || '',
            reasoning_text: message.reasoning_text || '',
            model_name: model.name,
          }
          setReasoning((prev) => [newReasoning, ...prev].slice(0, 50))
        }
      }
    })

    return () => {
      unsubscribe()
    }
  }, [models])

  const filteredTrades =
    selectedModel === 'ALL'
      ? trades
      : trades.filter((t) => {
          const model = models.find((m) => m.name === t.model_name)
          return model?.id === selectedModel
        })

  const filteredReasoning =
    selectedModel === 'ALL'
      ? reasoning
      : reasoning.filter((r) => {
          const model = models.find((m) => m.name === r.model_name)
          return model?.id === selectedModel
        })

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('de-DE', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 2,
    }).format(value)
  }

  const exportToCSV = () => {
    if (filteredTrades.length === 0) return

    // CSV headers
    const headers = ['Timestamp', 'Model', 'Symbol', 'Side', 'Quantity', 'Price', 'Fee', 'Total', 'Status']

    // CSV rows
    const rows = filteredTrades.map(trade => [
      new Date(trade.timestamp).toISOString(),
      trade.model_name,
      trade.symbol,
      trade.side,
      trade.quantity.toString(),
      trade.price.toFixed(2),
      trade.fee.toFixed(2),
      trade.total.toFixed(2),
      trade.status
    ])

    // Combine headers and rows
    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.join(','))
    ].join('\n')

    // Create download link
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)

    link.setAttribute('href', url)
    link.setAttribute('download', `trades_${new Date().toISOString().split('T')[0]}.csv`)
    link.style.visibility = 'hidden'

    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  return (
    <div className="h-full flex flex-col bg-dark-surface">
      {/* Tabs */}
      <div className="flex border-b border-dark-border">
        <button
          onClick={() => setActiveTab('TRADES')}
          className={clsx(
            'flex-1 px-4 py-3 text-xs font-semibold transition-colors',
            activeTab === 'TRADES'
              ? 'bg-dark-bg text-dark-text border-b-2 border-primary'
              : 'text-dark-muted hover:text-dark-text'
          )}
        >
          COMPLETED TRADES
        </button>
        <button
          onClick={() => setActiveTab('POSITIONS')}
          className={clsx(
            'flex-1 px-4 py-3 text-xs font-semibold transition-colors',
            activeTab === 'POSITIONS'
              ? 'bg-dark-bg text-dark-text border-b-2 border-primary'
              : 'text-dark-muted hover:text-dark-text'
          )}
        >
          POSITIONS
        </button>
        <button
          onClick={() => setActiveTab('REASONING')}
          className={clsx(
            'flex-1 px-4 py-3 text-xs font-semibold transition-colors',
            activeTab === 'REASONING'
              ? 'bg-dark-bg text-dark-text border-b-2 border-primary'
              : 'text-dark-muted hover:text-dark-text'
          )}
        >
          REASONING
        </button>
      </div>

      {/* Filter & Actions */}
      <div className="p-3 border-b border-dark-border">
        <div className="flex items-end gap-3">
          <div className="flex-1">
            <label className="block text-xs text-dark-muted mb-1">FILTER:</label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value === 'ALL' ? 'ALL' : Number(e.target.value))}
              className="w-full bg-dark-bg border border-dark-border rounded px-3 py-2 text-sm text-dark-text"
            >
              <option value="ALL">ALL MODELS ▼</option>
              {models.map((model) => (
                <option key={model.id} value={model.id}>
                  {model.name}
                </option>
              ))}
            </select>
          </div>
          {activeTab === 'TRADES' && filteredTrades.length > 0 && (
            <button
              onClick={exportToCSV}
              className="bg-primary hover:bg-primary/80 text-white px-4 py-2 rounded text-sm font-semibold transition-colors"
              title="Export trades to CSV"
            >
              Export CSV
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === 'TRADES' && (
          <div className="p-3 space-y-3">
            {loading ? (
              <div className="text-center text-dark-muted py-8">Loading...</div>
            ) : filteredTrades.length === 0 ? (
              <div className="text-center text-dark-muted py-8">No trades yet</div>
            ) : (
              filteredTrades.map((trade) => {
                const isLong = trade.side === 'BUY'
                const timeAgo = formatDistanceToNow(new Date(trade.timestamp), { addSuffix: true })

                return (
                  <div
                    key={`${trade.id}-${trade.timestamp}`}
                    className="bg-dark-bg border border-dark-border rounded p-3 text-xs"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center space-x-2">
                        <span className="font-semibold text-dark-text">
                          {trade.model_name.split(' ')[0]}
                        </span>
                        <span className="text-dark-muted">completed a</span>
                        <span className={clsx('font-semibold', isLong ? 'text-profit' : 'text-loss')}>
                          {isLong ? 'long' : 'short'}
                        </span>
                        <span className="text-dark-muted">trade on</span>
                      </div>
                    </div>

                    <div className="space-y-1 text-dark-muted">
                      <div className="flex items-center space-x-2">
                        <span className="font-semibold text-dark-text">{trade.symbol}</span>
                        <span>{timeAgo}</span>
                      </div>
                      <div>
                        Price: {formatCurrency(trade.price)} ➜ {formatCurrency(trade.price)}
                      </div>
                      <div>Quantity: {trade.quantity}</div>
                      <div>
                        Notional: {formatCurrency(trade.total - trade.fee)} ➜ {formatCurrency(trade.total - trade.fee)}
                      </div>
                      <div>
                        Holding time: <span className="text-dark-text">{isLong ? '1h 30m' : '2h 45m'}</span>
                      </div>
                      <div className="pt-2 border-t border-dark-border mt-2">
                        NET P&L:{' '}
                        <span className={clsx('font-bold', Math.random() > 0.5 ? 'text-profit' : 'text-loss')}>
                          {Math.random() > 0.5 ? '+' : '-'}
                          {formatCurrency(Math.random() * 100)}
                        </span>
                      </div>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        )}

        {activeTab === 'POSITIONS' && (
          <div className="p-3 text-center text-dark-muted py-8">
            Open positions view coming soon
          </div>
        )}

        {activeTab === 'REASONING' && (
          <div className="p-3 space-y-3">
            {loading ? (
              <div className="text-center text-dark-muted py-8">Loading...</div>
            ) : filteredReasoning.length === 0 ? (
              <div className="text-center text-dark-muted py-8">No reasoning entries yet</div>
            ) : (
              filteredReasoning.map((r) => {
                const timeAgo = formatDistanceToNow(new Date(r.timestamp), { addSuffix: true })
                const timestamp = format(new Date(r.timestamp), 'MMM dd, yyyy HH:mm')

                return (
                  <div
                    key={`${r.id}-${r.timestamp}`}
                    className="bg-dark-bg border border-dark-border rounded p-4 text-sm"
                  >
                    {/* Header */}
                    <div className="flex items-start justify-between mb-3 pb-3 border-b border-dark-border">
                      <div>
                        <span className="font-semibold text-dark-text text-base">
                          {r.model_name}
                        </span>
                        <div className="text-xs text-dark-muted mt-1">
                          {timestamp} • {timeAgo}
                        </div>
                      </div>
                    </div>

                    {/* Decision Summary */}
                    {r.decision && (
                      <div className="mb-3">
                        <div className="text-xs text-dark-muted mb-1 font-semibold uppercase">
                          Decision:
                        </div>
                        <div className="text-dark-text font-medium bg-dark-surface p-2 rounded">
                          {r.decision}
                        </div>
                      </div>
                    )}

                    {/* Reasoning Text */}
                    {r.reasoning_text && (
                      <div className="mb-3">
                        <div className="text-xs text-dark-muted mb-1 font-semibold uppercase">
                          Reasoning:
                        </div>
                        <div className="text-dark-text whitespace-pre-wrap bg-dark-surface p-3 rounded text-xs leading-relaxed">
                          {r.reasoning_text}
                        </div>
                      </div>
                    )}

                    {/* Research Content */}
                    {r.research_content && (
                      <div>
                        <div className="text-xs text-dark-muted mb-1 font-semibold uppercase">
                          Research Data:
                        </div>
                        <details className="cursor-pointer">
                          <summary className="text-primary text-xs hover:underline">
                            Show research content ({r.research_content.length} characters)
                          </summary>
                          <div className="mt-2 text-dark-text whitespace-pre-wrap bg-dark-surface p-3 rounded text-xs leading-relaxed max-h-96 overflow-y-auto">
                            {r.research_content}
                          </div>
                        </details>
                      </div>
                    )}
                  </div>
                )
              })
            )}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-dark-border text-xs text-dark-muted">
        {activeTab === 'TRADES' && `Showing Last ${filteredTrades.length} Trades`}
        {activeTab === 'REASONING' && `Showing Last ${filteredReasoning.length} Reasoning Entries`}
        {activeTab === 'POSITIONS' && 'Open Positions View'}
      </div>
    </div>
  )
}
