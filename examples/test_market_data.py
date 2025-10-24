"""
Example script to test the Market Data Service

This script demonstrates how to use the MarketDataService to:
- Check market status
- Validate symbols
- Fetch real-time prices for German stocks
- Use caching to avoid rate limits
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database.base import SessionLocal
from backend.services.market_data import MarketDataService


def main():
    """Run market data service examples"""
    print("=" * 60)
    print("Market Data Service Test")
    print("=" * 60)

    # Create database session
    db = SessionLocal()
    service = MarketDataService(db)

    try:
        # 1. Check market status
        print("\n1. Checking market status...")
        status = service.get_market_status()
        print(f"   Market is open: {status['is_open']}")
        print(f"   Trading day: {status['is_trading_day']}")
        print(f"   Current time (CET): {status['current_time_cet']}")
        print(f"   Status: {status['status_message']}")

        # 2. Validate symbols
        print("\n2. Validating stock symbols...")
        symbols_to_test = ["SAP.DE", "BMW.DE", "AAPL", "VOW3.DE", "INVALID"]
        for symbol in symbols_to_test:
            is_valid = service.validate_symbol(symbol)
            print(f"   {symbol}: {'✓ Valid' if is_valid else '✗ Invalid'}")

        # 3. Fetch prices for valid German stocks
        print("\n3. Fetching live prices (this may take a moment)...")
        german_stocks = ["SAP.DE", "BMW.DE", "VOW3.DE", "DBK.DE"]

        for symbol in german_stocks:
            print(f"\n   Fetching {symbol}...")
            price_data = service.fetch_price(symbol, use_cache=True)

            if price_data:
                print(f"   ✓ Symbol: {price_data['symbol']}")
                print(f"     Price: €{price_data['price']:.2f}")
                if price_data.get('volume'):
                    print(f"     Volume: {price_data['volume']:,}")
                if price_data.get('day_high') and price_data.get('day_low'):
                    print(f"     Day Range: €{price_data['day_low']:.2f} - €{price_data['day_high']:.2f}")
            else:
                print(f"   ✗ Failed to fetch price for {symbol}")

        # 4. Test caching
        print("\n4. Testing cache (should be instant)...")
        cached_data = service.fetch_price("SAP.DE", use_cache=True)
        if cached_data:
            print(f"   ✓ Retrieved cached price for SAP.DE: €{cached_data['price']:.2f}")
        else:
            print("   ✗ Cache miss")

        # 5. Fetch multiple prices at once
        print("\n5. Fetching multiple prices...")
        results = service.fetch_multiple_prices(["SAP.DE", "BMW.DE"], use_cache=True)
        for symbol, data in results.items():
            if data:
                print(f"   {symbol}: €{data['price']:.2f}")
            else:
                print(f"   {symbol}: Failed to fetch")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()

    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
