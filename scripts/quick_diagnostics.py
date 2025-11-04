#!/usr/bin/env python3
"""
Quick Diagnostics for Sentiment Arena

This script quickly identifies the most common issues:
1. API connectivity problems
2. Data availability issues  
3. Configuration mismatches
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import settings
from backend.services.openrouter_client import OpenRouterClient
from backend.services.alphavantage_client import AlphaVantageClient
from backend.services.finnhub_client import FinnhubClient
from backend.services.market_data import MarketDataService
from backend.database.base import SessionLocal
from backend.models.model import Model
from backend.logger import get_logger

logger = get_logger(__name__)

def check_configuration():
    """Check if configuration is properly set."""
    print("🔧 CONFIGURATION CHECK")
    print("-" * 40)
    
    issues = []
    
    # Check API keys
    if not settings.OPENROUTER_API_KEY:
        issues.append("❌ OPENROUTER_API_KEY not set")
    else:
        print(f"✅ OpenRouter API Key: {settings.OPENROUTER_API_KEY[:20]}...")
    
    if not getattr(settings, 'ALPHAVANTAGE_API_KEY', None):
        print("⚠️  Alpha Vantage API Key: Not set (optional)")
    else:
        print(f"✅ Alpha Vantage API Key: {settings.ALPHAVANTAGE_API_KEY[:10]}...")
    
    if not getattr(settings, 'FINNHUB_API_KEY', None):
        print("⚠️  Finnhub API Key: Not set (optional)")
    else:
        print(f"✅ Finnhub API Key: {settings.FINNHUB_API_KEY[:10]}...")
    
    # Check database
    try:
        db = SessionLocal()
        model_count = db.query(Model).count()
        print(f"✅ Database: Connected ({model_count} models)")
        db.close()
    except Exception as e:
        issues.append(f"❌ Database: {str(e)}")
    
    return issues

def check_apis():
    """Check API connectivity."""
    print("\n🌐 API CONNECTIVITY CHECK")
    print("-" * 40)
    
    issues = []
    
    # Test OpenRouter
    try:
        client = OpenRouterClient()
        response = client.get_completion_text(
            model="openai/gpt-4o-mini",
            messages=[{"role": "user", "content": "Test"}],
            max_tokens=5
        )
        if response:
            print("✅ OpenRouter API: Working")
        else:
            issues.append("❌ OpenRouter API: No response")
    except Exception as e:
        issues.append(f"❌ OpenRouter API: {str(e)}")
    
    # Test Alpha Vantage
    try:
        if getattr(settings, 'ALPHAVANTAGE_API_KEY', None):
            client = AlphaVantageClient()
            overview = client.get_company_overview('SAP')
            if overview and 'Symbol' in overview:
                print("✅ Alpha Vantage API: Working")
            else:
                issues.append("⚠️  Alpha Vantage API: No data for SAP")
        else:
            print("⚠️  Alpha Vantage API: Skipped (no API key)")
    except Exception as e:
        issues.append(f"❌ Alpha Vantage API: {str(e)}")
    
    # Test Finnhub
    try:
        if getattr(settings, 'FINNHUB_API_KEY', None):
            client = FinnhubClient()
            news = client.get_company_news('SAP')
            if news and len(news) > 0:
                print(f"✅ Finnhub API: Working ({len(news)} articles)")
            else:
                issues.append("⚠️  Finnhub API: No news for SAP")
        else:
            print("⚠️  Finnhub API: Skipped (no API key)")
    except Exception as e:
        issues.append(f"❌ Finnhub API: {str(e)}")
    
    return issues

def check_market_data():
    """Check market data availability."""
    print("\n📈 MARKET DATA CHECK")
    print("-" * 40)
    
    issues = []
    
    try:
        service = MarketDataService()
        test_symbols = ['SAP.DE', 'SIE.DE', 'AIR.DE']
        
        for symbol in test_symbols:
            try:
                data = service.fetch_price(symbol)
                if data and 'price' in data:
                    print(f"✅ {symbol}: €{data['price']:.2f}")
                else:
                    issues.append(f"⚠️  {symbol}: No price data")
            except Exception as e:
                issues.append(f"❌ {symbol}: {str(e)}")
    except Exception as e:
        issues.append(f"❌ Market Data Service: {str(e)}")
    
    return issues

def check_models():
    """Check model configuration."""
    print("\n🤖 MODEL CONFIGURATION CHECK")
    print("-" * 40)
    
    issues = []
    
    try:
        db = SessionLocal()
        models = db.query(Model).all()
        
        if not models:
            issues.append("❌ No models found in database")
            return issues
        
        print(f"✅ Found {len(models)} models in database:")
        for model in models:
            print(f"  - {model.name}: {model.api_identifier}")
        
        # Check if models match .env configuration
        active_models = getattr(settings, 'ACTIVE_MODELS', '').split(',')
        active_models = [m.strip() for m in active_models if m.strip()]
        
        db_model_ids = [m.api_identifier for m in models]
        
        missing_in_env = set(db_model_ids) - set(active_models)
        extra_in_env = set(active_models) - set(db_model_ids)
        
        if missing_in_env:
            issues.append(f"⚠️  Models in DB but not in .env: {missing_in_env}")
        
        if extra_in_env:
            issues.append(f"⚠️  Models in .env but not in DB: {extra_in_env}")
        
        if not missing_in_env and not extra_in_env:
            print("✅ Model configuration matches between DB and .env")
        
        db.close()
        
    except Exception as e:
        issues.append(f"❌ Model check: {str(e)}")
    
    return issues

def main():
    """Run all diagnostics."""
    print("=" * 60)
    print("SENTIMENT ARENA - QUICK DIAGNOSTICS")
    print("=" * 60)
    
    all_issues = []
    
    # Run all checks
    all_issues.extend(check_configuration())
    all_issues.extend(check_apis())
    all_issues.extend(check_market_data())
    all_issues.extend(check_models())
    
    # Summary
    print("\n" + "=" * 60)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 60)
    
    if not all_issues:
        print("🎉 All checks passed! System appears to be configured correctly.")
        print("\nYou can now run:")
        print("  - run_component_tests.bat (comprehensive testing)")
        print("  - run_manual_trading.bat (full trading session)")
    else:
        print(f"⚠️  Found {len(all_issues)} issues:")
        for issue in all_issues:
            print(f"  {issue}")
        
        print("\n🔧 RECOMMENDED ACTIONS:")
        print("1. Fix configuration issues first")
        print("2. Run: run_component_tests.bat")
        print("3. Fix any failing components")
        print("4. Then try: run_manual_trading.bat")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()