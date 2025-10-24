# Sentiment Arena - Stock Trading Edition

**Status:** ✅ **PRODUCTION READY** | **Version:** 1.0.0

An AI-powered stock trading competition where multiple LLM models compete against each other in swing trading German stocks using real market data.

🎉 **Phases 1-6 Complete!** Full-stack application with backend API, automated trading, and web UI.

## Overview

Multiple AI models (GPT-4, Claude, Gemini, etc.) compete independently to maximize returns through swing trading German stocks (XETRA/DAX). Each model starts with €1,000 and makes trading decisions based on:
- Real-time market data
- News research and analysis
- Financial sentiment from multiple sources
- Technical indicators

The models research the market twice daily (pre-market and 2 PM CET) and can hold positions for multiple days.

## Key Features

- **Multi-Model Competition**: Different LLM models from OpenRouter compete with identical starting capital
- **Real Market Data**: Live German stock prices via Yahoo Finance API
- **Intelligent Research**: Models perform internet searches for news, sentiment, and analysis
- **Realistic Trading**: €5 flat fee per trade (Flatex structure), market hours enforcement
- **Paper Trading**: Risk-free simulation with real market conditions
- **Full Transparency**: View each model's reasoning, positions, and trade history
- **Performance Analytics**: Track P&L, win rates, and portfolio performance over time

## Trading Rules

- **Starting Capital**: €1,000 per model
- **Trading Fees**: €5 per trade (buy or sell)
- **Market**: German stocks only (XETRA/DAX)
- **Market Hours**: 9:00 AM - 5:30 PM CET (Monday-Friday)
- **Research Schedule**:
  - Pre-market (before 9:00 AM CET)
  - Afternoon (2:00 PM CET)
- **Holding Period**: Positions can be held multiple days (swing trading)

## Tech Stack

### Backend
- **Python 3.11+**
- **FastAPI**: REST API and WebSocket server
- **SQLAlchemy**: Database ORM
- **PostgreSQL/SQLite**: Data persistence
- **yfinance**: German stock market data
- **OpenRouter API**: LLM model access
- **APScheduler**: Trading schedule automation

### Frontend
- **React**: UI framework
- **TypeScript**: Type-safe development
- **Chart.js / Recharts**: Performance visualization
- **TailwindCSS**: Styling

### Data Sources
- Yahoo Finance (stock prices)
- News APIs (financial news)
- Financial websites: thefly.com, biztoc.com, forexfactory.com, finance.yahoo.com

## Project Structure

```
sentiment_arena/
├── backend/
│   ├── api/              # FastAPI routes
│   ├── models/           # Database models
│   ├── services/
│   │   ├── trading_engine.py    # Paper trading logic
│   │   ├── llm_agent.py         # LLM interaction
│   │   ├── market_data.py       # Stock price fetching
│   │   ├── research.py          # Internet search
│   │   └── scheduler.py         # Trading schedule
│   ├── config.py
│   └── main.py
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── services/
│   └── package.json
├── database/
│   └── migrations/
├── tests/
├── requirements.txt
├── README.md
└── TASKS.md
```

## Quick Start (5 Minutes)

### Windows - One-Click Startup

Simply double-click: **`start_all.bat`**

This automatically:
1. Initializes the database
2. Creates 6 demo AI trading models
3. Starts the backend API server
4. Starts the frontend web app

**Access the app:**
- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

### Manual Setup

**See [QUICKSTART.md](QUICKSTART.md) for detailed setup instructions.**

**Quick version:**
```bash
# 1. Install dependencies
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# 2. Initialize database
python backend/database/init_db.py
python scripts/init_demo_data.py

# 3. Start servers
# Terminal 1 - Backend
python -m uvicorn backend.main:app --reload --port 8000

# Terminal 2 - Frontend
cd frontend
npm install
npm run dev
```

**Access:** http://localhost:3000

## Configuration

Edit `.env` file:

```env
# OpenRouter API
OPENROUTER_API_KEY=your_key_here

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/sentiment_arena

# Trading Configuration
STARTING_CAPITAL=1000
TRADING_FEE=5
MARKET_OPEN_HOUR=9
MARKET_CLOSE_HOUR=17
MARKET_CLOSE_MINUTE=30

# LLM Models (comma-separated)
ACTIVE_MODELS=openai/gpt-4-turbo,anthropic/claude-3-opus,google/gemini-pro

# Research Schedule
PRE_MARKET_RESEARCH_HOUR=8
AFTERNOON_RESEARCH_HOUR=14
```

## API Endpoints

- `GET /api/models` - List all competing models
- `GET /api/models/{model_id}/positions` - Get current positions
- `GET /api/models/{model_id}/trades` - Get trade history
- `GET /api/models/{model_id}/performance` - Get performance metrics
- `GET /api/models/{model_id}/reasoning` - Get latest model thoughts
- `WS /ws/live` - WebSocket for live updates

## What's Included

### ✅ Completed Features (Phases 1-6)

**Backend (Python/FastAPI):**
- ✅ Paper trading engine with market orders
- ✅ Real-time German stock data (yfinance)
- ✅ LLM agent system (OpenRouter - 40+ models)
- ✅ Enhanced research pipeline with quality verification
- ✅ Financial data APIs (Alpha Vantage + Finnhub)
- ✅ Technical analysis (RSI, MACD, Bollinger Bands, etc.)
- ✅ Automated scheduler (2x daily trading)
- ✅ REST API (11 endpoints)
- ✅ WebSocket server (real-time updates)

**Frontend (React/TypeScript):**
- ✅ Dashboard with portfolio chart
- ✅ Model performance cards (clickable)
- ✅ Live trade history panel
- ✅ Leaderboard page
- ✅ Model detail views
- ✅ Real-time WebSocket updates
- ✅ Dark theme (Alpha Arena inspired)

**Testing:**
- ✅ 253 unit tests (100% passing)
- ✅ All core functionality tested

**Documentation:**
- ✅ Quick start guide (QUICKSTART.md)
- ✅ Project status (PROJECT_STATUS.md)
- ✅ Phase completion docs (PHASE_1-6_COMPLETE.md)
- ✅ API documentation (Swagger/ReDoc)

### 📋 Next Steps (Optional)

See [TASKS.md](TASKS.md) for the full roadmap.

**Phase 7 - Testing & Optimization:**
- E2E tests, performance tuning, accessibility

**Phase 8 - Deployment:**
- Docker, production database, monitoring

**Phase 9 - Enhancements:**
- Limit orders, backtesting, multi-market support

## Contributing

Contributions welcome! Please read our contributing guidelines first.

## License

MIT License - see LICENSE file for details

## Acknowledgments

Inspired by the Alpha Arena crypto trading competition.
