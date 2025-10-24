"""
Interactive Demo: Technical Analysis Service

Demonstrates comprehensive technical analysis capabilities:
- Real-time stock analysis for German stocks
- Technical indicators (RSI, MACD, Bollinger Bands, MA, Stochastic, ADX)
- Chart pattern detection
- Volume analysis
- Trading signals
- LLM-formatted output

Usage:
    python examples/test_technical_analysis.py

Author: Sentiment Arena
Date: 2025-10-23
"""

import sys
import os
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.services.technical_analysis import TechnicalAnalysisService


def print_section_header(title: str):
    """Print a formatted section header."""
    print(f"\n{'=' * 80}")
    print(f" {title}")
    print(f"{'=' * 80}\n")


def print_indicator_details(analysis: dict):
    """Print detailed indicator breakdowns."""
    print_section_header("DETAILED INDICATOR BREAKDOWN")

    indicators = analysis.get("indicators", {})

    # RSI
    if indicators.get("rsi"):
        rsi = indicators["rsi"]
        print("📊 RSI (Relative Strength Index):")
        print(f"   Current: {rsi['value']:.2f}")
        if rsi.get("previous"):
            print(f"   Previous: {rsi['previous']:.2f}")
            change = rsi['value'] - rsi['previous']
            print(f"   Change: {change:+.2f}")
        print()

    # MACD
    if indicators.get("macd"):
        macd = indicators["macd"]
        print("📉 MACD (Moving Average Convergence Divergence):")
        if macd.get("macd"):
            print(f"   MACD Line: {macd['macd']:.4f}")
        if macd.get("signal"):
            print(f"   Signal Line: {macd['signal']:.4f}")
        if macd.get("histogram"):
            print(f"   Histogram: {macd['histogram']:.4f}")
            if macd.get("previous_histogram"):
                if macd["histogram"] > 0 and macd["previous_histogram"] < 0:
                    print("   🟢 BULLISH CROSSOVER DETECTED!")
                elif macd["histogram"] < 0 and macd["previous_histogram"] > 0:
                    print("   🔴 BEARISH CROSSOVER DETECTED!")
        print()

    # Bollinger Bands
    if indicators.get("bollinger_bands"):
        bb = indicators["bollinger_bands"]
        print("📐 Bollinger Bands:")
        if bb.get("upper"):
            print(f"   Upper Band: €{bb['upper']:.2f}")
        if bb.get("middle"):
            print(f"   Middle Band: €{bb['middle']:.2f}")
        if bb.get("lower"):
            print(f"   Lower Band: €{bb['lower']:.2f}")
        if bb.get("percent_b"):
            print(f"   %B: {bb['percent_b']:.2f}")
            if bb["percent_b"] < 0:
                print("   ⬇️ Price below lower band (oversold)")
            elif bb["percent_b"] > 1:
                print("   ⬆️ Price above upper band (overbought)")
        print()

    # Moving Averages
    if indicators.get("moving_averages"):
        ma = indicators["moving_averages"]
        print("📈 Moving Averages:")
        current_price = analysis.get("current_price", 0)
        if ma.get("sma_20"):
            relation = "above" if current_price > ma["sma_20"] else "below"
            print(f"   SMA-20: €{ma['sma_20']:.2f} (Price is {relation})")
        if ma.get("sma_50"):
            relation = "above" if current_price > ma["sma_50"] else "below"
            print(f"   SMA-50: €{ma['sma_50']:.2f} (Price is {relation})")
        if ma.get("sma_200"):
            relation = "above" if current_price > ma["sma_200"] else "below"
            print(f"   SMA-200: €{ma['sma_200']:.2f} (Price is {relation})")
        if ma.get("sma_50") and ma.get("sma_200"):
            if ma["sma_50"] > ma["sma_200"]:
                print("   🟢 Bullish MA alignment (SMA-50 > SMA-200)")
            else:
                print("   🔴 Bearish MA alignment (SMA-50 < SMA-200)")
        print()

    # Stochastic
    if indicators.get("stochastic"):
        stoch = indicators["stochastic"]
        print("🎯 Stochastic Oscillator:")
        if stoch.get("k"):
            print(f"   %K: {stoch['k']:.2f}")
            if stoch["k"] < 20:
                print("   🟢 Oversold condition (< 20)")
            elif stoch["k"] > 80:
                print("   🔴 Overbought condition (> 80)")
        if stoch.get("d"):
            print(f"   %D: {stoch['d']:.2f}")
        print()

    # ADX
    if indicators.get("adx"):
        adx = indicators["adx"]
        print("💪 ADX (Average Directional Index):")
        if adx.get("value"):
            print(f"   ADX: {adx['value']:.2f}")
            if adx["value"] > 25:
                print("   Strong trend detected")
            else:
                print("   Weak or no trend")
        if adx.get("plus_di") and adx.get("minus_di"):
            print(f"   +DI: {adx['plus_di']:.2f}")
            print(f"   -DI: {adx['minus_di']:.2f}")
            if adx["plus_di"] > adx["minus_di"]:
                print("   🟢 Uptrend direction")
            else:
                print("   🔴 Downtrend direction")
        print()

    # ATR
    if indicators.get("atr"):
        atr = indicators["atr"]
        if atr.get("value"):
            print("📏 ATR (Average True Range):")
            print(f"   ATR: €{atr['value']:.2f}")
            print(f"   Volatility Metric: {(atr['value'] / analysis.get('current_price', 1) * 100):.2f}%")
            print()


