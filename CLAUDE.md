# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Sentiment Arena is an AI-powered stock trading competition where multiple LLM models compete against each other in swing trading German stocks (XETRA/DAX) using real market data. Each model starts with €1,000 and makes autonomous trading decisions based on market research, news analysis, and technical indicators.

## Architecture

### Backend (Python/FastAPI)
- **FastAPI** REST API and WebSocket server for real-time updates
- **SQLAlchemy** ORM with PostgreSQL/SQLite for persistence
- **OpenRouter API** for accessing multiple LLM models (GPT-4, Claude, Gemini, etc.)
- **yfinance** for German stock market data
- **APScheduler** for automated trading schedules (pre-market and 2 PM CET)

### Frontend (React/TypeScript)
- **React** with TypeScript for type-safe UI development
- **TailwindCSS** for styling
- **Chart.js/Recharts** for performance visualizations
- **WebSocket client** for live portfolio and trade updates

### Key Services

#### Trading Engine (`backend/services/trading_engine.py`)
- Paper trading simulation with realistic market conditions
- Order validation and execution (market orders only initially)
- Position management (opening, averaging, closing positions)
- Portfolio valuation and P&L calculation
- €5 flat fee per trade (matching Flatex structure)
- Market hours enforcement (9:00 AM - 5:30 PM CET, weekdays only)

#### LLM Agent (`backend/services/llm_agent.py`)
- Orchestrates each model's trading decisions
- Performs internet research for news and sentiment (1-2 searches per session)
- Formats market data, portfolio state, and research findings into prompts
- Parses LLM JSON responses for trading decisions
- Stores model reasoning in database for transparency

#### Market Data (`backend/services/market_data.py`)
- Fetches real-time German stock prices via yfinance
- Validates XETRA symbols
- Caching to avoid rate limits
- Market hours and trading day validation

#### Research System (`backend/services/research.py`, `rss_news_fetcher.py`, `market_momentum.py`)
- **RSS feed integration** for all 40 DAX stocks (Yahoo Finance, Reuters, MarketWatch, Seeking Alpha)
- **Market momentum scoring** - Tracks news volume per stock (24-hour window)
- **Dynamic stock discovery** - Identifies trending stocks beyond current positions
- **Smart selection** - Researches 10 most relevant stocks (positions + trending)
- **News aggregation** - Combines RSS + Finnhub + Alpha Vantage news
- **Web search fallback** - DuckDuckGo with retry logic when RSS unavailable
- **Deduplication and ranking** - Removes duplicates, ranks by relevance and recency

#### Market Momentum System (`backend/services/market_momentum.py`)
- Monitors all 40 DAX stocks via RSS feeds
- Calculates news momentum score (0-100) based on article volume
- Identifies trending stocks (high news activity = potential opportunities)
- Smart stock selection algorithm:
  - Current positions (top 5 by value)
  - Trending stocks (top 5 by news momentum)
  - Total: ~10 stocks researched per session
- Enables dynamic response to market events
- Example: If BMW announces major partnership (50 articles), models will research it

**Why this matters:**
- Static 3-stock research misses opportunities
- Dynamic discovery responds to real market movements
- Models compete on information quality, not just list position

#### Scheduler (`backend/services/scheduler.py`)
- Pre-market research trigger (before 9:00 AM CET)
- Afternoon research trigger (2:00 PM CET)
- Position value updates during market hours
- End-of-day portfolio snapshots
- German market holiday awareness

### Database Schema

**Models Table**: LLM model configurations (name, api_identifier, starting_balance)
**Portfolios Table**: Current state (model_id, current_balance, total_pl)
**Positions Table**: Open positions (model_id, symbol, quantity, avg_price, unrealized_pl)
**Trades Table**: Full trade history (model_id, symbol, side, quantity, price, fee, timestamp, status)
**Reasoning Table**: Model decision logs (model_id, timestamp, research_content, decision, reasoning_text)
**Market Data Cache**: Price cache (symbol, price, timestamp, volume)

## Development Setup

### Backend
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python -m alembic upgrade head

