"""
Example script demonstrating Financial Data API integration (Phase 3.5.2).

This script shows how to use:
- Alpha Vantage API (fundamentals, earnings, technical indicators)
- Finnhub API (news, analyst ratings, sentiment)
- Financial Data Aggregator (unified interface)

Requirements:
- ALPHAVANTAGE_API_KEY in .env
- FINNHUB_API_KEY in .env
"""

import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path.parent))

from backend.services.alphavantage_client import AlphaVantageClient
from backend.services.finnhub_client import FinnhubClient
from backend.services.financial_data_aggregator import FinancialDataAggregator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def demo_alphavantage(symbol: str = "SAP"):
    """Demonstrate Alpha Vantage API client."""
    print_section("ALPHA VANTAGE API DEMO")

    with AlphaVantageClient() as av:
        print(f"Testing Alpha Vantage API with {symbol}...\n")

        # Company overview
        print("1. Company Overview:")
        overview = av.get_company_overview(symbol)
        if overview:
            print(f"   Name: {overview['name']}")
            print(f"   Sector: {overview['sector']}")
            print(f"   Market Cap: €{overview['market_cap'] / 1e9:.2f}B")
            print(f"   P/E Ratio: {overview['pe_ratio']}")
            print(f"   Profit Margin: {overview['profit_margin'] * 100:.2f}%" if overview['profit_margin'] else "   Profit Margin: N/A")
        else:
            print("   ❌ Failed to fetch company overview")

        # Earnings
        print("\n2. Earnings:")
        earnings = av.get_earnings(symbol)
        if earnings and earnings.get('latest_quarter'):
            lq = earnings['latest_quarter']
            print(f"   Latest Quarter: {lq['fiscal_date_ending']}")
            print(f"   Reported EPS: ${lq['reported_eps']:.2f}")
            print(f"   Estimated EPS: ${lq['estimated_eps']:.2f}")
            print(f"   Surprise: {lq['surprise_percentage']:+.2f}%")
        else:
            print("   ❌ Failed to fetch earnings")

        # RSI
        print("\n3. Technical Indicators - RSI:")
        rsi = av.get_rsi(symbol)
        if rsi:
            print(f"   RSI (14-day): {rsi['rsi']:.2f}")
            print(f"   Interpretation: {rsi['interpretation'].upper()}")
        else:
            print("   ❌ Failed to fetch RSI")

        # MACD
        print("\n4. Technical Indicators - MACD:")
        macd = av.get_macd(symbol)
        if macd:
            print(f"   MACD: {macd['macd']:.4f}")
            print(f"   Signal: {macd['signal']:.4f}")
            print(f"   Histogram: {macd['histogram']:.4f}")
            print(f"   Interpretation: {macd['interpretation'].replace('_', ' ').upper()}")
            if macd.get('crossover'):
                print(f"   ⚡ {macd['crossover'].upper()} CROSSOVER!")
        else:
            print("   ❌ Failed to fetch MACD")

        # Moving Averages
        print("\n5. Moving Averages:")
        sma_50 = av.get_sma(symbol, time_period=50)
        sma_200 = av.get_sma(symbol, time_period=200)

        if sma_50:
            print(f"   SMA-50: €{sma_50['sma']:.2f}")
        if sma_200:
            print(f"   SMA-200: €{sma_200['sma']:.2f}")

        if sma_50 and sma_200:
            if sma_50['sma'] > sma_200['sma']:
                print("   ⚡ GOLDEN CROSS - Bullish long-term trend")
            else:
                print("   ⚠️ DEATH CROSS - Bearish long-term trend")


def demo_finnhub(symbol: str = "SAP"):
    """Demonstrate Finnhub API client."""
    print_section("FINNHUB API DEMO")

    with FinnhubClient() as fh:
        print(f"Testing Finnhub API with {symbol}...\n")

        # Company news
        print("1. Company News (last 7 days):")
        news = fh.get_company_news(symbol, days_back=7)
        if news:
            print(f"   Total articles: {len(news)}")
            for i, article in enumerate(news[:3], 1):
                sent_emoji = "🟢" if article['sentiment'] == "positive" else "🔴" if article['sentiment'] == "negative" else "⚪"
                print(f"\n   {i}. {sent_emoji} {article['headline']}")
                print(f"      Source: {article['source']} | {article['datetime'].strftime('%Y-%m-%d')}")
        else:
            print("   ❌ Failed to fetch company news")

        # Sentiment
        print("\n2. Market Sentiment:")
        sentiment = fh.get_sentiment(symbol)
        if sentiment:
            print(f"   Overall: {sentiment['interpretation'].replace('_', ' ').upper()}")
            print(f"   Bullish: {sentiment['sentiment_bullish']:.1f}%")
            print(f"   Bearish: {sentiment['sentiment_bearish']:.1f}%")
            print(f"   Articles this week: {sentiment['buzz_articles_in_last_week']}")
        else:
            print("   ❌ Failed to fetch sentiment")

        # Analyst recommendations
        print("\n3. Analyst Recommendations:")
        recommendations = fh.get_recommendation_trends(symbol)
        if recommendations:
            print(f"   Consensus: {recommendations['consensus'].replace('_', ' ').upper()}")
            print(f"   Total Analysts: {recommendations['total_analysts']}")
            print(f"   Strong Buy: {recommendations['strong_buy']}")
            print(f"   Buy: {recommendations['buy']}")
            print(f"   Hold: {recommendations['hold']}")
            print(f"   Sell: {recommendations['sell']}")
            print(f"   Strong Sell: {recommendations['strong_sell']}")
        else:
            print("   ❌ Failed to fetch recommendations")

        # Price target
        print("\n4. Analyst Price Targets:")
        price_target = fh.get_price_target(symbol)
        if price_target and price_target.get('target_mean'):
            print(f"   Mean Target: €{price_target['target_mean']:.2f}")
            print(f"   High: €{price_target['target_high']:.2f}")
            print(f"   Low: €{price_target['target_low']:.2f}")
            print(f"   Number of Analysts: {price_target['num_analysts']}")
        else:
            print("   ❌ Failed to fetch price targets")


