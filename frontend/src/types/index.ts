// Type definitions for Sentiment Arena

export interface Model {
  id: number
  name: string
  api_identifier: string
  starting_balance: number
  current_balance: number
  total_value: number
  total_pl: number
  num_positions: number
  num_trades: number
  created_at: string
}

export interface Position {
  id: number
  symbol: string
  quantity: number
  avg_price: number
  current_price: number
  unrealized_pl: number
  unrealized_pl_pct: number
  position_value: number
  opened_at: string
  updated_at: string
}

export interface Trade {
  id: number
  symbol: string
  side: 'BUY' | 'SELL'
  quantity: number
  price: number
  fee: number
  total: number
  status: string
  timestamp: string
}

export interface Portfolio {
  model_id: number
  model_name: string
  current_balance: number
  total_value: number
  total_pl: number
  total_pl_pct: number
  realized_pl: number
  num_positions: number
  positions: Position[]
}

export interface Performance {
  model_id: number
  model_name: string
  starting_balance: number
  current_balance: number
  total_value: number
  total_pl: number
  total_pl_pct: number
  realized_pl: number
  unrealized_pl: number
  total_trades: number
  winning_trades: number
  losing_trades: number
  win_rate: number
  total_fees_paid: number
  num_positions: number
  roi: number
}

export interface Reasoning {
  id: number
  timestamp: string
  decision: string
  reasoning_text: string
  research_content: string
  confidence: string
  raw_response: string
}

export interface MarketStatus {
  is_open: boolean
  is_trading_day: boolean
  current_time_cet: string
  market_hours: {
    open: string
    close: string
  }
  trading_days: string
}

export interface LeaderboardEntry {
  rank: number
  model_id: number
  model_name: string
  api_identifier: string
  total_value: number
  total_pl: number
  total_pl_pct: number
  realized_pl: number
  current_balance: number
  num_positions: number
  num_trades: number
}

// WebSocket message types
export interface WSMessage {
  type: 'connected' | 'position_update' | 'trade' | 'reasoning' | 'portfolio_update' | 'scheduler_event' | 'pong'
  timestamp?: string
  [key: string]: any
}

export interface WSPositionUpdate extends WSMessage {
  type: 'position_update'
  model_id: number
  symbol: string
  current_price: number
  unrealized_pl: number
}

export interface WSTrade extends WSMessage {
  type: 'trade'
  model_id: number
  trade_id: number
  symbol: string
  side: 'BUY' | 'SELL'
  quantity: number
  price: number
  fee: number
}

export interface WSReasoning extends WSMessage {
  type: 'reasoning'
  model_id: number
  reasoning_id: number
  decision: string
  confidence: string
}

export interface WSPortfolioUpdate extends WSMessage {
  type: 'portfolio_update'
  model_id: number
  current_balance: number
  total_value: number
  total_pl: number
}