# Run development server
cd backend
uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Environment Configuration
Copy `.env.example` to `.env` and configure:
- `OPENROUTER_API_KEY`: Your OpenRouter API key
- `DATABASE_URL`: PostgreSQL connection string
- `STARTING_CAPITAL`: Starting balance per model (default: 1000)
- `TRADING_FEE`: Fee per trade in euros (default: 5)
- `ACTIVE_MODELS`: Comma-separated list of OpenRouter model identifiers
- Market hours configuration (CET timezone)

## Trading Rules & Constraints

- Starting capital: €1,000 per model
- Trading fee: €5 per trade (buy or sell)
- Market: German stocks only (XETRA/DAX symbols)
- Market hours: 9:00 AM - 5:30 PM CET (Monday-Friday)
- No short selling
- No leverage
- Swing trading strategy (positions held multiple days)
- Research occurs twice daily: pre-market and 2 PM CET

## API Endpoints

- `GET /api/models` - List all competing models with basic stats
- `GET /api/models/{model_id}/portfolio` - Current portfolio (balance + positions)
- `GET /api/models/{model_id}/positions` - Open positions
- `GET /api/models/{model_id}/trades` - Trade history (paginated)
- `GET /api/models/{model_id}/performance` - Performance metrics (P&L, win rate, ROI)
- `GET /api/models/{model_id}/reasoning` - Latest model reasoning/decisions
- `GET /api/leaderboard` - Models ranked by performance
- `WS /ws/live` - WebSocket for real-time updates (positions, trades, reasoning)

## Key Implementation Notes

### Research Pipeline
- **Stage 1: Market Monitoring** - RSS feeds track all 40 DAX stocks continuously
- **Stage 2: Momentum Scoring** - Calculate news volume per stock (last 24 hours)
- **Stage 3: Stock Selection** - Choose 10 most relevant (positions + trending)
- **Stage 4: Complete Research** - Technical + Fundamental + News analysis for selected stocks
- **Stage 5: LLM Synthesis** - Enhanced research pipeline with quality verification
- **Stage 6: Trading Decision** - LLM receives full context including market momentum

### LLM Prompt Design
Prompts should include:
- Current portfolio state (cash, positions, total value)
- Market data for relevant stocks
- Research findings (news, sentiment)
- **Market momentum summary** - Trending stocks and article counts
- Trading rules and constraints
- Expected JSON response format

### Position Calculations
- Average price when adding to positions: `(old_avg * old_qty + new_price * new_qty) / (old_qty + new_qty)`
- Unrealized P&L: `(current_price - avg_price) * quantity`
- Realized P&L: Calculated on position close, includes trading fees

### Market Hours Enforcement
All trades must be validated against:
- Current time in CET timezone
- Market open hours (9:00 AM - 5:30 PM)
- Trading days (weekdays only)
- German market holidays

### Real-time Updates
WebSocket broadcasts:
- Position value updates (during market hours)
- Trade executions (immediate)
- Model reasoning entries (when research completes)
- Portfolio performance changes

## Implementation Phases

The project follows a phased approach (see TASKS.md for detailed breakdown):
1. **Phase 1**: Project setup, database schema, configuration
2. **Phase 2**: Market data integration and paper trading engine
3. **Phase 3**: LLM agent system with OpenRouter and research
4. **Phase 4**: Scheduling and automation
5. **Phase 5**: Backend API (REST + WebSocket)
6. **Phase 6**: Frontend UI (dashboard, positions, trade history, charts)
7. **Phase 7**: Testing (unit, integration, E2E)
8. **Phase 8**: Documentation and deployment
9. **Phase 9**: Future enhancements

## Quick Start MVP

For rapid initial development, focus on:
1. Basic database models and migrations
2. Market data service (price fetching only)
3. Simple paper trading engine (market orders)
4. OpenRouter integration
5. Basic LLM agent with hardcoded prompt
6. Minimal FastAPI with essential endpoints
7. Simple frontend showing positions

This creates a working prototype before iterating on advanced features.