def print_patterns(analysis: dict):
    """Print chart pattern details."""
    print_section_header("CHART PATTERNS")

    patterns = analysis.get("patterns", {})

    print(f"📊 Trend: {patterns.get('trend', 'unknown').upper()}")
    print(f"🛡️ Support: €{patterns.get('support', 0):.2f} ({patterns.get('distance_to_support', 0):.1f}% below current)")
    print(f"🚧 Resistance: €{patterns.get('resistance', 0):.2f} ({patterns.get('distance_to_resistance', 0):.1f}% above current)")

    if patterns.get("breakout"):
        print(f"\n⚡ BREAKOUT: {patterns['breakout'].replace('_', ' ').upper()}")

    if patterns.get("golden_death_cross"):
        cross_type = "GOLDEN CROSS" if patterns["golden_death_cross"] == "golden_cross" else "DEATH CROSS"
        emoji = "🟢" if patterns["golden_death_cross"] == "golden_cross" else "🔴"
        print(f"\n{emoji} {cross_type} DETECTED!")


def print_volume(analysis: dict):
    """Print volume analysis details."""
    print_section_header("VOLUME ANALYSIS")

    vol = analysis.get("volume_analysis", {})

    print(f"Current Volume: {vol.get('current_volume', 0):,}")
    print(f"Average Volume: {vol.get('average_volume', 0):,}")
    print(f"Volume Ratio: {vol.get('volume_ratio', 0):.2f}x")

    if vol.get("above_average"):
        print("📈 Volume is ABOVE average")
    else:
        print("📉 Volume is BELOW average")

    print(f"\nVolume Trend: {vol.get('volume_trend', 'unknown').upper()}")
    print(f"OBV Trend: {vol.get('obv_trend', 'unknown').upper()}")

    if vol.get("obv"):
        print(f"OBV: {vol['obv']:,.0f}")


def print_signals(analysis: dict):
    """Print trading signals."""
    print_section_header("TRADING SIGNALS")

    signals = analysis.get("signals", {})

    # Overall signal with emoji
    overall = signals.get("overall_signal", "neutral").upper()
    emoji = "🟢" if overall == "BULLISH" else "🔴" if overall == "BEARISH" else "🟡"
    print(f"{emoji} Overall Signal: {overall}\n")

    # Bullish signals
    bullish = signals.get("bullish_signals", [])
    if bullish:
        print("🟢 Bullish Signals:")
        for sig in bullish:
            print(f"   ✓ {sig}")
        print()

    # Bearish signals
    bearish = signals.get("bearish_signals", [])
    if bearish:
        print("🔴 Bearish Signals:")
        for sig in bearish:
            print(f"   ✗ {sig}")
        print()

    # Neutral signals
    neutral = signals.get("neutral_signals", [])
    if neutral:
        print("🟡 Neutral Signals:")
        for sig in neutral:
            print(f"   • {sig}")


