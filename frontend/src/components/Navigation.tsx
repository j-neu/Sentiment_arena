import { Link, useLocation } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { getMarketStatus } from '../services/api'
import type { MarketStatus } from '../types'

export function Navigation() {
  const location = useLocation()
  const [marketStatus, setMarketStatus] = useState<MarketStatus | null>(null)

  useEffect(() => {
    const loadMarketStatus = async () => {
      try {
        const status = await getMarketStatus()
        setMarketStatus(status)
      } catch (error) {
        console.error('Failed to load market status:', error)
      }
    }

    loadMarketStatus()
    const interval = setInterval(loadMarketStatus, 60000) // Refresh every minute
    return () => clearInterval(interval)
  }, [])

  const isActive = (path: string) => location.pathname === path

  return (
    <nav className="bg-dark-surface border-b border-dark-border">
      <div className="flex items-center justify-between px-6">
        <div className="flex space-x-1">
          <Link
            to="/"
            className={`nav-link ${isActive('/') ? 'nav-link-active' : ''}`}
          >
            LIVE
          </Link>
          <Link
            to="/leaderboard"
            className={`nav-link ${isActive('/leaderboard') ? 'nav-link-active' : ''}`}
          >
            LEADERBOARD
          </Link>
          <Link
            to="/models"
            className={`nav-link ${isActive('/models') ? 'nav-link-active' : ''}`}
          >
            MODELS
          </Link>
        </div>

        <div className="flex items-center space-x-4 py-2">
          {marketStatus && (
            <div className="flex items-center space-x-2">
              <div
                className={`w-2 h-2 rounded-full ${
                  marketStatus.is_open ? 'bg-profit animate-pulse' : 'bg-loss'
                }`}
              />
              <span className="text-xs text-dark-muted">
                Market {marketStatus.is_open ? 'OPEN' : 'CLOSED'}
              </span>
            </div>
          )}
        </div>
      </div>
    </nav>
  )
}
