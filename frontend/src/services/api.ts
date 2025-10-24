import axios from 'axios'
import type {
  Model,
  Portfolio,
  Position,
  Trade,
  Performance,
  Reasoning,
  MarketStatus,
  LeaderboardEntry,
} from '../types'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// System endpoints
export const getHealth = async () => {
  const response = await api.get('/health')
  return response.data
}

// Model endpoints
export const getModels = async (): Promise<Model[]> => {
  const response = await api.get('/api/models')
  return response.data
}

export const getPortfolio = async (modelId: number): Promise<Portfolio> => {
  const response = await api.get(`/api/models/${modelId}/portfolio`)
  return response.data
}

export const getPositions = async (modelId: number): Promise<Position[]> => {
  const response = await api.get(`/api/models/${modelId}/positions`)
  return response.data
}

export const getTrades = async (
  modelId: number,
  skip = 0,
  limit = 50
): Promise<{ total: number; skip: number; limit: number; trades: Trade[] }> => {
  const response = await api.get(`/api/models/${modelId}/trades`, {
    params: { skip, limit },
  })
  return response.data
}

export const getPerformance = async (modelId: number): Promise<Performance> => {
  const response = await api.get(`/api/models/${modelId}/performance`)
  return response.data
}

export const getReasoning = async (modelId: number, limit = 10): Promise<Reasoning[]> => {
  const response = await api.get(`/api/models/${modelId}/reasoning`, {
    params: { limit },
  })
  return response.data
}

// Leaderboard endpoint
export const getLeaderboard = async (): Promise<LeaderboardEntry[]> => {
  const response = await api.get('/api/leaderboard')
  return response.data
}

// Market status endpoint
export const getMarketStatus = async (): Promise<MarketStatus> => {
  const response = await api.get('/api/market/status')
  return response.data
}

// Admin endpoints
export const triggerResearch = async (jobName?: string) => {
  const response = await api.post('/api/admin/trigger-research', null, {
    params: jobName ? { job_name: jobName } : {},
  })
  return response.data
}

export default api
