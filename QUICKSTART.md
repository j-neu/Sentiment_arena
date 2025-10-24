# Sentiment Arena - Quick Start Guide

Get the AI trading competition running in 5 minutes!

---

## Prerequisites

- **Python 3.11+** installed
- **Node.js 18+** installed
- **Git** (optional)

---

## Option 1: Automated Start (Windows)

### One-Click Startup

Simply double-click: **`start_all.bat`**

This will:
1. Check and initialize the database
2. Create demo trading models
3. Start the backend API server
4. Start the frontend web app

**Access the app:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## Option 2: Manual Setup

### Step 1: Install Backend Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

### Step 2: Initialize Database

```bash
# Run database migrations
python backend/database/init_db.py

# Create demo models
python scripts/init_demo_data.py
```

### Step 3: Install Frontend Dependencies

```bash
cd frontend
npm install
```

### Step 4: Configure Environment

Create `.env` files (or copy from `.env.example`):

**Backend `.env`:**
```bash
# Required for trading functionality
OPENROUTER_API_KEY=your_key_here

# Optional - for enhanced research
ALPHAVANTAGE_API_KEY=your_key_here
FINNHUB_API_KEY=your_key_here

# Database
DATABASE_URL=sqlite:///./sentiment_arena.db

# Market configuration
STARTING_CAPITAL=1000.0
TRADING_FEE=5.0
```

**Frontend `.env`:**
```bash
VITE_API_URL=http://localhost:8000
VITE_WS_PORT=8000
```

### Step 5: Start the Servers

**Terminal 1 - Backend:**
```bash
# Windows
venv\Scripts\activate
python -m uvicorn backend.main:app --reload --port 8000

# Linux/Mac
source venv/bin/activate
python -m uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

---

## Verify Installation

### 1. Check Backend
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "components": {
    "database": "connected",
    "scheduler": "stopped",
    "websocket": "active"
  }
}
```

### 2. Check Models
```bash
curl http://localhost:8000/api/models
```

Should return 6 demo models (GPT-4, Claude, Gemini, etc.)

### 3. Check Frontend

Open browser: **http://localhost:3000**

You should see:
- Dashboard with portfolio chart
- Model performance cards
- Trade history panel
- Navigation bar

---

## Trigger a Trading Session

### Option 1: Manual Trigger (API)

```bash
curl -X POST http://localhost:8000/api/admin/trigger-research?job_name=pre_market_research
```

This will:
1. All models perform research on German stocks
2. Generate trading decisions
3. Execute trades (if market is open)
4. Display results in real-time on frontend

### Option 2: Automated Schedule

The scheduler runs automatically:
- **8:30 AM CET** - Pre-market research
- **2:00 PM CET** - Afternoon research
- **Every 15 min** - Position value updates (during market hours)
- **5:35 PM CET** - End-of-day snapshot

To enable scheduler on startup, it's already running when backend starts!

---

## Project Structure

```
sentiment_arena/
├── backend/              # Python FastAPI backend
│   ├── api/             # REST API routes
│   ├── models/          # Database models
│   ├── services/        # Trading engine, LLM, market data
│   └── main.py          # FastAPI app
├── frontend/            # React frontend
│   ├── src/
│   │   ├── components/  # UI components
│   │   ├── pages/       # Dashboard, Leaderboard, Models
│   │   └── services/    # API client, WebSocket
│   └── package.json
├── scripts/             # Utility scripts
├── tests/               # Unit tests
├── start_all.bat        # One-click startup (Windows)
├── start_backend.bat    # Backend only
└── start_frontend.bat   # Frontend only
```

---

## Common Issues

### Port Already in Use

**Error:** `Address already in use`

**Solution:**
```bash
# Windows - Kill process on port 8000
netstat -ano | findstr :8000
taskkill /PID <pid> /F

# Linux/Mac
lsof -ti:8000 | xargs kill -9
```

### Database Locked

**Error:** `database is locked`

**Solution:**
- Stop all backend processes
- Delete `sentiment_arena.db`
- Re-run `python backend/database/init_db.py`
- Re-run `python scripts/init_demo_data.py`

### Frontend Build Errors

**Error:** Module not found or compilation errors

**Solution:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### API Connection Failed

**Error:** Frontend can't connect to backend

**Solution:**
1. Verify backend is running: `curl http://localhost:8000/health`
2. Check CORS settings in `backend/config.py`
3. Verify `CORS_ORIGINS` includes `http://localhost:3000`

---

## Next Steps

### 1. Add Real API Keys

Edit `.env` and add your OpenRouter API key:
```bash
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxx
```

Get a key at: https://openrouter.ai/

### 2. Configure Active Models

Edit `.env` to choose which models compete:
```bash
ACTIVE_MODELS=openai/gpt-4-turbo,anthropic/claude-3-opus-20240229
```

### 3. Customize Trading Strategy

Edit prompt templates in `backend/prompts/`:
- `trading_prompt.txt` - Default strategy
- `conservative_prompt.txt` - Risk-averse strategy
- Create your own custom strategies

### 4. Monitor the Competition

- **Dashboard** - Live portfolio values and trades
- **Leaderboard** - Rankings by performance
- **Models** - Detailed metrics per model
- **API Docs** - http://localhost:8000/docs

### 5. Run Real Trading

Set market hours in `.env`:
```bash
MARKET_OPEN_HOUR=9
MARKET_CLOSE_HOUR=17
MARKET_CLOSE_MINUTE=30
TIMEZONE=Europe/Berlin
```

The scheduler will automatically trade during German market hours!

---

## Key Features

✅ **6 AI Models** competing with €1,000 each
✅ **Real-time Dashboard** with live updates
✅ **Automated Trading** twice daily (8:30 AM, 2 PM CET)
✅ **German Stocks** (XETRA/DAX)
✅ **Paper Trading** (no real money)
✅ **Research Pipeline** with LLM-powered analysis
✅ **Technical Analysis** (RSI, MACD, Bollinger Bands, etc.)
✅ **Financial APIs** (Alpha Vantage, Finnhub)
✅ **Performance Tracking** (P&L, win rate, ROI)
✅ **WebSocket Updates** for real-time data

---

## Documentation

- **README.md** - Project overview
- **CLAUDE.md** - Architecture and design
- **TASKS.md** - Implementation roadmap
- **PHASE_X_COMPLETE.md** - Detailed phase documentation
- **API Docs** - http://localhost:8000/docs (when running)

---

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the phase completion docs (PHASE_1-6_COMPLETE.md)
3. Check backend logs for errors
4. Check browser console for frontend errors

---

## What's Next?

After getting familiar with the app:

1. **Phase 7** - Add comprehensive testing
2. **Phase 8** - Deploy to production
3. **Phase 9** - Advanced features (limit orders, backtesting, etc.)

---

**Happy Trading! 🚀📈**

*Built with Python, FastAPI, React, TypeScript, and AI magic*
