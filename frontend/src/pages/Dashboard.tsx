import { useEffect, useState } from 'react'
import { getModels } from '../services/api'
import { PortfolioChart } from '../components/PortfolioChart'
import { ModelCard } from '../components/ModelCard'
import { TradeHistory } from '../components/TradeHistory'
import type { Model } from '../types'
import wsClient from '../services/websocket'

export function Dashboard() {
  const [models, setModels] = useState<Model[]>([])
  const [selectedModels, setSelectedModels] = useState<number[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadModels = async () => {
      try {
        const data = await getModels()
        setModels(data)
        // Select all models by default
        setSelectedModels(data.map(m => m.id))
      } catch (error) {
        console.error('Failed to load models:', error)
      } finally {
        setLoading(false)
      }
    }

    loadModels()

    // Connect WebSocket
    wsClient.connect()

    // Subscribe to updates
    const unsubscribe = wsClient.subscribe((message) => {
      if (message.type === 'portfolio_update') {
        // Refresh models when portfolio updates
        loadModels()
      }
    })

    return () => {
      unsubscribe()
    }
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-dark-muted">Loading...</div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Side: Chart */}
        <div className="flex-1 flex flex-col p-4">
          <div className="flex-1 card">
            <PortfolioChart models={models} selectedModels={selectedModels} />
          </div>

          {/* Model Performance Cards */}
          <div className="mt-4 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-3">
            {models.map((model) => (
              <ModelCard
                key={model.id}
                model={model}
                isSelected={selectedModels.includes(model.id)}
                onToggle={(id) => {
                  setSelectedModels((prev) =>
                    prev.includes(id)
                      ? prev.filter((mid) => mid !== id)
                      : [...prev, id]
                  )
                }}
              />
            ))}
          </div>
        </div>

        {/* Right Side: Trade History */}
        <div className="w-96 border-l border-dark-border">
          <TradeHistory />
        </div>
      </div>
    </div>
  )
}