def print_context(analysis: dict):
    """Print historical context."""
    print_section_header("HISTORICAL CONTEXT")

    context = analysis.get("context", {})

    # Price changes
    if context.get("price_changes"):
        pc = context["price_changes"]
        print("📅 Price Changes:")
        print(f"   1-Day: {pc.get('1_day', 0):+.2f}%")
        print(f"   5-Day: {pc.get('5_day', 0):+.2f}%")
        print(f"   20-Day: {pc.get('20_day', 0):+.2f}%")
        print()

    # 52-week high/low
    if context.get("52_week"):
        wk52 = context["52_week"]
        print("📊 52-Week Range:")
        print(f"   High: €{wk52.get('high', 0):.2f} ({wk52.get('distance_from_high', 0):.1f}% below)")
        print(f"   Low: €{wk52.get('low', 0):.2f} ({wk52.get('distance_from_low', 0):.1f}% above)")


def demo_stock_analysis(symbol: str):
    """Run complete technical analysis demo for a stock."""
    print_section_header(f"TECHNICAL ANALYSIS DEMO: {symbol}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Initialize service
    print("Initializing Technical Analysis Service...")
    ta_service = TechnicalAnalysisService(lookback_days=90)

    # Fetch and analyze
    print(f"Fetching data for {symbol}...\n")
    analysis = ta_service.get_technical_analysis(symbol)

    if not analysis.get("success"):
        print(f"❌ Error: {analysis.get('error', 'Unknown error')}")
        return

    print(f"✅ Analysis complete for {symbol}")
    print(f"Current Price: €{analysis.get('current_price', 0):.2f}\n")

    # Print all sections
    print_indicator_details(analysis)
    print_patterns(analysis)
    print_volume(analysis)
    print_signals(analysis)
    print_context(analysis)

    # LLM-formatted output
    print_section_header("LLM-FORMATTED OUTPUT")
    print(analysis.get("llm_formatted", ""))


def main():
    """Main demo function."""
    print("\n" + "=" * 80)
    print(" TECHNICAL ANALYSIS SERVICE - INTERACTIVE DEMO")
    print("=" * 80)
    print("\nThis demo showcases comprehensive technical analysis for German stocks.")
    print("Using pandas-ta library with 90-day lookback period.\n")

    # Demo stocks
    stocks = [
        ("SAP.DE", "SAP SE"),
        ("BMW.DE", "BMW AG"),
        ("SIE.DE", "Siemens AG")
    ]

    print("Available demo stocks:")
    for i, (symbol, name) in enumerate(stocks, 1):
        print(f"  {i}. {symbol} - {name}")
    print(f"  {len(stocks) + 1}. Custom symbol")
    print(f"  {len(stocks) + 2}. Exit")

    while True:
        try:
            choice = input("\nSelect option (1-5): ").strip()

            if choice == str(len(stocks) + 2):
                print("\nExiting demo. Goodbye!")
                break

            if choice == str(len(stocks) + 1):
                custom_symbol = input("Enter stock symbol (e.g., ADS.DE): ").strip().upper()
                if not custom_symbol.endswith('.DE'):
                    custom_symbol += '.DE'
                demo_stock_analysis(custom_symbol)
            elif choice.isdigit() and 1 <= int(choice) <= len(stocks):
                symbol, name = stocks[int(choice) - 1]
                demo_stock_analysis(symbol)
            else:
                print("Invalid choice. Please try again.")

        except KeyboardInterrupt:
            print("\n\nInterrupted. Exiting...")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            print("Please try again.")

    print("\n" + "=" * 80)
    print(" Demo complete. Thank you for using Technical Analysis Service!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
