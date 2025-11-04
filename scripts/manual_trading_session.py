"""
Sentiment Arena - Manual Trading Session Script

This script triggers a single trading session for all active models.
Run this manually at 8:30 AM and 2:00 PM CET, or whenever you want to test trading.

Usage:
    python scripts/manual_trading_session.py [--job-name pre_market_research|afternoon_research]

Examples:
    python scripts/manual_trading_session.py
    python scripts/manual_trading_session.py --job-name pre_market_research
    python scripts/manual_trading_session.py --job-name afternoon_research
"""

import sys
import os
import argparse
from datetime import datetime
import pytz

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database.base import SessionLocal, engine
from backend.models.model import Model
from backend.services.trading_engine import TradingEngine
from backend.services.market_data import MarketDataService
from backend.services.multi_model_research_orchestrator import MultiModelResearchOrchestrator
from backend.services.llm_agent import LLMAgent
from backend.config import settings
from backend.logger import get_logger

logger = get_logger(__name__)


def print_banner():
    """Print a nice banner"""
    print("=" * 70)
    print(" " * 15 + "SENTIMENT ARENA - MANUAL TRADING")
    print("=" * 70)
    print()


def get_current_cet_time():
    """Get current time in CET timezone"""
    cet_tz = pytz.timezone('Europe/Berlin')
    return datetime.now(cet_tz)


def check_market_status(db: SessionLocal):
    """Check if market is currently open"""
    market_data = MarketDataService(db)
    is_open = market_data.is_market_open()
    is_trading_day = market_data.is_trading_day()

    current_time = get_current_cet_time()

    print(f"Current Time (CET): {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Market Open: {'YES ✓' if is_open else 'NO ✗'}")
    print(f"Trading Day: {'YES ✓' if is_trading_day else 'NO ✗'}")
    print()

    if not is_trading_day:
        print("⚠️  WARNING: Today is not a trading day (weekend or holiday)")
        print()

    if not is_open:
        print("⚠️  WARNING: Market is currently closed (9:00 AM - 5:30 PM CET)")
        print("   Trades can be planned but won't execute until market opens.")
        print()

    return is_open, is_trading_day


def run_trading_session(job_name: str = "manual_session"):
    """
    Run a complete trading session for all models

    Args:
        job_name: Name of the job (pre_market_research, afternoon_research, or manual_session)
    """
    print_banner()

    # Check market status
    db = SessionLocal()
    is_open, is_trading_day = check_market_status(db)

    print(f"Job Type: {job_name}")
    print("=" * 70)
    print()

    # Create services
    market_data = MarketDataService(db)
    trading_engine = TradingEngine(db, market_data)
    research_orchestrator = MultiModelResearchOrchestrator(
        openrouter_api_key=settings.OPENROUTER_API_KEY,
        alphavantage_api_key=settings.ALPHAVANTAGE_API_KEY,
        finnhub_api_key=settings.FINNHUB_API_KEY
    )

    try:
        # Get all active models
        models = db.query(Model).all()

        if not models:
            print("❌ ERROR: No models found in database!")
            print("   Please run: python scripts/init_demo_data.py")
            return False

        print(f"Found {len(models)} models:")
        for model in models:
            print(f"  - {model.name} ({model.api_identifier})")
        print()

        # Process each model
        success_count = 0
        error_count = 0

        for i, model in enumerate(models, 1):
            print(f"[{i}/{len(models)}] Processing {model.name}...")
            print("-" * 70)

            try:
                # Create LLM agent for this model
                agent = LLMAgent(
                    db=db,
                    model_id=model.id,
                    trading_engine=trading_engine,
                    market_data_service=market_data
                )

                # Run trading decision
                print(f"  → Running research and trading decision...")
                result = agent.make_trading_decision()

                if result.get('success'):
                    print(f"  ✓ Success!")
                    execution = result.get('execution', {})
                    if execution.get('success') and execution.get('action') in ['BUY', 'SELL']:
                        print(f"  ✓ Executed {execution.get('action')} order")
                        if execution.get('symbol'):
                            print(f"     • {execution.get('action')} {execution.get('symbol', 'N/A')} @ €{execution.get('price', 0):.2f}")
                    else:
                        print(f"  → No trades executed (decision: {result.get('decision', {}).get('action', 'HOLD')})")
                    success_count += 1
                else:
                    print(f"  ✗ Failed: {result.get('error', 'Unknown error')}")
                    error_count += 1

            except Exception as e:
                print(f"  ✗ Error: {str(e)}")
                logger.error(f"Error processing model {model.name}", exc_info=True)
                error_count += 1

            print()

        # Summary
        print("=" * 70)
        print("TRADING SESSION COMPLETE")
        print("=" * 70)
        print(f"Successful: {success_count}/{len(models)}")
        print(f"Failed: {error_count}/{len(models)}")
        print()

        current_time = get_current_cet_time()
        print(f"Completed at: {current_time.strftime('%Y-%m-%d %H:%M:%S CET')}")
        print()

        # Next steps
        if success_count > 0:
            print("✓ View results at: http://localhost:3000")
            print("✓ Check API at: http://localhost:8000/docs")

        return success_count > 0

    finally:
        db.close()
        research_orchestrator.cleanup()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Run a manual trading session for all models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/manual_trading_session.py
  python scripts/manual_trading_session.py --job-name pre_market_research
  python scripts/manual_trading_session.py --job-name afternoon_research

Job Types:
  pre_market_research   - Morning research session (before 9:00 AM)
  afternoon_research    - Afternoon session (2:00 PM)
  manual_session        - Ad-hoc manual session (default)
        """
    )

    parser.add_argument(
        '--job-name',
        type=str,
        default='manual_session',
        choices=['pre_market_research', 'afternoon_research', 'manual_session'],
        help='Type of trading session to run (default: manual_session)'
    )

    args = parser.parse_args()

    try:
        success = run_trading_session(args.job_name)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Session cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ ERROR: {str(e)}")
        logger.error("Manual trading session failed", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
