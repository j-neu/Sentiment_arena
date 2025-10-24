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

1. **Recent Events** (last 7-14 days)
   - Key announcements, earnings, price movements
   - Include specific dates and numbers
   - Only include if verified by credible sources

2. **Sentiment Analysis**
   - Overall market sentiment (bullish/bearish/neutral)
   - Analyst consensus and ratings
   - News sentiment trend
   - Note if sources conflict

3. **Risk Factors**
   - Company-specific risks
   - Sector/macro risks
   - Any red flags or concerns
   - Rate each risk (high/medium/low severity)

4. **Opportunities**
   - Growth catalysts
   - Positive developments
   - Competitive advantages

5. **Source Quality Assessment**
   - Note contradictions between sources
   - Flag if important information is missing
   - Identify gaps in coverage

6. **Key Takeaways**
   - 3-5 bullet points summarizing the most important insights
   - Actionable information for trading decisions

CRITICAL REQUIREMENTS:
- Prioritize HIGH credibility sources over medium/low
- If sources contradict, note the contradiction explicitly
- If information is unverified or from low-credibility sources, flag it
- Be objective - avoid promotional or sensationalist language
- Include specific numbers, dates, and facts
- If data is missing or uncertain, explicitly state it

Return your analysis as a JSON object with this structure:
{{
    "recent_events": "...",
    "sentiment_analysis": "...",
    "risk_factors": "...",
    "opportunities": "...",
    "source_quality": "...",
    "key_takeaways": ["...", "...", "..."],
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

            # Return structured fallback
            return {
                "recent_events": response[:500] if response else "Synthesis failed",
                "sentiment_analysis": "Unable to parse synthesis",
                "risk_factors": "Unable to parse synthesis",
                "opportunities": "Unable to parse synthesis",
                "source_quality": "Parsing error occurred",
                "key_takeaways": ["Synthesis parsing failed"],
                "contradictions_found": [],
                "data_gaps": ["Synthesis parsing failed"],
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

        formatted = f"""=== RESEARCH BRIEFING FOR {symbol} ===
Quality Score: {confidence} confidence

📊 RECENT EVENTS:
{briefing.get('recent_events', 'No recent events data')}

💭 SENTIMENT ANALYSIS:
{briefing.get('sentiment_analysis', 'No sentiment data')}

⚠️ RISK FACTORS:
{briefing.get('risk_factors', 'No risk data')}

🚀 OPPORTUNITIES:
{briefing.get('opportunities', 'No opportunities data')}

✅ SOURCE QUALITY:
{briefing.get('source_quality', 'No source quality data')}

🎯 KEY TAKEAWAYS:
"""
        for i, takeaway in enumerate(briefing.get('key_takeaways', []), 1):
            formatted += f"{i}. {takeaway}\n"

        # Add contradictions if any
        contradictions = briefing.get('contradictions_found', [])
        if contradictions and contradictions != []:
            formatted += "\n⚡ CONTRADICTIONS DETECTED:\n"
            for contradiction in contradictions:
                formatted += f"- {contradiction}\n"

        # Add data gaps if any
        gaps = briefing.get('data_gaps', [])
        if gaps and gaps != []:
            formatted += "\n📝 DATA GAPS:\n"
            for gap in gaps:
                formatted += f"- {gap}\n"

        # Add metadata
        metadata = briefing.get('metadata', {})
        if metadata:
            num_sources = metadata.get('num_sources', 0)
            credibility = metadata.get('credibility_breakdown', {})
            formatted += f"\n📖 SOURCES: {num_sources} total "
            formatted += f"(High: {credibility.get('high', 0)}, "
            formatted += f"Medium: {credibility.get('medium', 0)}, "
            formatted += f"Low: {credibility.get('low', 0)})\n"

        return formatted

    def get_model_info(self) -> Dict[str, str]:
        """Get information about models being used."""
        return {
            "trading_model": self.trading_model,
            "research_model": self.research_model,
            "company": ResearchModelMapper.get_model_company(self.trading_model)
        }
