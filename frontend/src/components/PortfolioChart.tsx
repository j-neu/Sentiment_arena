import { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import type { Model } from '../types'

interface PortfolioChartProps {
  models: Model[]
  selectedModels: number[]
}

const MODEL_COLORS = [
  '#3b82f6', // blue
  '#8b5cf6', // purple
  '#ec4899', // pink
  '#ef4444', // red
  '#f59e0b', // orange
  '#10b981', // green
  '#06b6d4', // cyan
  '#6366f1', // indigo
]

export function PortfolioChart({ models, selectedModels }: PortfolioChartProps) {
  const [timeRange, setTimeRange] = useState<'ALL' | '72H'>('ALL')
  const [chartData, setChartData] = useState<any[]>([])

  useEffect(() => {
    // For now, we'll create mock historical data
    // In a real implementation, you'd fetch this from an API endpoint
    const generateMockData = () => {
      const data = []
      const now = new Date()
      const points = 20

      for (let i = points; i >= 0; i--) {
        const timestamp = new Date(now.getTime() - i * 3600000) // 1 hour intervals
        const point: any = {
          time: timestamp.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
        }

        models.forEach((model) => {
          if (selectedModels.includes(model.id)) {
            // Simulate portfolio value over time
            const variance = (Math.random() - 0.5) * 50
            point[`model_${model.id}`] = model.total_value + variance
          }
        })

        data.push(point)
      }

      return data
    }

    setChartData(generateMockData())
  }, [models, selectedModels])

  const selectedModelData = models.filter((m) => selectedModels.includes(m.id))

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold">TOTAL ACCOUNT VALUE</h2>
        <div className="flex space-x-2">
          <button
            onClick={() => setTimeRange('ALL')}
            className={`px-3 py-1 text-sm rounded ${
              timeRange === 'ALL'
                ? 'bg-primary text-white'
                : 'bg-dark-border text-dark-muted'
            }`}
          >
            ALL
          </button>
          <button
            onClick={() => setTimeRange('72H')}
            className={`px-3 py-1 text-sm rounded ${
              timeRange === '72H'
                ? 'bg-primary text-white'
                : 'bg-dark-border text-dark-muted'
            }`}
          >
            72H
          </button>
        </div>
      </div>

      <div className="flex-1">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2a2a2a" />
            <XAxis
              dataKey="time"
              stroke="#888888"
              style={{ fontSize: '12px' }}
            />
            <YAxis
              stroke="#888888"
              style={{ fontSize: '12px' }}
              tickFormatter={(value) => `€${(value / 1000).toFixed(1)}k`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1a1a1a',
                border: '1px solid #2a2a2a',
                borderRadius: '8px',
              }}
              formatter={(value: number) =>
                new Intl.NumberFormat('de-DE', {
                  style: 'currency',
                  currency: 'EUR',
                }).format(value)
              }
            />
            <Legend />
            {selectedModelData.map((model, index) => (
              <Line
                key={model.id}
                type="monotone"
                dataKey={`model_${model.id}`}
                name={model.name}
                stroke={MODEL_COLORS[index % MODEL_COLORS.length]}
                strokeWidth={2}
                dot={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
