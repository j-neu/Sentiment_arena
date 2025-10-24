"""
Example script demonstrating the TradingEngine functionality.

This script shows how to:
1. Initialize a trading engine
2. Create portfolios for models
3. Execute buy and sell orders
4. Track positions and P&L
5. Calculate performance metrics
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import backend modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database.base import SessionLocal, engine, Base
from backend.services.trading_engine import TradingEngine
from backend.models.model import Model
from backend.models.portfolio import Portfolio
from backend.models.position import Position
from backend.models.trade import Trade


def print_separator(title: str = ""):
    """Print a visual separator."""
    if title:
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}")
    else:
        print(f"{'='*60}\n")


def main():
    """Main example function."""

    # Create database tables
    Base.metadata.create_all(bind=engine)

    # Create database session
    db = SessionLocal()

    try:
        print_separator("TRADING ENGINE DEMO")

        # Clean up any existing test data
        db.query(Trade).delete()
        db.query(Position).delete()
        db.query(Portfolio).delete()
        db.query(Model).filter(Model.name == "Demo Model").delete()
        db.commit()

        # Create a test model
        model = Model(
            name="Demo Model",
            api_identifier="demo/test-model",
            starting_balance=1000.0
        )
        db.add(model)
        db.commit()
        db.refresh(model)
        print(f"[OK] Created model: {model.name} (ID: {model.id})")

        # Initialize trading engine
        engine_instance = TradingEngine(db)
        print(f"[OK] Trading engine initialized with €5 fee per trade")

        # Initialize portfolio
        print_separator("1. Portfolio Initialization")
        portfolio = engine_instance.initialize_portfolio(model.id)
        print(f"Portfolio created:")
        print(f"  Model ID: {portfolio.model_id}")
        print(f"  Starting Balance: €{portfolio.current_balance:.2f}")
        print(f"  Total P&L: €{portfolio.total_pl:.2f}")

        # Execute buy orders
        print_separator("2. Executing Buy Orders")

        print("\nBuying 10 shares of SAP.DE...")
        result1 = engine_instance.execute_buy(model.id, "SAP.DE", 10)
        if result1['success']:
            print(f"[OK] Buy executed:")
            print(f"  Symbol: SAP.DE")
            print(f"  Quantity: {result1['position'].quantity}")
            print(f"  Avg Price: €{result1['position'].avg_price:.2f}")
            print(f"  Total Cost: €{result1['total_cost']:.2f} (includes €5 fee)")
        else:
            print(f"[FAIL] Buy failed: {result1['reason']}")

        print("\nBuying 5 shares of BMW.DE...")
        result2 = engine_instance.execute_buy(model.id, "BMW.DE", 5)
        if result2['success']:
            print(f"[OK] Buy executed:")
            print(f"  Symbol: BMW.DE")
            print(f"  Quantity: {result2['position'].quantity}")
            print(f"  Avg Price: €{result2['position'].avg_price:.2f}")
            print(f"  Total Cost: €{result2['total_cost']:.2f} (includes €5 fee)")
        else:
            print(f"[FAIL] Buy failed: {result2['reason']}")

        # View positions
        print_separator("3. Current Positions")
        positions = engine_instance.get_positions(model.id)
        print(f"Total positions: {len(positions)}\n")

        for pos in positions:
            print(f"Symbol: {pos.symbol}")
            print(f"  Quantity: {pos.quantity}")
            print(f"  Avg Price: €{pos.avg_price:.2f}")
            print(f"  Current Price: €{pos.current_price:.2f}")
            print(f"  Unrealized P&L: €{pos.unrealized_pl:.2f}")
            print()

        # Update position values
        print_separator("4. Updating Position Values")
        print("Fetching latest market prices...")
        updated_positions = engine_instance.update_position_values(model.id)
        print(f"[OK] Updated {len(updated_positions)} positions\n")

        for pos in updated_positions:
            pl_symbol = "+" if pos.unrealized_pl >= 0 else ""
            print(f"{pos.symbol}: €{pos.current_price:.2f} ({pl_symbol}€{pos.unrealized_pl:.2f})")

        # Calculate portfolio value
        print_separator("5. Portfolio Valuation")
        portfolio_value = engine_instance.calculate_portfolio_value(model.id)

        print(f"Cash Balance: €{portfolio_value['cash_balance']:.2f}")
        print(f"Positions Value: €{portfolio_value['positions_value']:.2f}")
        print(f"Total Portfolio Value: €{portfolio_value['total_value']:.2f}")
        print(f"Realized P&L: €{portfolio_value['realized_pl']:.2f}")
        print(f"Unrealized P&L: €{portfolio_value['unrealized_pl']:.2f}")
        print(f"Total P&L: €{portfolio_value['total_pl']:.2f} ({portfolio_value['pl_percentage']:.2f}%)")
        print(f"Open Positions: {portfolio_value['num_positions']}")

        # Execute a sell order (close partial position)
        print_separator("6. Executing Sell Order")

        if len(positions) > 0:
            first_position = positions[0]
            sell_qty = min(5, first_position.quantity)

            print(f"\nSelling {sell_qty} shares of {first_position.symbol}...")
            result3 = engine_instance.execute_sell(model.id, first_position.symbol, sell_qty)

            if result3['success']:
                print(f"[OK] Sell executed:")
                print(f"  Symbol: {first_position.symbol}")
                print(f"  Quantity Sold: {sell_qty}")
                print(f"  Execution Price: €{result3['execution_price']:.2f}")
                print(f"  Total Proceeds: €{result3['total_proceeds']:.2f} (after €5 fee)")
                print(f"  Realized P&L: €{result3['realized_pl']:.2f}")

                if result3['position']:
                    print(f"  Remaining Quantity: {result3['position'].quantity}")
                else:
                    print(f"  Position fully closed")
            else:
                print(f"[FAIL] Sell failed: {result3['reason']}")

        # View trade history
        print_separator("7. Trade History")
        trades = engine_instance.get_trades(model.id, limit=10)
        print(f"Recent trades (showing {len(trades)}):\n")

        for i, trade in enumerate(trades, 1):
            pl_info = ""
            if trade.realized_pl is not None:
                pl_symbol = "+" if trade.realized_pl >= 0 else ""
                pl_info = f" | Realized P&L: {pl_symbol}€{trade.realized_pl:.2f}"

            print(f"{i}. {trade.side.value} {trade.quantity}x {trade.symbol} @ €{trade.price:.2f}")
            print(f"   Total: €{trade.total:.2f} | Fee: €{trade.fee:.2f}{pl_info}")
            print(f"   Status: {trade.status.value} | {trade.executed_at.strftime('%Y-%m-%d %H:%M:%S')}")
            print()

        # Performance metrics
        print_separator("8. Performance Metrics")
        metrics = engine_instance.get_performance_metrics(model.id)

        if metrics:
            print(f"Total Trades: {metrics['total_trades']}")
            print(f"  Buy Orders: {metrics['buy_count']}")
            print(f"  Sell Orders: {metrics['sell_count']}")
            print()
            print(f"Trading Performance:")
            print(f"  Win Rate: {metrics['win_rate']:.1f}%")
            print(f"  Winning Trades: {metrics['winning_trades']}")
            print(f"  Losing Trades: {metrics['losing_trades']}")
            print()
            print(f"Financial Summary:")
            print(f"  Total P&L: €{metrics['total_pl']:.2f} ({metrics['pl_percentage']:.2f}%)")
            print(f"  Realized P&L: €{metrics['realized_pl']:.2f}")
            print(f"  Unrealized P&L: €{metrics['unrealized_pl']:.2f}")
            print(f"  Total Fees Paid: €{metrics['total_fees_paid']:.2f}")
            print()
            print(f"Portfolio Status:")
            print(f"  Starting Balance: €{metrics['starting_balance']:.2f}")
            print(f"  Current Cash: €{metrics['cash_balance']:.2f}")
            print(f"  Positions Value: €{metrics['positions_value']:.2f}")
            print(f"  Total Portfolio Value: €{metrics['total_value']:.2f}")

        print_separator("DEMO COMPLETE")
        print("All trading engine features demonstrated successfully!")

    except Exception as e:
        print(f"\n[FAIL] Error occurred: {e}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


if __name__ == "__main__":
    main()
