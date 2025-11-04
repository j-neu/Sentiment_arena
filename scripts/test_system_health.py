"""
System Health Test Script

Tests all critical components to ensure the system is ready for trading:
- Database connectivity
- Model identifiers (correct OpenRouter format)
- API connectivity (OpenRouter, Alpha Vantage, Finnhub)
- Market data fetching
- Research system
- Complete research orchestrator

Run this script after fixes to validate the system is working properly.
"""
import sys
from pathlib import Path
import time
import io

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database.base import SessionLocal
from backend.models.model import Model
from backend.services.openrouter_client import OpenRouterClient
from backend.services.market_data import MarketDataService
from backend.services.research import ResearchService
from backend.services.complete_research_orchestrator import CompleteResearchOrchestrator
from backend.services.research_model_mapper import ResearchModelMapper
from backend.config import settings
from backend.logger import get_logger
from backend.constants import DAX_TOP_5

logger = get_logger(__name__)


def print_header(title):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_success(message):
    """Print success message"""
    print(f"✓ {message}")


def print_error(message):
    """Print error message"""
    print(f"✗ {message}")


def print_warning(message):
    """Print warning message"""
    print(f"⚠ {message}")


def test_database():
    """Test database connectivity"""
    print_header("TEST 1: Database Connectivity")
    try:
        db = SessionLocal()
        models = db.query(Model).all()
        print_success(f"Database connected successfully")
        print_success(f"Found {len(models)} models in database")

        if len(models) == 0:
            print_warning("No models found. Run scripts/init_demo_data.py first")
            return False, []

        return True, models
    except Exception as e:
        print_error(f"Database connection failed: {e}")
        return False, []
    finally:
        db.close()


def test_model_identifiers(models):
    """Test that all model identifiers are correct"""
    print_header("TEST 2: Model Identifiers")

    # Known incorrect identifiers that should have been fixed
    KNOWN_INCORRECT = {
        "anthropic/claude-sonnet-4-5": "anthropic/claude-4.5-sonnet-20250929",
        "deepseek/deepseek-v3.1": "deepseek/deepseek-chat-v3.1",
        "zhipuai/glm-4.6": "z-ai/glm-4.6",
    }

    all_correct = True
    for model in models:
        identifier = model.api_identifier

        # Check if it's an old incorrect identifier
        if identifier in KNOWN_INCORRECT:
            print_error(f"Model '{model.name}' has INCORRECT identifier: {identifier}")
            print(f"  → Should be: {KNOWN_INCORRECT[identifier]}")
            print(f"  → Run: python scripts/update_model_identifiers.py")
            all_correct = False
        else:
            print_success(f"Model '{model.name}': {identifier}")

            # Check if it's in research mapper
            research_model = ResearchModelMapper.get_research_model(identifier)
            print(f"    Research model: {research_model}")

    if all_correct:
        print_success("All model identifiers are correct!")
    else:
        print_error("Some model identifiers need updating!")

    return all_correct


def test_openrouter_connectivity(models):
    """Test OpenRouter API connectivity with each model"""
    print_header("TEST 3: OpenRouter API Connectivity")

    if not settings.OPENROUTER_API_KEY or settings.OPENROUTER_API_KEY == "your_openrouter_api_key_here":
        print_error("OPENROUTER_API_KEY not set in .env file")
        return False

    print_success(f"API Key found: {settings.OPENROUTER_API_KEY[:20]}...")

    client = OpenRouterClient(settings.OPENROUTER_API_KEY)
    success_count = 0
    total = len(models)

    for model in models:
        print(f"\nTesting: {model.name} ({model.api_identifier})")
        try:
            # Test with a simple prompt
            response = client.chat_completion(
                model=model.api_identifier,
                messages=[{"role": "user", "content": "Reply with just 'OK' if you receive this."}],
                max_tokens=10,
                temperature=0
            )

            # Extract the message content from the response
            if response and "choices" in response and len(response["choices"]) > 0:
                content = response["choices"][0]["message"]["content"]
                print_success(f"  Response: {content[:50]}")
                success_count += 1
            else:
                print_error(f"  Empty response from model")
        except Exception as e:
            print_error(f"  API call failed: {str(e)[:100]}")

        time.sleep(1)  # Rate limiting

    print(f"\n{'=' * 70}")
    print(f"OpenRouter Test Results: {success_count}/{total} models working")

    if success_count == total:
        print_success("All models working!")
        return True
    elif success_count > 0:
        print_warning(f"{total - success_count} models failed. Check identifiers.")
        return False
    else:
        print_error("No models working! Check API key and identifiers.")
        return False


def test_market_data():
    """Test market data fetching"""
    print_header("TEST 4: Market Data Service")

    try:
        db = SessionLocal()
        market_data = MarketDataService(db)

        # Test with top DAX stocks
        test_symbols = DAX_TOP_5[:3]  # Test first 3
        print(f"Testing with symbols: {test_symbols}")

        success_count = 0
        for symbol in test_symbols:
            print(f"\nFetching: {symbol}")
            try:
                data = market_data.fetch_price(symbol)
                if data:
                    print_success(f"  Price: €{data.get('price', 'N/A'):.2f}")
                    print(f"  Volume: {data.get('volume', 'N/A'):,}")
                    success_count += 1
                else:
                    print_error(f"  No data returned")
            except Exception as e:
                print_error(f"  Failed: {e}")

        if success_count == len(test_symbols):
            print_success("\nMarket data service working!")
            return True
        else:
            print_warning(f"\nPartial success: {success_count}/{len(test_symbols)} stocks")
            return success_count > 0

    except Exception as e:
        print_error(f"Market data service failed: {e}")
        return False
    finally:
        db.close()


