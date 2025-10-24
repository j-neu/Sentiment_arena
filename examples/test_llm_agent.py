"""
Example script demonstrating the LLM Agent system.

This script shows how to:
1. Initialize an LLM agent for a model
2. Make trading decisions with research
3. View reasoning and execution results
4. Handle multiple trading sessions
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database.base import SessionLocal, engine
from backend.models import Base
from backend.models.model import Model
from backend.services.llm_agent import LLMAgent
from backend.services.trading_engine import TradingEngine
from backend.logger import get_logger

logger = get_logger(__name__)


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def main():
    """Main example function."""
    print_section("LLM Agent Demo - Sentiment Arena")

    # Create database tables
    Base.metadata.create_all(bind=engine)

    # Create database session
    db = SessionLocal()

    try:
        # Step 1: Create a model
        print_section("Step 1: Creating LLM Model")

        # Check if model already exists
        existing_model = db.query(Model).filter(Model.api_identifier == "openai/gpt-4-turbo").first()

        if existing_model:
            print(f"Using existing model: {existing_model.name} (ID: {existing_model.id})")
            model = existing_model
        else:
            model = Model(
                name="GPT-4 Turbo",
                api_identifier="openai/gpt-4-turbo",
                starting_balance=1000.0
            )
            db.add(model)
            db.commit()
            db.refresh(model)
            print(f"Created new model: {model.name} (ID: {model.id})")

        # Step 2: Initialize portfolio
        print_section("Step 2: Initializing Portfolio")

        trading_engine = TradingEngine(db)
        portfolio = trading_engine.get_portfolio(model.id)

        if not portfolio:
            portfolio = trading_engine.initialize_portfolio(model.id)
            print(f"Portfolio initialized with €{portfolio.current_balance:.2f}")
        else:
            print(f"Existing portfolio found:")
            print(f"  Balance: €{portfolio.current_balance:.2f}")
            print(f"  Total Value: €{portfolio.total_value:.2f}")
            print(f"  Total P&L: €{portfolio.total_pl:.2f}")

        # Step 3: Create LLM Agent
        print_section("Step 3: Creating LLM Agent")

        # Note: This will use the API key from .env file
        print(f"Initializing agent for {model.name}...")
        agent = LLMAgent(db, model_id=model.id)
        print("Agent initialized successfully!")
        print(f"  - OpenRouter client ready")
        print(f"  - Research service ready")
        print(f"  - Market data service ready")
        print(f"  - Trading engine ready")

        # Step 4: Get current positions
        print_section("Step 4: Current Portfolio State")

        positions = trading_engine.get_positions(model.id)
        if positions:
            print(f"Open positions ({len(positions)}):")
            for pos in positions:
                print(f"  - {pos.symbol}: {pos.quantity} shares @ €{pos.avg_price:.2f}")
                print(f"    Current: €{pos.current_price:.2f} | P&L: €{pos.unrealized_pl:.2f}")
        else:
            print("No open positions")

        # Step 5: Make a trading decision (with research)
        print_section("Step 5: Making Trading Decision (WITH Research)")

        print("Note: This will make real API calls to OpenRouter and perform web searches!")
        user_input = input("Continue? (y/n): ")

        if user_input.lower() == 'y':
            print("\nPerforming market research and making trading decision...")
            print("This may take 30-60 seconds...\n")

            result = agent.make_trading_decision(
                perform_research=True,
                research_queries=["German stock market news", "DAX outlook"]
            )

            if result["success"]:
                print("✅ Decision made successfully!")

                decision = result["decision"]
                print(f"\nDecision Details:")
                print(f"  Action: {decision['action']}")

                if decision['action'] != 'HOLD':
                    print(f"  Symbol: {decision.get('symbol', 'N/A')}")
                    print(f"  Quantity: {decision.get('quantity', 'N/A')}")

                print(f"  Confidence: {decision.get('confidence', 'N/A')}")
                print(f"\nReasoning:")
                print(f"  {decision.get('reasoning', 'No reasoning provided')}")
                print(f"\nMarket Outlook:")
                print(f"  {decision.get('market_outlook', 'N/A')}")
                print(f"\nRisk Assessment:")
                print(f"  {decision.get('risk_assessment', 'N/A')}")

                # Show execution result
                execution = result["execution"]
                print(f"\nExecution Result:")
                print(f"  Success: {execution.get('success', False)}")

                if execution.get('success'):
                    print(f"  Action: {execution.get('action', 'N/A')}")
                    if execution.get('action') == 'BUY' and 'position' in execution:
                        pos = execution['position']
                        print(f"  Position: {pos.quantity} shares of {pos.symbol} @ €{pos.avg_price:.2f}")
                    elif execution.get('action') == 'SELL' and 'realized_pl' in execution:
                        print(f"  Realized P&L: €{execution['realized_pl']:.2f}")
                else:
                    print(f"  Error: {execution.get('error', 'Unknown error')}")

            else:
                print(f"❌ Decision failed: {result.get('error', 'Unknown error')}")

        # Step 6: Make a decision without research
        print_section("Step 6: Making Trading Decision (WITHOUT Research)")

        user_input = input("Make another decision without research? (y/n): ")

        if user_input.lower() == 'y':
            print("\nMaking trading decision without research...")

            result = agent.make_trading_decision(perform_research=False)

            if result["success"]:
                decision = result["decision"]
                print(f"✅ Decision: {decision['action']}")
                print(f"   Reasoning: {decision.get('reasoning', 'N/A')}")
            else:
                print(f"❌ Error: {result.get('error', 'Unknown')}")

        # Step 7: View latest reasoning
        print_section("Step 7: Latest Reasoning")

        latest_reasoning = agent.get_latest_reasoning()
        if latest_reasoning:
            print(f"Timestamp: {latest_reasoning.created_at}")
            print(f"Decision: {latest_reasoning.decision}")
            print(f"\nFull Reasoning:")
            print(latest_reasoning.reasoning_text)

            if latest_reasoning.research_content:
                print(f"\nResearch Summary (first 500 chars):")
                print(latest_reasoning.research_content[:500] + "...")
        else:
            print("No reasoning entries found")

        # Step 8: View updated portfolio
        print_section("Step 8: Updated Portfolio State")

        db.refresh(portfolio)
        print(f"Current Balance: €{portfolio.current_balance:.2f}")
        print(f"Total Value: €{portfolio.total_value:.2f}")
        print(f"Total P&L: €{portfolio.total_pl:.2f}")

        positions = trading_engine.get_positions(model.id)
        if positions:
            print(f"\nOpen Positions ({len(positions)}):")
            for pos in positions:
                db.refresh(pos)
                print(f"  - {pos.symbol}: {pos.quantity} shares @ €{pos.avg_price:.2f}")
                print(f"    Current: €{pos.current_price:.2f} | P&L: €{pos.unrealized_pl:.2f}")

        # Step 9: View performance metrics
        print_section("Step 9: Performance Metrics")

        metrics = trading_engine.get_performance_metrics(model.id)
        print(f"Total Trades: {metrics['total_trades']}")
        print(f"  - Buy Orders: {metrics['buy_count']}")
        print(f"  - Sell Orders: {metrics['sell_count']}")
        print(f"Win Rate: {metrics['win_rate']:.1f}%")
        print(f"  - Winning Trades: {metrics['winning_trades']}")
        print(f"  - Losing Trades: {metrics['losing_trades']}")
        print(f"Total Fees Paid: €{metrics['total_fees']:.2f}")
        print(f"Total P&L: €{metrics['total_pl']:.2f} ({metrics['pl_percentage']:.2f}%)")

        print_section("Demo Complete!")
        print("The LLM agent successfully demonstrated:")
        print("  ✅ Portfolio initialization")
        print("  ✅ Market research aggregation")
        print("  ✅ LLM-powered decision making")
        print("  ✅ Trade execution")
        print("  ✅ Reasoning storage")
        print("  ✅ Performance tracking")

    except Exception as e:
        logger.error(f"Error in demo: {e}", exc_info=True)
        print(f"\n❌ Error occurred: {e}")
        print("Check the logs for more details")

    finally:
        # Cleanup
        if 'agent' in locals():
            agent.close()
        db.close()
        print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