def demo_aggregator(symbol: str = "SAP.DE"):
    """Demonstrate Financial Data Aggregator."""
    print_section("FINANCIAL DATA AGGREGATOR DEMO")

    with FinancialDataAggregator() as aggregator:
        print(f"Fetching complete analysis for {symbol}...\n")
        print("This will take 30-60 seconds due to API rate limits...")
        print("(Alpha Vantage: 5 calls/min, Finnhub: 60 calls/min)\n")

        # Get complete analysis
        analysis = aggregator.get_complete_analysis(
            symbol=symbol,
            include_news=True,
            include_technicals=True,
            include_fundamentals=True,
            news_days_back=7
        )

        if analysis['success']:
            print("✅ Successfully fetched all data!\n")

            # Format for LLM
            formatted = aggregator.format_for_llm(analysis)
            print(formatted)

        else:
            print(f"⚠️ Completed with {len(analysis['errors'])} errors:\n")
            for error in analysis['errors']:
                print(f"   - {error}")

            # Still format whatever we got
            if analysis['data']:
                print("\n" + "=" * 80)
                print("PARTIAL DATA (formatted for LLM):")
                print("=" * 80 + "\n")
                formatted = aggregator.format_for_llm(analysis)
                print(formatted)


def main():
    """Run all demos."""
    print("\n" + "=" * 80)
    print("  FINANCIAL DATA API INTEGRATION - PHASE 3.5.2")
    print("=" * 80)

    # Check API keys
    av_key = os.getenv("ALPHAVANTAGE_API_KEY")
    fh_key = os.getenv("FINNHUB_API_KEY")

    if not av_key:
        print("\n⚠️ WARNING: ALPHAVANTAGE_API_KEY not found in .env")
        print("Get a free key at: https://www.alphavantage.co/support/#api-key\n")

    if not fh_key:
        print("\n⚠️ WARNING: FINNHUB_API_KEY not found in .env")
        print("Get a free key at: https://finnhub.io/register\n")

    if not av_key and not fh_key:
        print("Please add API keys to your .env file and try again.")
        return

    # Menu
    print("\nChoose a demo:")
    print("1. Alpha Vantage API (fundamentals, earnings, technical indicators)")
    print("2. Finnhub API (news, sentiment, analyst ratings)")
    print("3. Financial Data Aggregator (complete analysis)")
    print("4. Run all demos")
    print("0. Exit")

    choice = input("\nEnter your choice (0-4): ").strip()

    if choice == "1":
        if av_key:
            symbol = input("\nEnter stock symbol (e.g., SAP for SAP.DE) [SAP]: ").strip() or "SAP"
            demo_alphavantage(symbol)
        else:
            print("\n❌ Alpha Vantage API key required")

    elif choice == "2":
        if fh_key:
            symbol = input("\nEnter stock symbol (e.g., SAP for SAP.DE) [SAP]: ").strip() or "SAP"
            demo_finnhub(symbol)
        else:
            print("\n❌ Finnhub API key required")

    elif choice == "3":
        if av_key or fh_key:
            symbol = input("\nEnter stock symbol (e.g., SAP.DE) [SAP.DE]: ").strip() or "SAP.DE"
            demo_aggregator(symbol)
        else:
            print("\n❌ At least one API key required")

    elif choice == "4":
        symbol_base = input("\nEnter stock symbol base (e.g., SAP for SAP.DE) [SAP]: ").strip() or "SAP"
        symbol_full = f"{symbol_base}.DE"

        if av_key:
            demo_alphavantage(symbol_base)
        else:
            print("\n⚠️ Skipping Alpha Vantage demo (no API key)")

        if fh_key:
            demo_finnhub(symbol_base)
        else:
            print("\n⚠️ Skipping Finnhub demo (no API key)")

        if av_key or fh_key:
            demo_aggregator(symbol_full)
        else:
            print("\n⚠️ Skipping Aggregator demo (no API keys)")

    elif choice == "0":
        print("\nExiting...")
        return

    else:
        print("\n❌ Invalid choice")
        return

    print("\n" + "=" * 80)
    print("  DEMO COMPLETE")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
