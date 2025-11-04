# Sentiment Arena - Testing Guide

## Overview

This guide provides a systematic approach to testing and debugging the Sentiment Arena trading system. Instead of running the full application and encountering many warnings and errors, we now test each component individually to identify and fix issues before integration.

## Testing Workflow

### Step 1: Quick Diagnostics
**Run:** `run_quick_diagnostics.bat`

**Purpose:** Identify the most common configuration and connectivity issues in under 30 seconds.

**Checks:**
- ✅ API key configuration (OpenRouter, Alpha Vantage, Finnhub)
- ✅ Database connectivity and model count
- ✅ OpenRouter API connectivity with test call
- ✅ Market data availability for German stocks
- ✅ Model configuration consistency between database and .env

**Expected Output:**
```
🎉 All checks passed! System appears to be configured correctly.
```

### Step 2: Comprehensive Component Testing
**Run:** `run_component_tests.bat`

**Purpose:** Test each system component individually to identify specific failures.

**Components Tested:**
1. **Database Connection** - Verify database operations
2. **Market Data Service** - Test German stock price fetching
3. **OpenRouter API** - Test LLM model access and responses
4. **Alpha Vantage API** - Test financial data availability
5. **Finnhub API** - Test news and sentiment data
6. **Web Search Service** - Test DuckDuckGo search and parsing
7. **Technical Analysis** - Test indicator calculations
8. **Trading Engine** - Test order execution and portfolio management
9. **Research Pipeline** - Test complete end-to-end research

**Expected Output:**
```
🎉 All tests passed! System is ready for trading.
```

### Step 3: Manual Trading Session
**Run:** `run_manual_trading.bat`

**Purpose:** Test the complete system with real trading decisions.

**Only run this after Steps 1 and 2 pass completely.**

## Common Issues and Solutions

### Issue 1: Alpha Vantage Returns No Data
**Symptoms:**
```
WARNING - No overview data found for SAP
WARNING - No RSI data found for SAP
WARNING - No MACD data found for SAP
```

**Causes:**
- Free tier rate limits (5 calls/minute)
- German stock symbol mapping issues
- API key problems

**Solutions:**
1. **Rate Limits:** Wait between calls, use caching
2. **Symbol Mapping:** Ensure German stocks use correct symbols (SAP, not SAP.DE)
3. **API Key:** Verify key is valid and has proper permissions

### Issue 2: Finnhub 403 Forbidden Errors
**Symptoms:**
```
ERROR - Request failed: 403 Client Error: Forbidden
```

**Causes:**
- API key lacks required permissions
- Free tier limitations
- Symbol not supported

**Solutions:**
1. **Check API Key:** Ensure key has sentiment and price target permissions
2. **Upgrade Plan:** Consider paid tier for better access
3. **Symbol Format:** Use correct format (SAP, not SAP.DE)

### Issue 3: Web Search Returns 0 Results
**Symptoms:**
```
WARNING - No results parsed on attempt 1/2/3
```

**Causes:**
- DuckDuckGo HTML structure changes
- Network connectivity issues
- Search query problems

**Solutions:**
1. **Updated Parsing:** Use multiple regex patterns (already fixed)
2. **Network Check:** Verify internet connectivity
3. **Query Testing:** Try simpler search terms

### Issue 4: Model Identifier Mismatch
**Symptoms:**
```
ERROR - 400 Client Error: Bad Request
```

**Causes:**
- Database models don't match .env configuration
- Outdated model identifiers
- API key lacks access to specific models

**Solutions:**
1. **Sync Configuration:** Ensure .env matches database models
2. **Update Identifiers:** Use current OpenRouter model names
3. **API Access:** Verify key has access to required models

### Issue 5: Research Synthesis Errors
**Symptoms:**
```
ERROR - 'str' object has no attribute 'get'
```

**Causes:**
- JSON parsing failures return strings instead of dictionaries
- Malformed LLM responses
- Missing error handling

**Solutions:**
1. **Robust Parsing:** Ensure fallback data structures (already fixed)
2. **JSON Validation:** Add proper JSON parsing with fallbacks
3. **Error Handling:** Graceful degradation for failed components

## Testing Individual Components

### Test Market Data Only
```python
from backend.services.market_data import MarketDataService
service = MarketDataService()
data = service.fetch_price('SAP.DE')
print(f"SAP Price: {data}")
```

### Test OpenRouter API Only
```python
from backend.services.openrouter_client import OpenRouterClient
client = OpenRouterClient()
response = client.get_completion_text(
    model="openai/gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello"}]
)
print(f"Response: {response}")
```

### Test Research Pipeline Only
```python
from backend.services.complete_research_orchestrator import CompleteResearchOrchestrator
orchestrator = CompleteResearchOrchestrator(...)
result = orchestrator.conduct_complete_research('SAP.DE', ...)
print(f"Research Success: {result['success']}")
```

## Quality Metrics

### Research Quality Benchmarks
- **Web Search:** Should return 3+ relevant articles per query
- **Alpha Vantage:** Should return data for 60%+ of German stocks
- **Finnhub:** Should return news for 80%+ of German stocks
- **Research Synthesis:** Should complete with HIGH/MEDIUM confidence
- **Total Research Time:** Should be under 120 seconds per stock

### API Performance Benchmarks
- **OpenRouter Response:** Should be under 30 seconds
- **Market Data Fetch:** Should be under 5 seconds
- **Web Search:** Should return results within 10 seconds
- **Database Queries:** Should be under 100ms

## Debugging Tips

### Enable Debug Logging
Edit `.env`:
```env
LOG_LEVEL=DEBUG
```

### Test Specific Models
```python
# Test only one model
from backend.services.llm_agent import LLMAgent
agent = LLMAgent(db, model_id=1, ...)
result = agent.make_trading_decision()
```

### Check Database State
```python
from backend.database.base import SessionLocal
db = SessionLocal()
models = db.query(Model).all()
for model in models:
    print(f"{model.name}: {model.api_identifier}")
```

## Success Criteria

### Before Running Full Trading
1. ✅ Quick diagnostics pass completely
2. ✅ All 9 component tests pass
3. ✅ Market data available for top 3 DAX stocks
4. ✅ OpenRouter API responds correctly
5. ✅ Web search returns multiple results
6. ✅ Research pipeline completes successfully

### During Trading Sessions
1. ✅ No critical errors (only warnings acceptable)
2. ✅ Research completes for all target stocks
3. ✅ LLM models make valid trading decisions
4. ✅ Trades execute without errors
5. ✅ Database updates correctly

## Next Steps

1. **Run Diagnostics:** `run_quick_diagnostics.bat`
2. **Fix Issues:** Address any configuration problems
3. **Component Testing:** `run_component_tests.bat`
4. **Fix Components:** Address any failing tests
5. **Full Testing:** `run_manual_trading.bat`
6. **Monitor Performance:** Watch for warnings and optimize

## Files Created

- `scripts/comprehensive_component_test.py` - Full component testing
- `scripts/quick_diagnostics.py` - Quick issue identification
- `run_component_tests.bat` - Component testing launcher
- `run_quick_diagnostics.bat` - Diagnostics launcher
- `TESTING_GUIDE.md` - This guide

## Support

If you encounter issues not covered here:
1. Check the logs for specific error messages
2. Run the diagnostic scripts to identify the problem area
3. Test individual components to isolate the issue
4. Review the component test results for detailed failure information

Remember: **Always test components individually before running the full system!**