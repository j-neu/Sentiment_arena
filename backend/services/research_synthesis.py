"""
Research Synthesis Service

Multi-stage research pipeline that:
1. Collects raw data from multiple sources
2. Uses LLM to synthesize and analyze research
3. Assesses source credibility
4. Identifies contradictions and data gaps
5. Produces high-quality briefings
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
import json

from backend.logger import get_logger
from backend.services.openrouter_client import OpenRouterClient
from backend.services.research_model_mapper import ResearchModelMapper
from backend.services.research import ResearchService

logger = get_logger(__name__)


class ResearchSynthesizer:
    """
    Synthesizes raw research data into high-quality, verified briefings.

    Uses cheaper LLM from the same company to analyze and filter research
    before it reaches the premium trading model.
    """

    # Source credibility tiers
    HIGH_CREDIBILITY_SOURCES = [
        "reuters.com", "bloomberg.com", "wsj.com", "ft.com",
        "sec.gov", "marketwatch.com", "cnbc.com", "barrons.com"
    ]

    MEDIUM_CREDIBILITY_SOURCES = [
        "yahoo.com", "finance.yahoo.com", "seekingalpha.com",
        "fool.com", "benzinga.com", "thefly.com", "biztoc.com"
    ]

    def __init__(
        self,
        openrouter_client: OpenRouterClient,
        research_service: ResearchService,
        trading_model: str
    ):
        """
        Initialize research synthesizer.

        Args:
            openrouter_client: OpenRouter API client
            research_service: Research service for web searches
            trading_model: Trading model identifier
        """
        self.client = openrouter_client
        self.research_service = research_service
        self.trading_model = trading_model
        self.research_model = ResearchModelMapper.get_research_model(trading_model)

        logger.info(
            f"ResearchSynthesizer initialized: trading_model={trading_model}, "
            f"research_model={self.research_model}"
        )

    def synthesize_stock_research(
        self,
        symbol: str,
        raw_results: List[Dict[str, Any]],
        existing_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Synthesize raw search results into a comprehensive briefing.

        Args:
            symbol: Stock symbol (e.g., "SAP.DE")
            raw_results: Raw search results from web/APIs
            existing_data: Optional existing data (prices, positions, etc.)

        Returns:
            Dictionary with synthesized briefing and metadata
        """
        logger.info(f"Synthesizing research for {symbol} from {len(raw_results)} sources")

        # Assess source credibility
        credibility_ratings = self._assess_source_credibility(raw_results)

        # Build synthesis prompt
        prompt = self._build_synthesis_prompt(
            symbol=symbol,
            raw_results=raw_results,
            credibility_ratings=credibility_ratings,
            existing_data=existing_data
        )

        try:
            # Call research LLM for synthesis
            response = self.client.get_completion_text(
                model=self.research_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional financial analyst synthesizing research data."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for factual synthesis
                max_tokens=2000
            )

            # Parse synthesized briefing
            briefing = self._parse_synthesis(response)

            # Add metadata
            briefing["metadata"] = {
                "symbol": symbol,
                "num_sources": len(raw_results),
                "credibility_breakdown": self._credibility_breakdown(credibility_ratings),
                "synthesis_model": self.research_model,
                "timestamp": datetime.now().isoformat()
            }

            logger.info(f"Successfully synthesized briefing for {symbol}")
            return briefing

        except Exception as e:
            logger.error(f"Error synthesizing research for {symbol}: {e}")
            # Return fallback briefing
            return self._fallback_briefing(symbol, raw_results)

    def _assess_source_credibility(
        self,
        raw_results: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        Assess credibility of each source.

        Args:
            raw_results: List of search results with URLs

        Returns:
            Dictionary mapping URLs to credibility ratings (high/medium/low)
        """
        ratings = {}

        for result in raw_results:
            url = result.get("url", "")
            domain = self._extract_domain(url)

            if any(hc in domain for hc in self.HIGH_CREDIBILITY_SOURCES):
                ratings[url] = "high"
            elif any(mc in domain for mc in self.MEDIUM_CREDIBILITY_SOURCES):
                ratings[url] = "medium"
            else:
                ratings[url] = "low"

        return ratings

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            # Simple domain extraction
            if "://" in url:
                domain = url.split("://")[1].split("/")[0]
            else:
                domain = url.split("/")[0]
            return domain.lower()
        except:
            return ""

    def _credibility_breakdown(
        self,
        ratings: Dict[str, str]
    ) -> Dict[str, int]:
        """Get counts of sources by credibility."""
        breakdown = {"high": 0, "medium": 0, "low": 0}
        for rating in ratings.values():
            breakdown[rating] = breakdown.get(rating, 0) + 1
        return breakdown

    def _build_synthesis_prompt(
        self,
        symbol: str,
        raw_results: List[Dict[str, Any]],
        credibility_ratings: Dict[str, str],
        existing_data: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt for research synthesis."""
        company_name = symbol.replace(".DE", "")

        # Format raw results with credibility ratings
        formatted_sources = []
        for i, result in enumerate(raw_results, 1):
            url = result.get("url", "")
            credibility = credibility_ratings.get(url, "unknown")
            formatted_sources.append(
                f"[{i}] ({credibility.upper()} credibility)\n"
                f"Title: {result.get('title', 'N/A')}\n"
                f"Source: {url}\n"
                f"Content: {result.get('snippet', 'N/A')}\n"
            )

        sources_text = "\n".join(formatted_sources)

        # Format existing data
        existing_text = ""
        if existing_data:
            existing_text = f"\n=== EXISTING DATA ===\n{json.dumps(existing_data, indent=2)}\n"

        prompt = f"""Synthesize the following research data for {symbol} ({company_name}) into a comprehensive, objective briefing.

{existing_text}
=== RAW RESEARCH SOURCES ===
{sources_text}

=== YOUR TASK ===
Analyze all sources and create a comprehensive briefing with the following sections:

1. **Recent Events** (last 7 days)
   - Key announcements, earnings, price movements
   - Include specific dates and numbers
   - Only include if verified by credible sources
   - Categorize events: Earnings, M&A, Guidance, Product launches, Legal/Regulatory

2. **Sentiment Analysis**
   - Overall market sentiment (bullish/bearish/neutral)
   - Analyst consensus and ratings with specific counts
   - News sentiment trend with percentage breakdown
   - Social media sentiment if available
   - Note if sources conflict with severity rating

3. **Risk Factors**
   - Company-specific risks (operational, financial, competitive)
   - Sector/macro risks (economic, regulatory, geopolitical)
   - Any red flags or concerns with timeline
   - Rate each risk (high/medium/low severity) with impact timeframe
   - Risk mitigation factors if mentioned

4. **Technical Analysis Summary**
   - Key technical indicators and signals
   - Support and resistance levels
   - Recent price patterns and trends
   - Volume analysis and momentum
   - Trading signals (overbought/oversold, breakouts)

5. **Fundamental Metrics**
   - Valuation metrics (P/E, P/B, P/S ratios)
   - Growth metrics (revenue, earnings growth rates)
   - Profitability metrics (margins, ROE, ROA)
   - Financial health metrics (debt ratios, cash flow)
   - Comparison to sector averages and historical ranges

6. **Opportunities**
   - Growth catalysts with timeline
   - Positive developments with expected impact
   - Competitive advantages and moats
   - Market expansion opportunities
   - Undervaluation indicators

7. **Contextual Information**
   - Sector performance comparison (relative to peers)
   - Peer stock comparison (key metrics)
   - Historical volatility context (current vs. historical)
   - Market regime identification (bull/bear/sideways)
   - Macroeconomic factors affecting the stock

8. **Uncertainty Quantification**
   - Confidence levels for each data point (High/Medium/Low)
   - Data freshness indicators (how recent is each piece of information)
   - Missing information explicitly stated
   - Probability ranges for key forecasts
   - Risk-adjusted perspective on opportunities

9. **Source Quality Assessment**
   - Credibility breakdown with percentages
   - Contradiction analysis with resolution attempts
   - Information completeness assessment
   - Source diversity evaluation
   - Reliability scoring for key claims

10. **Key Takeaways**
    - 5-7 bullet points summarizing the most important insights
    - Actionable information for trading decisions
    - Priority ranking of insights by importance
    - Time-sensitive information highlighted
    - Risk-reward assessment summary

CRITICAL REQUIREMENTS:
- Prioritize HIGH credibility sources over medium/low
- If sources contradict, note the contradiction explicitly with resolution attempt
- If information is unverified or from low-credibility sources, flag it
- Be objective - avoid promotional or sensationalist language
- Include specific numbers, dates, and facts with sources
- If data is missing or uncertain, explicitly state it
- Quantify uncertainty wherever possible
- Provide context for all metrics (comparisons, historical ranges)
- Include time horizons for all forecasts and risks

Return your analysis as a JSON object with this structure:
{{
    "recent_events": {{
        "earnings": "...",
        "m_a": "...",
        "guidance": "...",
        "product_launches": "...",
        "legal_regulatory": "..."
    }},
    "sentiment_analysis": {{
        "overall": "bullish|bearish|neutral",
        "analyst_consensus": {{
            "rating": "BUY|HOLD|SELL",
            "count": "...",
            "price_target": "..."
        }},
        "news_sentiment": {{
            "bullish_percent": "...",
            "bearish_percent": "...",
            "neutral_percent": "..."
        }},
        "social_media": "...",
        "contradictions": {{
            "detected": true|false,
            "severity": "high|medium|low",
            "description": "..."
        }}
    }},
    "risk_factors": {{
        "company_specific": [
            {{
                "risk": "...",
                "severity": "high|medium|low",
                "timeframe": "...",
                "mitigation": "..."
            }}
        ],
        "sector_macro": [
            {{
                "risk": "...",
                "severity": "high|medium|low",
                "timeframe": "..."
            }}
        ]
    }},
    "technical_analysis": {{
        "indicators": {{
            "rsi": "...",
            "macd": "...",
            "moving_averages": "..."
        }},
        "levels": {{
            "support": "...",
            "resistance": "..."
        }},
        "patterns": "...",
        "signals": ["...", "..."]
    }},
    "fundamental_metrics": {{
        "valuation": {{
            "pe_ratio": "...",
            "pb_ratio": "...",
            "ps_ratio": "...",
            "sector_comparison": "..."
        }},
        "growth": {{
            "revenue_growth": "...",
            "earnings_growth": "..."
        }},
        "profitability": {{
            "gross_margin": "...",
            "operating_margin": "...",
            "net_margin": "...",
            "roe": "...",
            "roa": "..."
        }},
        "financial_health": {{
            "debt_to_equity": "...",
            "current_ratio": "...",
            "cash_flow": "..."
        }}
    }},
    "opportunities": [
        {{
            "opportunity": "...",
            "timeline": "...",
            "impact": "high|medium|low",
            "probability": "high|medium|low"
        }}
    ],
    "contextual_information": {{
        "sector_performance": "...",
        "peer_comparison": {{
            "metric": "...",
            "company_value": "...",
            "peer_average": "...",
            "percentile": "..."
        }},
        "historical_volatility": {{
            "current": "...",
            "historical_average": "...",
            "percentile": "..."
        }},
        "market_regime": "bull|bear|sideways",
        "macroeconomic_factors": ["...", "..."]
    }},
    "uncertainty_quantification": {{
        "data_freshness": {{
            "events": "... hours ago",
            "financials": "... days ago",
            "technical": "... minutes ago"
        }},
        "confidence_levels": {{
            "earnings_data": "high|medium|low",
            "sentiment": "high|medium|low",
            "forecasts": "high|medium|low"
        }},
        "missing_information": ["...", "..."],
        "probability_ranges": {{
            "price_target": {{
                "min": "...",
                "max": "...",
                "confidence": "..."
            }}
        }}
    }},
    "source_quality": {{
        "credibility_breakdown": {{
            "high_percent": "...",
            "medium_percent": "...",
            "low_percent": "..."
        }},
        "contradictions": [
            {{
                "claim": "...",
                "conflicting_sources": ["...", "..."],
                "resolution": "..."
            }}
        ],
        "completeness_score": "...",
        "source_diversity": "...",
        "reliability_assessment": "..."
    }},
    "key_takeaways": [
        {{
            "insight": "...",
            "priority": "high|medium|low",
            "actionable": true|false,
            "time_sensitive": true|false
        }}
    ],
    "contradictions_found": ["..." or []],
    "data_gaps": ["..." or []],
    "confidence_level": "HIGH|MEDIUM|LOW"
}}"""

        return prompt

    def _parse_synthesis(self, response: str) -> Dict[str, Any]:
        """Parse LLM synthesis response."""
        try:
            # Remove markdown code blocks if present
            response = response.strip()
            if response.startswith("```"):
                lines = response.split("\n")
                json_lines = []
                in_code_block = False
                for line in lines:
                    if line.strip().startswith("```"):
                        in_code_block = not in_code_block
                        continue
                    if in_code_block:
                        json_lines.append(line)
                response = "\n".join(json_lines)

            # Parse JSON
            briefing = json.loads(response)

            # Validate structure
            required_fields = [
                "recent_events", "sentiment_analysis", "risk_factors",
                "opportunities", "source_quality", "key_takeaways"
            ]

            for field in required_fields:
                if field not in briefing:
                    briefing[field] = "Not available"

            # Ensure lists are lists
            if not isinstance(briefing.get("key_takeaways"), list):
                briefing["key_takeaways"] = []

            if "contradictions_found" not in briefing:
                briefing["contradictions_found"] = []

            if "data_gaps" not in briefing:
                briefing["data_gaps"] = []

            if "confidence_level" not in briefing:
                briefing["confidence_level"] = "MEDIUM"

            return briefing

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse synthesis as JSON: {e}")

            # Return properly structured fallback with dictionaries/lists
            return {
                "recent_events": {
                    "earnings": "Unable to parse synthesis - JSON decode error",
                    "m_a": "",
                    "guidance": "",
                    "product_launches": "",
                    "legal_regulatory": ""
                },
                "sentiment_analysis": {
                    "overall": "unknown",
                    "analyst_consensus": {},
                    "news_sentiment": {},
                    "social_media": "Unable to parse synthesis",
                    "contradictions": {
                        "detected": False,
                        "severity": "low",
                        "description": "No data available due to parsing error"
                    }
                },
                "risk_factors": {
                    "company_specific": [],
                    "sector_macro": []
                },
                "opportunities": [],
                "source_quality": {
                    "credibility_breakdown": {
                        "high_percent": "0",
                        "medium_percent": "0", 
                        "low_percent": "100"
                    },
                    "contradictions": [],
                    "completeness_score": "0",
                    "source_diversity": "None - parsing failed",
                    "reliability_assessment": "LOW - JSON parsing error"
                },
                "key_takeaways": [
                    {
                        "insight": "Synthesis parsing failed - unable to extract structured data",
                        "priority": "low",
                        "actionable": False,
                        "time_sensitive": False
                    }
                ],
                "contradictions_found": ["JSON parsing failed"],
                "data_gaps": ["Synthesis parsing failed - no structured data available"],
                "confidence_level": "LOW"
            }

    def _fallback_briefing(
        self,
        symbol: str,
        raw_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create fallback briefing if synthesis fails."""
        logger.warning(f"Using fallback briefing for {symbol}")

        # Extract basic info from raw results
        titles = [r.get("title", "") for r in raw_results[:5]]
        snippets = [r.get("snippet", "") for r in raw_results[:3]]

        return {
            "recent_events": f"Search found {len(raw_results)} results. Top headlines: " + "; ".join(titles),
            "sentiment_analysis": "Unable to synthesize sentiment - raw data available",
            "risk_factors": "Synthesis failed - manual review recommended",
            "opportunities": "Synthesis failed - manual review recommended",
            "source_quality": f"Found {len(raw_results)} sources but synthesis failed",
            "key_takeaways": titles[:3],
            "contradictions_found": ["Synthesis failed"],
            "data_gaps": ["Complete synthesis unavailable"],
            "confidence_level": "LOW",
            "metadata": {
                "symbol": symbol,
                "num_sources": len(raw_results),
                "synthesis_model": self.research_model,
                "timestamp": datetime.now().isoformat(),
                "error": "Synthesis failed - using fallback"
            }
        }

    def format_for_trading_llm(self, briefing: Dict[str, Any]) -> str:
        """
        Format synthesized briefing for consumption by trading LLM.

        Args:
            briefing: Synthesized briefing dictionary

        Returns:
            Formatted string for trading LLM prompt
        """
        symbol = briefing.get("metadata", {}).get("symbol", "Unknown")
        confidence = briefing.get("confidence_level", "UNKNOWN")

        # Format recent events with subcategories
        recent_events = briefing.get('recent_events', {})
        if isinstance(recent_events, dict):
            events_text = ""
            if recent_events.get('earnings'):
                events_text += f"  📈 Earnings: {recent_events['earnings']}\n"
            if recent_events.get('m_a'):
                events_text += f"  🤝 M&A: {recent_events['m_a']}\n"
            if recent_events.get('guidance'):
                events_text += f"  📊 Guidance: {recent_events['guidance']}\n"
            if recent_events.get('product_launches'):
                events_text += f"  🚀 Product Launches: {recent_events['product_launches']}\n"
            if recent_events.get('legal_regulatory'):
                events_text += f"  ⚖️ Legal/Regulatory: {recent_events['legal_regulatory']}\n"
            if not events_text:
                events_text = "  No significant recent events found"
        else:
            events_text = str(recent_events)

        # Format sentiment analysis with detailed breakdown
        sentiment = briefing.get('sentiment_analysis', {})
        if isinstance(sentiment, dict):
            sentiment_text = f"  Overall: {sentiment.get('overall', 'Unknown')}\n"
            
            analyst = sentiment.get('analyst_consensus', {})
            if analyst:
                sentiment_text += f"  Analyst Consensus: {analyst.get('rating', 'N/A')} "
                sentiment_text += f"({analyst.get('count', 'N/A')} analysts, "
                sentiment_text += f"target: {analyst.get('price_target', 'N/A')})\n"
            
            news_sent = sentiment.get('news_sentiment', {})
            if news_sent:
                sentiment_text += f"  News Sentiment: {news_sent.get('bullish_percent', 'N/A')}% bullish, "
                sentiment_text += f"{news_sent.get('bearish_percent', 'N/A')}% bearish, "
                sentiment_text += f"{news_sent.get('neutral_percent', 'N/A')}% neutral\n"
            
            if sentiment.get('social_media'):
                sentiment_text += f"  Social Media: {sentiment['social_media']}\n"
            
            contradictions = sentiment.get('contradictions', {})
            if contradictions and contradictions.get('detected'):
                sentiment_text += f"  ⚠️ Contradictions: {contradictions.get('severity', 'Unknown')} severity - {contradictions.get('description', 'No description')}\n"
        else:
            sentiment_text = str(sentiment)

        # Format risk factors with categorization
        risks = briefing.get('risk_factors', {})
        if isinstance(risks, dict):
            risk_text = ""
            
            company_risks = risks.get('company_specific', [])
            if company_risks:
                risk_text += "  Company-Specific Risks:\n"
                for risk in company_risks[:3]:  # Limit to top 3
                    risk_text += f"    • {risk.get('risk', 'Unknown')} ({risk.get('severity', 'Unknown')} severity"
                    if risk.get('timeframe'):
                        risk_text += f", timeframe: {risk['timeframe']}"
                    risk_text += ")\n"
            
            sector_risks = risks.get('sector_macro', [])
            if sector_risks:
                risk_text += "  Sector/Macro Risks:\n"
                for risk in sector_risks[:2]:  # Limit to top 2
                    risk_text += f"    • {risk.get('risk', 'Unknown')} ({risk.get('severity', 'Unknown')} severity"
                    if risk.get('timeframe'):
                        risk_text += f", timeframe: {risk['timeframe']}"
                    risk_text += ")\n"
            
            if not risk_text:
                risk_text = "  No significant risk factors identified"
        else:
            risk_text = str(risks)

        # Format technical analysis
        tech = briefing.get('technical_analysis', {})
        if isinstance(tech, dict):
            tech_text = ""
            
            indicators = tech.get('indicators', {})
            if indicators:
                tech_text += "  Key Indicators:\n"
                for key, value in indicators.items():
                    tech_text += f"    • {key}: {value}\n"
            
            levels = tech.get('levels', {})
            if levels:
                tech_text += "  Key Levels:\n"
                if levels.get('support'):
                    tech_text += f"    • Support: {levels['support']}\n"
                if levels.get('resistance'):
                    tech_text += f"    • Resistance: {levels['resistance']}\n"
            
            signals = tech.get('signals', [])
            if signals:
                tech_text += "  Trading Signals:\n"
                for signal in signals[:3]:
                    tech_text += f"    • {signal}\n"
            
            if not tech_text:
                tech_text = "  No technical analysis data available"
        else:
            tech_text = str(tech)

        # Format fundamental metrics
        fundamentals = briefing.get('fundamental_metrics', {})
        if isinstance(fundamentals, dict):
            fund_text = ""
            
            valuation = fundamentals.get('valuation', {})
            if valuation:
                fund_text += "  Valuation:\n"
                for key, value in valuation.items():
                    if key != 'sector_comparison':
                        fund_text += f"    • {key}: {value}\n"
                if valuation.get('sector_comparison'):
                    fund_text += f"    • Sector Comparison: {valuation['sector_comparison']}\n"
            
            growth = fundamentals.get('growth', {})
            if growth:
                fund_text += "  Growth:\n"
                for key, value in growth.items():
                    fund_text += f"    • {key}: {value}\n"
            
            profitability = fundamentals.get('profitability', {})
            if profitability:
                fund_text += "  Profitability:\n"
                for key, value in profitability.items():
                    fund_text += f"    • {key}: {value}\n"
            
            if not fund_text:
                fund_text = "  No fundamental metrics available"
        else:
            fund_text = str(fundamentals)

        # Format opportunities with impact assessment
        opportunities = briefing.get('opportunities', [])
        if isinstance(opportunities, list):
            opp_text = ""
            for opp in opportunities[:3]:  # Limit to top 3
                opp_text += f"  • {opp.get('opportunity', 'Unknown')}"
                if opp.get('timeline'):
                    opp_text += f" (Timeline: {opp['timeline']})"
                if opp.get('impact'):
                    opp_text += f" - {opp['impact']} impact"
                if opp.get('probability'):
                    opp_text += f" ({opp['probability']} probability)"
                opp_text += "\n"
            
            if not opp_text:
                opp_text = "  No specific opportunities identified"
        else:
            opp_text = str(opportunities)

        # Format contextual information
        context = briefing.get('contextual_information', {})
        if isinstance(context, dict):
            context_text = ""
            
            if context.get('sector_performance'):
                context_text += f"  Sector Performance: {context['sector_performance']}\n"
            
            peer = context.get('peer_comparison', {})
            if peer:
                context_text += f"  Peer Comparison: {peer.get('metric', 'Unknown')} - "
                context_text += f"Company: {peer.get('company_value', 'N/A')}, "
                context_text += f"Peer Avg: {peer.get('peer_average', 'N/A')}, "
                context_text += f"Percentile: {peer.get('percentile', 'N/A')}\n"
            
            vol = context.get('historical_volatility', {})
            if vol:
                context_text += f"  Volatility Context: Current {vol.get('current', 'N/A')} vs "
                context_text += f"Historical Avg {vol.get('historical_average', 'N/A')} "
                context_text += f"(Percentile: {vol.get('percentile', 'N/A')})\n"
            
            if context.get('market_regime'):
                context_text += f"  Market Regime: {context['market_regime']}\n"
            
            macro = context.get('macroeconomic_factors', [])
            if macro:
                context_text += f"  Macro Factors: {', '.join(macro[:2])}\n"
            
            if not context_text:
                context_text = "  No contextual information available"
        else:
            context_text = str(context)

        # Format uncertainty quantification
        uncertainty = briefing.get('uncertainty_quantification', {})
        if isinstance(uncertainty, dict):
            uncertainty_text = ""
            
            freshness = uncertainty.get('data_freshness', {})
            if freshness:
                uncertainty_text += "  Data Freshness:\n"
                for key, value in freshness.items():
                    uncertainty_text += f"    • {key}: {value}\n"
            
            confidence = uncertainty.get('confidence_levels', {})
            if confidence:
                uncertainty_text += "  Confidence Levels:\n"
                for key, value in confidence.items():
                    uncertainty_text += f"    • {key}: {value}\n"
            
            missing = uncertainty.get('missing_information', [])
            if missing:
                uncertainty_text += "  Missing Information:\n"
                for item in missing[:3]:
                    uncertainty_text += f"    • {item}\n"
            
            ranges = uncertainty.get('probability_ranges', {})
            if ranges and ranges.get('price_target'):
                pt = ranges['price_target']
                uncertainty_text += f"  Price Target Range: {pt.get('min', 'N/A')} - {pt.get('max', 'N/A')} "
                uncertainty_text += f"({pt.get('confidence', 'N/A')} confidence)\n"
            
            if not uncertainty_text:
                uncertainty_text = "  No uncertainty quantification available"
        else:
            uncertainty_text = str(uncertainty)

        # Format source quality with detailed breakdown
        source_quality = briefing.get('source_quality', {})
        if isinstance(source_quality, dict):
            source_text = ""
            
            credibility = source_quality.get('credibility_breakdown', {})
            if credibility:
                source_text += f"  Credibility: {credibility.get('high_percent', 'N/A')}% high, "
                source_text += f"{credibility.get('medium_percent', 'N/A')}% medium, "
                source_text += f"{credibility.get('low_percent', 'N/A')}% low\n"
            
            if source_quality.get('completeness_score'):
                source_text += f"  Completeness Score: {source_quality['completeness_score']}/100\n"
            
            if source_quality.get('reliability_assessment'):
                source_text += f"  Reliability: {source_quality['reliability_assessment']}\n"
            
            contradictions = source_quality.get('contradictions', [])
            if contradictions:
                source_text += "  Contradictions Found:\n"
                for contradiction in contradictions[:2]:
                    source_text += f"    • {contradiction.get('claim', 'Unknown')}\n"
            
            if not source_text:
                source_text = "  No source quality assessment available"
        else:
            source_text = str(source_quality)

        # Format key takeaways with priority
        takeaways = briefing.get('key_takeaways', [])
        if isinstance(takeaways, list):
            takeaway_text = ""
            for takeaway in takeaways[:5]:  # Limit to top 5
                priority = takeaway.get('priority', 'medium').upper()
                actionable = "✓" if takeaway.get('actionable') else "✗"
                time_sensitive = "⏰" if takeaway.get('time_sensitive') else ""
                takeaway_text += f"  [{priority}] {actionable}{time_sensitive} {takeaway.get('insight', 'Unknown')}\n"
            
            if not takeaway_text:
                takeaway_text = "  No key takeaways available"
        else:
            takeaway_text = str(takeaways)

        # Build the complete formatted briefing
        formatted = f"""=== ENHANCED RESEARCH BRIEFING FOR {symbol} ===
Overall Confidence: {confidence}

📊 RECENT EVENTS (Last 7 Days):
{events_text}

💭 SENTIMENT ANALYSIS:
{sentiment_text}

⚠️ RISK FACTORS:
{risk_text}

📈 TECHNICAL ANALYSIS:
{tech_text}

💰 FUNDAMENTAL METRICS:
{fund_text}

🚀 OPPORTUNITIES:
{opp_text}

🌍 CONTEXTUAL INFORMATION:
{context_text}

📊 UNCERTAINTY QUANTIFICATION:
{uncertainty_text}

✅ SOURCE QUALITY:
{source_text}

🎯 KEY TAKEAWAYS:
{takeaway_text}
"""

        # Add metadata
        metadata = briefing.get('metadata', {})
        if metadata:
            num_sources = metadata.get('num_sources', 0)
            credibility = metadata.get('credibility_breakdown', {})
            formatted += f"\n📖 RESEARCH METADATA:\n"
            formatted += f"  Sources: {num_sources} total "
            formatted += f"(High: {credibility.get('high', 0)}, "
            formatted += f"Medium: {credibility.get('medium', 0)}, "
            formatted += f"Low: {credibility.get('low', 0)})\n"
            formatted += f"  Research Model: {metadata.get('synthesis_model', 'Unknown')}\n"
            formatted += f"  Timestamp: {metadata.get('timestamp', 'Unknown')}\n"

        return formatted

    def get_model_info(self) -> Dict[str, str]:
        """Get information about models being used."""
        return {
            "trading_model": self.trading_model,
            "research_model": self.research_model,
            "company": ResearchModelMapper.get_model_company(self.trading_model)
        }