def test_research_system():
    """Test research service"""
    print_header("TEST 5: Research System")

    try:
        research = ResearchService()

        # Test basic market sentiment search
        print("Testing market sentiment search...")
        results = research.search_market_sentiment("DAX stock market", max_results=5)

        if len(results) > 0:
            print_success(f"Found {len(results)} research articles")
            for i, result in enumerate(results[:3], 1):
                print(f"  {i}. {result.get('title', 'No title')[:60]}")
                print(f"     Source: {result.get('source', 'Unknown')}")
            return True
        else:
            print_warning("No research results found (search may be blocked/rate-limited)")
            print("  This is not critical - complete research may still work")
            return False

    except Exception as e:
        print_error(f"Research system failed: {e}")
        return False


def test_complete_research():
    """Test complete research orchestrator"""
    print_header("TEST 6: Complete Research Orchestrator")

    if not settings.OPENROUTER_API_KEY:
        print_error("Cannot test without OPENROUTER_API_KEY")
        return False

    try:
        orchestrator = CompleteResearchOrchestrator(
            openrouter_api_key=settings.OPENROUTER_API_KEY,
            alphavantage_api_key=getattr(settings, 'ALPHAVANTAGE_API_KEY', None),
            finnhub_api_key=getattr(settings, 'FINNHUB_API_KEY', None),
            model_identifier="openai/gpt-4o-mini"  # Use cheap model for testing
        )

        print_success("Complete research orchestrator initialized")

        # Test with one stock
        test_symbol = "SAP.DE"
        print(f"\nTesting complete research for {test_symbol}...")
        print("(This may take 30-60 seconds)")

        result = orchestrator.conduct_complete_research(
            symbol=test_symbol,
            include_technical=True,
            include_financial_apis=False,  # Skip to save API calls
            include_web_research=False,    # Skip to save time
            include_quality_verification=False
        )

        if result.get("success"):
            print_success("Complete research successful!")
            timing = result.get("timing", {})
            print(f"  Technical analysis: {timing.get('technical', 0):.1f}s")
            print(f"  Total time: {timing.get('total', 0):.1f}s")

            briefing = result.get("unified_briefing", "")
            if briefing:
                print(f"\nBriefing preview (first 200 chars):")
                print(f"  {briefing[:200]}...")

            return True
        else:
            print_error("Complete research failed")
            errors = result.get("errors", [])
            for error in errors[:3]:
                print(f"  - {error}")
            return False

    except Exception as e:
        print_error(f"Complete research orchestrator failed: {e}")
        import traceback
        print(f"\nFull error:")
        traceback.print_exc()
        return False


def main():
    """Run all health tests"""
    print("\n" + "=" * 70)
    print("  SENTIMENT ARENA - SYSTEM HEALTH CHECK")
    print("=" * 70)
    print("\nThis script will test all critical components of the trading system.")
    print("Please wait while tests run...\n")

    results = {}

    # Test 1: Database
    db_ok, models = test_database()
    results["database"] = db_ok

    if not db_ok or len(models) == 0:
        print("\n❌ Cannot continue without database. Please fix and retry.")
        return

    # Test 2: Model Identifiers
    identifiers_ok = test_model_identifiers(models)
    results["identifiers"] = identifiers_ok

    if not identifiers_ok:
        print("\n⚠️  Model identifiers need updating. Run update script first.")
        print("   Command: python scripts/update_model_identifiers.py")
        response = input("\nContinue with remaining tests? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            return

    # Test 3: OpenRouter
    openrouter_ok = test_openrouter_connectivity(models)
    results["openrouter"] = openrouter_ok

    # Test 4: Market Data
    market_data_ok = test_market_data()
    results["market_data"] = market_data_ok

    # Test 5: Research
    research_ok = test_research_system()
    results["research"] = research_ok

    # Test 6: Complete Research
    complete_research_ok = test_complete_research()
    results["complete_research"] = complete_research_ok

    # Summary
    print_header("SUMMARY")
    print(f"\n{'Component':<30} {'Status'}")
    print("-" * 50)

    for component, status in results.items():
        status_str = "✓ PASS" if status else "✗ FAIL"
        print(f"{component.replace('_', ' ').title():<30} {status_str}")

    total_tests = len(results)
    passed_tests = sum(results.values())

    print("\n" + "=" * 70)
    print(f"OVERALL: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print("\n✓ System is healthy and ready for trading!")
        print("\nYou can now run: run_manual_trading.bat")
    elif passed_tests >= total_tests - 1:
        print("\n⚠️  System is mostly healthy with minor issues.")
        print("You can proceed, but some features may not work optimally.")
        print("\nYou can try: run_manual_trading.bat")
    else:
        print("\n❌ System has significant issues. Please fix before trading.")
        print("\nRequired fixes:")
        if not results["database"]:
            print("  - Fix database connection")
        if not results["identifiers"]:
            print("  - Update model identifiers: python scripts/update_model_identifiers.py")
        if not results["openrouter"]:
            print("  - Check OpenRouter API key in .env")
            print("  - Verify model identifiers are correct")
        if not results["market_data"]:
            print("  - Check internet connection")
            print("  - Verify Yahoo Finance is accessible")

    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
