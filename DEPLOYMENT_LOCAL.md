# Local Deployment Guide - 1 Week Test

**Purpose:** Run Sentiment Arena on your local Windows PC for 1 week to evaluate trading performance.

---

## Overview

You have two deployment options:

1. **Persistent Backend (Recommended)** - Backend runs 24/7, automatically trades 2x per day
2. **Manual Trading** - You manually run trading sessions whenever you want

---

## Option 1: Persistent Backend (Recommended)

### How It Works

- Backend runs continuously in the background
- Automatically triggers trading at **8:30 AM CET** and **2:00 PM CET**
- Updates positions every 15 minutes during market hours
- Auto-restarts if it crashes
- Frontend runs on-demand when you want to view results

### Setup

**Step 1: Start the persistent backend**

Double-click: **`run_backend_persistent.bat`**

Or from command line:
```bash
run_backend_persistent.bat
```

This will:
- Start the backend on http://localhost:8000
- Show a console window with logs
- Keep running until you close the window
- Auto-restart if the backend crashes

**Step 2: Start the frontend (when you want to view results)**

Double-click: **`start_frontend.bat`**

Or from command line:
```bash
cd frontend
npm run dev
```

Access the dashboard at: http://localhost:3000

### Keep It Running

**To keep backend running 24/7:**
1. Leave the console window open (don't close it!)
2. Minimize the window to system tray
3. Make sure your PC doesn't sleep (adjust power settings)

**Windows Power Settings:**
- Go to: Settings → System → Power & Sleep
- Set "When plugged in, PC goes to sleep after": **Never**
- Or use a tool like "Caffeine" to prevent sleep

**What happens if PC restarts?**
- You'll need to manually restart `run_backend_persistent.bat`
- Consider adding it to Windows Startup folder for auto-start:
  - Press `Win + R`, type `shell:startup`, press Enter
  - Create a shortcut to `run_backend_persistent.bat` in this folder

### Monitoring

**Check if backend is running:**
```bash
curl http://localhost:8000/health
```

**View logs:**
- Console window shows real-time logs
- Look for scheduled job execution at 8:30 AM and 2:00 PM

**Expected log output:**
```
[2025-10-24 08:30:00] Starting pre-market research job...
[2025-10-24 08:30:15] Model GPT-4 Turbo: Researching...
[2025-10-24 08:32:45] Model GPT-4 Turbo: Executed BUY 10 SAP.DE @ €150.50
...
```

---

## Option 2: Manual Trading Sessions

### How It Works

- Backend does NOT run automatically
- You manually trigger trading sessions at your convenience
- Good for testing or if you don't want backend running 24/7

### Usage

**Double-click:** `run_manual_trading.bat`

Or from command line:
```bash
# Default manual session
python scripts/manual_trading_session.py

# Morning session (8:30 AM recommended)
python scripts/manual_trading_session.py --job-name pre_market_research

# Afternoon session (2:00 PM recommended)
python scripts/manual_trading_session.py --job-name afternoon_research
```

### What It Does

1. Checks market status (open/closed, trading day)
2. Runs research for all models
3. Makes trading decisions
4. Executes trades (if market is open)
5. Stores results in database
6. Shows summary of trades executed

### Example Output

```
======================================================================
              SENTIMENT ARENA - MANUAL TRADING
======================================================================

Current Time (CET): 2025-10-24 08:30:15
Market Open: YES ✓
Trading Day: YES ✓

Job Type: pre_market_research
======================================================================

Found 6 models:
  - GPT-4 Turbo (openai/gpt-4-turbo)
  - Claude 3 Opus (anthropic/claude-3-opus-20240229)
  - Gemini Pro (google/gemini-pro)
  ...

[1/6] Processing GPT-4 Turbo...
----------------------------------------------------------------------
  → Running research and trading decision...
  ✓ Success!
  ✓ Executed 1 trades
     • BUY 10 SAP.DE @ €150.50

[2/6] Processing Claude 3 Opus...
----------------------------------------------------------------------
  → Running research and trading decision...
  ✓ Success!
  → No trades executed (decision: HOLD)

...

======================================================================
TRADING SESSION COMPLETE
======================================================================
Successful: 6/6
Failed: 0/6

Completed at: 2025-10-24 08:35:22 CET

✓ View results at: http://localhost:3000
✓ Check API at: http://localhost:8000/docs
```

### Recommended Schedule

For a proper 1-week test, run manually:
- **8:30 AM CET** - Morning session (pre-market research)
- **2:00 PM CET** - Afternoon session

Set reminders on your phone or use Windows Task Scheduler to remind you.

---

## Viewing Results

### Start the Frontend

```bash
cd frontend
npm run dev
```

Access at: http://localhost:3000

### What You'll See

- **Dashboard** - Portfolio performance chart for all models
- **Leaderboard** - Rankings by P&L
- **Models** - Detailed view per model (positions, performance, reasoning)
- **Trade History** - All trades with filters and CSV export

### API Endpoints

Backend API: http://localhost:8000
API Docs: http://localhost:8000/docs

Key endpoints:
- `GET /api/models` - List all models
- `GET /api/leaderboard` - Current rankings
- `GET /api/models/{id}/trades` - Trade history
- `GET /api/models/{id}/reasoning` - Model decisions

---

## Troubleshooting

### Backend won't start

**Error: "Virtual environment not found"**
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**Error: "Address already in use (port 8000)"**
```bash
# Find and kill process using port 8000
netstat -ano | findstr :8000
taskkill /PID <pid> /F
```

**Error: "Database is locked"**
- Stop all backend processes
- Close any database connections
- Restart backend

### Manual trading fails

**Error: "No models found"**
```bash
python scripts/init_demo_data.py
```

**Error: "API key not found"**
- Add `OPENROUTER_API_KEY=sk-or-v1-xxxxx` to `.env` file
- Restart backend

**Warning: "Market is closed"**
- Trading decisions are still made and stored
- Trades will execute when market opens
- Or you can test with mock data

### Frontend won't connect

**Error: "Cannot connect to backend"**
1. Verify backend is running: `curl http://localhost:8000/health`
2. Check frontend `.env` file has `VITE_API_URL=http://localhost:8000`
3. Restart frontend: `npm run dev`

---

## Data Storage

### Database Location

`sentiment_arena.db` (SQLite file in project root)

**Backup your data:**
```bash
# Copy database before testing
copy sentiment_arena.db sentiment_arena_backup.db

# Restore if needed
copy sentiment_arena_backup.db sentiment_arena.db
```

### Cache Location

`research_cache.json` (Research results cache)
- Automatically managed
- Reduces API costs by 75-90%
- Safe to delete if you want fresh research

### Logs

Backend logs are printed to console
- Consider redirecting to file for long-term monitoring:
```bash
python -m uvicorn backend.main:app --port 8000 > logs/backend.log 2>&1
```

---

## Cost Monitoring

### Expected Costs (1 Week)

**With caching:**
- Research: ~$0.72/month × 0.25 weeks = **~$0.18**
- Trading decisions: ~$3.20/month × 0.25 weeks = **~$0.80**
- **Total: ~$1.00 for 1 week**

**Without caching:**
- Total: ~$2.60 for 1 week

### API Usage

Monitor your OpenRouter usage at: https://openrouter.ai/usage

Check for:
- Total requests
- Cost per model
- Any errors or failures

---

## 1-Week Test Plan

### Day 0 (Setup Day)
- [ ] Run `run_backend_persistent.bat`
- [ ] Verify backend is healthy: http://localhost:8000/health
- [ ] Run initial manual session to test: `run_manual_trading.bat`
- [ ] Check frontend: http://localhost:3000
- [ ] Verify trades appear in UI

### Day 1-7 (Monitoring)
- [ ] Backend should run continuously (check once per day)
- [ ] View frontend each evening to check performance
- [ ] Watch for:
  - Trading sessions at 8:30 AM and 2:00 PM
  - Position updates during market hours
  - Model rankings changing over time
  - Any errors in backend console

### Day 7 (Evaluation)
- [ ] Export all trades to CSV (via frontend)
- [ ] Check leaderboard for winners
- [ ] Review model reasoning for best/worst performers
- [ ] Analyze:
  - Total P&L per model
  - Win rate (% profitable trades)
  - Best performing stock picks
  - Strategy differences between models

---

## Next Steps After 1 Week

### If results are good:
1. **Move to Raspberry Pi** for 24/7 operation
   - Lower power consumption
   - Dedicated device
   - Auto-restart on boot

2. **Add more models** to competition
3. **Refine trading strategies** based on results
4. **Deploy to cloud** for remote access

### If results need work:
1. **Adjust prompts** in `backend/prompts/`
2. **Modify trading parameters** in `.env`
3. **Test different model combinations**
4. **Analyze failure patterns** in reasoning logs

---

## Quick Reference

### Start Persistent Backend (24/7)
```bash
run_backend_persistent.bat
```

### Run Manual Trading Session
```bash
run_manual_trading.bat
```

### Start Frontend
```bash
start_frontend.bat
```

### Check Status
```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/models
```

### Stop Everything
- Close backend console window (Ctrl+C)
- Close frontend console window (Ctrl+C)

---

## Support

**Issues?**
1. Check console logs for errors
2. Review troubleshooting section above
3. Check API health endpoint
4. Restart services

**Need help?**
- Backend docs: http://localhost:8000/docs
- Project docs: See QUICKSTART.md, README.md
- Phase completion docs: PHASE_X_COMPLETE.md files

---

**Good luck with your 1-week test! 🚀📈**
