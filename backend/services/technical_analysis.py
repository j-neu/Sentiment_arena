"""
Technical Analysis Service

Provides comprehensive technical analysis using pandas-ta library:
- Technical indicators (RSI, MACD, Bollinger Bands, Moving Averages, Stochastic, ADX)
- Chart pattern detection (support/resistance, breakouts, trends)
- Volume analysis (OBV, volume profile, above/below average)
- Signal generation (overbought/oversold, bullish/bearish crossovers)
- Historical context and comparisons
- LLM-formatted output with clear explanations

Author: Sentiment Arena
Date: 2025-10-23
"""

import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from backend.logger import get_logger

logger = get_logger(__name__)


class TechnicalAnalysisService:
    """
    Comprehensive technical analysis service using pandas-ta.

    Provides technical indicators, chart patterns, volume analysis,
    and LLM-formatted insights for trading decisions.
    """

    def __init__(self, lookback_days: int = 90):
        """
        Initialize technical analysis service.

        Args:
            lookback_days: Number of days of historical data to fetch (default: 90)
        """
        self.lookback_days = lookback_days
        logger.info(f"TechnicalAnalysisService initialized with {lookback_days} day lookback")

    def get_technical_analysis(self, symbol: str) -> Dict[str, Any]:
        """
        Get comprehensive technical analysis for a stock.

        Args:
            symbol: Stock symbol (e.g., "SAP.DE")

        Returns:
            Dictionary containing all technical analysis data
        """
        try:
            logger.info(f"Starting technical analysis for {symbol}")

            # Fetch historical data
            df = self._fetch_historical_data(symbol)
            if df is None or len(df) < 20:
                logger.warning(f"Insufficient data for {symbol}")
                return self._empty_analysis(symbol, "Insufficient historical data")

            # Calculate all indicators
            indicators = self._calculate_indicators(df)

            # Detect patterns
            patterns = self._detect_patterns(df)

            # Analyze volume
            volume_analysis = self._analyze_volume(df)

            # Generate signals
            signals = self._generate_signals(df, indicators)

            # Get historical context
            context = self._get_historical_context(df, indicators)

            # Format for LLM
            llm_output = self._format_for_llm(
                symbol=symbol,
                current_price=df['Close'].iloc[-1],
                indicators=indicators,
                patterns=patterns,
                volume_analysis=volume_analysis,
                signals=signals,
                context=context
            )

            logger.info(f"Technical analysis complete for {symbol}")

            return {
                "success": True,
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "current_price": float(df['Close'].iloc[-1]),
                "indicators": indicators,
                "patterns": patterns,
                "volume_analysis": volume_analysis,
                "signals": signals,
                "context": context,
                "llm_formatted": llm_output
            }

        except Exception as e:
            logger.error(f"Error in technical analysis for {symbol}: {str(e)}", exc_info=True)
            return self._empty_analysis(symbol, str(e))

    def _fetch_historical_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch historical price data from yfinance."""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.lookback_days)

            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date)

            if df.empty:
                logger.warning(f"No data returned for {symbol}")
                return None

            logger.debug(f"Fetched {len(df)} days of data for {symbol}")
            return df

        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {str(e)}")
            return None

    def _calculate_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate all technical indicators."""
        try:
            def safe_get_value(series_or_df, column=None, index=-1):
                """Safely get value from series or dataframe."""
                try:
                    if series_or_df is None:
                        return None
                    if isinstance(series_or_df, pd.DataFrame):
                        if column and column in series_or_df.columns:
                            return float(series_or_df[column].iloc[index])
                        # Try to find column with partial match
                        for col in series_or_df.columns:
                            if column and column.split('_')[0] in col:
                                return float(series_or_df[col].iloc[index])
                        return None
                    elif isinstance(series_or_df, pd.Series):
                        if len(series_or_df) > abs(index):
                            return float(series_or_df.iloc[index])
                    return None
                except:
                    return None

            # RSI (14-period)
            rsi = ta.rsi(df['Close'], length=14)

            # MACD
            macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)

            # Bollinger Bands
            bbands = ta.bbands(df['Close'], length=20, std=2)

            # Moving Averages
            sma_20 = ta.sma(df['Close'], length=20)
            sma_50 = ta.sma(df['Close'], length=50)
            sma_200 = ta.sma(df['Close'], length=200)
            ema_12 = ta.ema(df['Close'], length=12)
            ema_26 = ta.ema(df['Close'], length=26)

            # Stochastic Oscillator
            stoch = ta.stoch(df['High'], df['Low'], df['Close'], k=14, d=3)

            # ADX (Average Directional Index) - Trend Strength
            adx = ta.adx(df['High'], df['Low'], df['Close'], length=14)

            # ATR (Average True Range) - Volatility
            atr = ta.atr(df['High'], df['Low'], df['Close'], length=14)

            indicators = {
                "rsi": {
                    "value": safe_get_value(rsi, index=-1),
                    "previous": safe_get_value(rsi, index=-2)
                },
                "macd": {
                    "macd": safe_get_value(macd, 'MACD', -1),
                    "signal": safe_get_value(macd, 'MACDs', -1),
                    "histogram": safe_get_value(macd, 'MACDh', -1),
                    "previous_histogram": safe_get_value(macd, 'MACDh', -2)
                },
                "bollinger_bands": {
                    "upper": safe_get_value(bbands, 'BBU', -1),
                    "middle": safe_get_value(bbands, 'BBM', -1),
                    "lower": safe_get_value(bbands, 'BBL', -1),
                    "bandwidth": safe_get_value(bbands, 'BBB', -1),
                    "percent_b": safe_get_value(bbands, 'BBP', -1)
                },
                "moving_averages": {
                    "sma_20": safe_get_value(sma_20, index=-1),
                    "sma_50": safe_get_value(sma_50, index=-1),
                    "sma_200": safe_get_value(sma_200, index=-1),
                    "ema_12": safe_get_value(ema_12, index=-1),
                    "ema_26": safe_get_value(ema_26, index=-1)
                },
                "stochastic": {
                    "k": safe_get_value(stoch, 'STOCHk', -1),
                    "d": safe_get_value(stoch, 'STOCHd', -1)
                },
                "adx": {
                    "value": safe_get_value(adx, 'ADX', -1),
                    "plus_di": safe_get_value(adx, 'DMP', -1),
                    "minus_di": safe_get_value(adx, 'DMN', -1)
                },
                "atr": {
                    "value": safe_get_value(atr, index=-1)
                }
            }

            return indicators

        except Exception as e:
            logger.error(f"Error calculating indicators: {str(e)}", exc_info=True)
            return {}

    def _detect_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect chart patterns (support/resistance, breakouts, trends)."""
        try:
            current_price = df['Close'].iloc[-1]

            # Calculate support and resistance using recent highs/lows
            lookback = min(20, len(df))
            recent_highs = df['High'].tail(lookback)
            recent_lows = df['Low'].tail(lookback)

            # Support: Average of recent lows
            support = float(recent_lows.min())

            # Resistance: Average of recent highs
            resistance = float(recent_highs.max())

            # Detect breakout
            prev_resistance = float(df['High'].tail(lookback).iloc[:-5].max())
            prev_support = float(df['Low'].tail(lookback).iloc[:-5].min())

            breakout = None
            if current_price > prev_resistance:
                breakout = "bullish_breakout"
            elif current_price < prev_support:
                breakout = "bearish_breakdown"

            # Trend detection using price action
            sma_50 = ta.sma(df['Close'], length=50)
            sma_200 = ta.sma(df['Close'], length=200)

            trend = "neutral"
            if sma_50 is not None and sma_200 is not None and len(sma_50) > 0 and len(sma_200) > 0:
                if sma_50.iloc[-1] > sma_200.iloc[-1]:
                    trend = "bullish"
                else:
                    trend = "bearish"

            # Detect Golden Cross / Death Cross
            cross = None
            if sma_50 is not None and sma_200 is not None and len(sma_50) > 1 and len(sma_200) > 1:
                if sma_50.iloc[-2] < sma_200.iloc[-2] and sma_50.iloc[-1] > sma_200.iloc[-1]:
                    cross = "golden_cross"
                elif sma_50.iloc[-2] > sma_200.iloc[-2] and sma_50.iloc[-1] < sma_200.iloc[-1]:
                    cross = "death_cross"

            patterns = {
                "support": support,
                "resistance": resistance,
                "breakout": breakout,
                "trend": trend,
                "golden_death_cross": cross,
                "distance_to_support": float(((current_price - support) / current_price) * 100),
                "distance_to_resistance": float(((resistance - current_price) / current_price) * 100)
            }

            return patterns

        except Exception as e:
            logger.error(f"Error detecting patterns: {str(e)}", exc_info=True)
            return {}

    def _analyze_volume(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze volume patterns."""
        try:
            # On-Balance Volume (OBV)
            obv = ta.obv(df['Close'], df['Volume'])

            # Volume moving average
            volume_sma_20 = ta.sma(df['Volume'], length=20)

            current_volume = df['Volume'].iloc[-1]
            avg_volume = volume_sma_20.iloc[-1] if volume_sma_20 is not None and len(volume_sma_20) > 0 else df['Volume'].mean()

            # Volume trend (increasing or decreasing)
            recent_volumes = df['Volume'].tail(5)
            volume_trend = "increasing" if recent_volumes.iloc[-1] > recent_volumes.iloc[0] else "decreasing"

            volume_analysis = {
                "current_volume": int(current_volume),
                "average_volume": int(avg_volume),
                "volume_ratio": float(current_volume / avg_volume) if avg_volume > 0 else 1.0,
                "obv": float(obv.iloc[-1]) if obv is not None and len(obv) > 0 else None,
                "obv_trend": "bullish" if obv is not None and len(obv) > 5 and obv.iloc[-1] > obv.iloc[-5] else "bearish",
                "volume_trend": volume_trend,
                "above_average": bool(current_volume > avg_volume)
            }

            return volume_analysis

        except Exception as e:
            logger.error(f"Error analyzing volume: {str(e)}", exc_info=True)
            return {}

    def _generate_signals(self, df: pd.DataFrame, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """Generate trading signals from indicators."""
        try:
            signals = {
                "overall_signal": "neutral",
                "bullish_signals": [],
                "bearish_signals": [],
                "neutral_signals": []
            }

            # RSI Signals
            if indicators.get("rsi", {}).get("value"):
                rsi_val = indicators["rsi"]["value"]
                if rsi_val < 30:
                    signals["bullish_signals"].append("RSI oversold (< 30)")
                elif rsi_val > 70:
                    signals["bearish_signals"].append("RSI overbought (> 70)")
                else:
                    signals["neutral_signals"].append(f"RSI neutral ({rsi_val:.1f})")

            # MACD Signals
            macd = indicators.get("macd", {})
            if macd.get("histogram") is not None and macd.get("previous_histogram") is not None:
                if macd["histogram"] > 0 and macd["previous_histogram"] < 0:
                    signals["bullish_signals"].append("MACD bullish crossover")
                elif macd["histogram"] < 0 and macd["previous_histogram"] > 0:
                    signals["bearish_signals"].append("MACD bearish crossover")

            # Bollinger Bands Signals
            bbands = indicators.get("bollinger_bands", {})
            if bbands.get("percent_b") is not None:
                percent_b = bbands["percent_b"]
                if percent_b < 0:
                    signals["bullish_signals"].append("Price below lower Bollinger Band (oversold)")
                elif percent_b > 1:
                    signals["bearish_signals"].append("Price above upper Bollinger Band (overbought)")

            # Moving Average Signals
            ma = indicators.get("moving_averages", {})
            current_price = df['Close'].iloc[-1]

            if ma.get("sma_50") and ma.get("sma_200"):
                if ma["sma_50"] > ma["sma_200"]:
                    signals["bullish_signals"].append("50-day SMA above 200-day SMA (bullish trend)")
                else:
                    signals["bearish_signals"].append("50-day SMA below 200-day SMA (bearish trend)")

            if ma.get("sma_20"):
                if current_price > ma["sma_20"]:
                    signals["bullish_signals"].append("Price above 20-day SMA")
                else:
                    signals["bearish_signals"].append("Price below 20-day SMA")

            # Stochastic Signals
            stoch = indicators.get("stochastic", {})
            if stoch.get("k") is not None:
                if stoch["k"] < 20:
                    signals["bullish_signals"].append("Stochastic oversold (< 20)")
                elif stoch["k"] > 80:
                    signals["bearish_signals"].append("Stochastic overbought (> 80)")

            # ADX Trend Strength
            adx = indicators.get("adx", {})
            if adx.get("value") is not None:
                if adx["value"] > 25:
                    if adx.get("plus_di", 0) > adx.get("minus_di", 0):
                        signals["bullish_signals"].append(f"Strong uptrend (ADX: {adx['value']:.1f})")
                    else:
                        signals["bearish_signals"].append(f"Strong downtrend (ADX: {adx['value']:.1f})")
                else:
                    signals["neutral_signals"].append(f"Weak trend (ADX: {adx['value']:.1f})")

            # Overall signal
            bullish_count = len(signals["bullish_signals"])
            bearish_count = len(signals["bearish_signals"])

            if bullish_count > bearish_count + 2:
                signals["overall_signal"] = "bullish"
            elif bearish_count > bullish_count + 2:
                signals["overall_signal"] = "bearish"
            else:
                signals["overall_signal"] = "neutral"

            return signals

        except Exception as e:
            logger.error(f"Error generating signals: {str(e)}", exc_info=True)
            return {"overall_signal": "neutral", "bullish_signals": [], "bearish_signals": [], "neutral_signals": []}

    def _get_historical_context(self, df: pd.DataFrame, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """Get historical context for current indicators."""
        try:
            current_price = df['Close'].iloc[-1]

            # Price changes
            price_1d_change = ((current_price - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100 if len(df) > 1 else 0
            price_5d_change = ((current_price - df['Close'].iloc[-6]) / df['Close'].iloc[-6]) * 100 if len(df) > 5 else 0
            price_20d_change = ((current_price - df['Close'].iloc[-21]) / df['Close'].iloc[-21]) * 100 if len(df) > 20 else 0

            # 52-week high/low
            high_52w = df['High'].max()
            low_52w = df['Low'].min()

            context = {
                "price_changes": {
                    "1_day": float(price_1d_change),
                    "5_day": float(price_5d_change),
                    "20_day": float(price_20d_change)
                },
                "52_week": {
                    "high": float(high_52w),
                    "low": float(low_52w),
                    "distance_from_high": float(((high_52w - current_price) / high_52w) * 100),
                    "distance_from_low": float(((current_price - low_52w) / low_52w) * 100)
                },
                "volatility": {
                    "atr": indicators.get("atr", {}).get("value"),
                    "bollinger_bandwidth": indicators.get("bollinger_bands", {}).get("bandwidth")
                }
            }

            return context

        except Exception as e:
            logger.error(f"Error getting historical context: {str(e)}", exc_info=True)
            return {}

    def _format_for_llm(
        self,
        symbol: str,
        current_price: float,
        indicators: Dict[str, Any],
        patterns: Dict[str, Any],
        volume_analysis: Dict[str, Any],
        signals: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """Format technical analysis for LLM consumption."""

        output = f"📊 TECHNICAL ANALYSIS: {symbol}\n"
        output += f"Current Price: €{current_price:.2f}\n\n"

        # Overall Signal
        signal_emoji = "🟢" if signals["overall_signal"] == "bullish" else "🔴" if signals["overall_signal"] == "bearish" else "🟡"
        output += f"{signal_emoji} Overall Technical Signal: {signals['overall_signal'].upper()}\n\n"

        # Key Indicators
        output += "📈 KEY INDICATORS:\n"

        rsi = indicators.get("rsi", {})
        if rsi.get("value"):
            rsi_status = "Oversold" if rsi["value"] < 30 else "Overbought" if rsi["value"] > 70 else "Neutral"
            output += f"  • RSI (14): {rsi['value']:.1f} - {rsi_status}\n"

        macd = indicators.get("macd", {})
        if macd.get("histogram"):
            macd_signal = "Bullish" if macd["histogram"] > 0 else "Bearish"
            output += f"  • MACD Histogram: {macd['histogram']:.3f} - {macd_signal}\n"

        stoch = indicators.get("stochastic", {})
        if stoch.get("k"):
            stoch_status = "Oversold" if stoch["k"] < 20 else "Overbought" if stoch["k"] > 80 else "Neutral"
            output += f"  • Stochastic %K: {stoch['k']:.1f} - {stoch_status}\n"

        adx = indicators.get("adx", {})
        if adx.get("value"):
            trend_strength = "Strong" if adx["value"] > 25 else "Weak"
            output += f"  • ADX (14): {adx['value']:.1f} - {trend_strength} trend\n"

        # Moving Averages
        output += "\n📉 MOVING AVERAGES:\n"
        ma = indicators.get("moving_averages", {})
        if ma.get("sma_20"):
            ma_position = "Above" if current_price > ma["sma_20"] else "Below"
            output += f"  • Price vs 20-day SMA: {ma_position} (€{ma['sma_20']:.2f})\n"
        if ma.get("sma_50"):
            ma_position = "Above" if current_price > ma["sma_50"] else "Below"
            output += f"  • Price vs 50-day SMA: {ma_position} (€{ma['sma_50']:.2f})\n"
        if ma.get("sma_200"):
            ma_position = "Above" if current_price > ma["sma_200"] else "Below"
            output += f"  • Price vs 200-day SMA: {ma_position} (€{ma['sma_200']:.2f})\n"

        # Chart Patterns
        output += "\n🔍 CHART PATTERNS:\n"
        output += f"  • Trend: {patterns.get('trend', 'unknown').upper()}\n"
        output += f"  • Support Level: €{patterns.get('support', 0):.2f} ({patterns.get('distance_to_support', 0):.1f}% below current)\n"
        output += f"  • Resistance Level: €{patterns.get('resistance', 0):.2f} ({patterns.get('distance_to_resistance', 0):.1f}% above current)\n"

        if patterns.get("breakout"):
            output += f"  • ⚡ BREAKOUT DETECTED: {patterns['breakout'].replace('_', ' ').upper()}\n"

        if patterns.get("golden_death_cross"):
            cross_type = "GOLDEN CROSS" if patterns["golden_death_cross"] == "golden_cross" else "DEATH CROSS"
            output += f"  • ⚠️ {cross_type} DETECTED!\n"

        # Volume Analysis
        output += "\n📊 VOLUME ANALYSIS:\n"
        vol_status = "Above average" if volume_analysis.get("above_average") else "Below average"
        vol_ratio = volume_analysis.get("volume_ratio", 1.0)
        output += f"  • Current Volume: {vol_status} ({vol_ratio:.2f}x average)\n"
        output += f"  • Volume Trend: {volume_analysis.get('volume_trend', 'unknown').upper()}\n"
        output += f"  • OBV Trend: {volume_analysis.get('obv_trend', 'unknown').upper()}\n"

        # Signals
        output += "\n🎯 TRADING SIGNALS:\n"
        if signals.get("bullish_signals"):
            output += "  Bullish Signals:\n"
            for sig in signals["bullish_signals"]:
                output += f"    ✅ {sig}\n"

        if signals.get("bearish_signals"):
            output += "  Bearish Signals:\n"
            for sig in signals["bearish_signals"]:
                output += f"    ❌ {sig}\n"

        # Historical Context
        output += "\n📅 HISTORICAL CONTEXT:\n"
        price_changes = context.get("price_changes", {})
        output += f"  • 1-Day Change: {price_changes.get('1_day', 0):+.2f}%\n"
        output += f"  • 5-Day Change: {price_changes.get('5_day', 0):+.2f}%\n"
        output += f"  • 20-Day Change: {price_changes.get('20_day', 0):+.2f}%\n"

        week_52 = context.get("52_week", {})
        output += f"  • 52-Week High: €{week_52.get('high', 0):.2f} ({week_52.get('distance_from_high', 0):.1f}% below)\n"
        output += f"  • 52-Week Low: €{week_52.get('low', 0):.2f} ({week_52.get('distance_from_low', 0):.1f}% above)\n"

        return output

    def _empty_analysis(self, symbol: str, error: str) -> Dict[str, Any]:
        """Return empty analysis structure on error."""
        return {
            "success": False,
            "symbol": symbol,
            "error": error,
            "timestamp": datetime.now().isoformat(),
            "indicators": {},
            "patterns": {},
            "volume_analysis": {},
            "signals": {"overall_signal": "neutral", "bullish_signals": [], "bearish_signals": [], "neutral_signals": []},
            "context": {},
            "llm_formatted": f"⚠️ Technical analysis unavailable for {symbol}: {error}"
        }
