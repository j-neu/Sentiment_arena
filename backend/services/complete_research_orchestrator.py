"""
Complete Research Orchestrator

Combines all research components into a unified system:
- Phase 3.5.1: Enhanced Research Pipeline (LLM synthesis + quality verification)
- Phase 3.5.2: Financial Data APIs (Alpha Vantage + Finnhub)
- Phase 3.5.3: Technical Analysis (pandas-ta indicators)

This orchestrator coordinates all data sources and produces a comprehensive
briefing for LLM trading decisions.

Author: Sentiment Arena
Date: 2025-10-23
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import time

from backend.services.technical_analysis import TechnicalAnalysisService
from backend.services.financial_data_aggregator import FinancialDataAggregator
from backend.services.enhanced_research import EnhancedResearchPipeline
from backend.services.openrouter_client import OpenRouterClient
from backend.logger import get_logger

logger = get_logger(__name__)


class CompleteResearchOrchestrator:
    """
    Orchestrates all research components to produce comprehensive stock briefings.

    Coordinates:
    1. Technical analysis (fast, free, indicators)
    2. Financial APIs (structured fundamental data)
    3. Enhanced research pipeline (web search + LLM synthesis)
    4. Quality verification across all sources
    5. Unified briefing generation
    """

    def __init__(
        self,
        openrouter_api_key: str,
        alphavantage_api_key: Optional[str] = None,
        finnhub_api_key: Optional[str] = None,
        model_identifier: str = "openai/gpt-3.5-turbo"
    ):
        """
        Initialize complete research orchestrator.

        Args:
            openrouter_api_key: OpenRouter API key for LLM synthesis
            alphavantage_api_key: Alpha Vantage API key (optional)
            finnhub_api_key: Finnhub API key (optional)
            model_identifier: Model for research/synthesis (default: GPT-3.5)
        """
        self.openrouter_client = OpenRouterClient(openrouter_api_key)
        self.model_identifier = model_identifier

        # Initialize all services
        self.technical_analysis = TechnicalAnalysisService(lookback_days=90)

        self.financial_aggregator = FinancialDataAggregator(
            alphavantage_api_key=alphavantage_api_key,
            finnhub_api_key=finnhub_api_key
        )

        self.enhanced_research = EnhancedResearchPipeline(
            openrouter_client=self.openrouter_client,
            trading_model=model_identifier
        )

        logger.info("CompleteResearchOrchestrator initialized")

    def conduct_complete_research(
        self,
        symbol: str,
        include_technical: bool = True,
        include_financial_apis: bool = True,
        include_web_research: bool = True,
        include_quality_verification: bool = True
    ) -> Dict[str, Any]:
        """
        Conduct comprehensive research for a stock.

        Args:
            symbol: Stock symbol (e.g., "SAP.DE")
            include_technical: Include technical analysis (default: True)
            include_financial_apis: Include financial API data (default: True)
            include_web_research: Include web research (default: True)
            include_quality_verification: Run quality verification (default: True)

        Returns:
            Dictionary containing all research data and unified briefing
        """
        logger.info(f"Starting complete research for {symbol}")
        start_time = time.time()

        result = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "success": False,
            "technical_analysis": None,
            "financial_data": None,
            "enhanced_research": None,
            "unified_briefing": None,
            "quality_score": None,
            "timing": {},
            "errors": []
        }

        # Stage 1: Technical Analysis (fastest, always run if enabled)
        if include_technical:
            tech_start = time.time()
            try:
                logger.info(f"[1/4] Running technical analysis for {symbol}...")
                tech_result = self.technical_analysis.get_technical_analysis(symbol)
                result["technical_analysis"] = tech_result
                result["timing"]["technical_analysis"] = time.time() - tech_start

                if not tech_result.get("success"):
                    logger.warning(f"Technical analysis failed: {tech_result.get('error')}")
                    result["errors"].append(f"Technical analysis: {tech_result.get('error')}")
                else:
                    logger.info(f"Technical analysis complete ({result['timing']['technical_analysis']:.2f}s)")
            except Exception as e:
                logger.error(f"Error in technical analysis: {str(e)}", exc_info=True)
                result["errors"].append(f"Technical analysis error: {str(e)}")
                result["timing"]["technical_analysis"] = time.time() - tech_start

        # Stage 2: Financial APIs (structured data)
        if include_financial_apis:
            fin_start = time.time()
            try:
                logger.info(f"[2/4] Fetching financial data for {symbol}...")
                fin_result = self.financial_aggregator.get_complete_analysis(symbol)
                result["financial_data"] = fin_result
                result["timing"]["financial_data"] = time.time() - fin_start

                if not fin_result.get("success"):
                    logger.warning(f"Financial data fetch had issues: {fin_result.get('errors')}")
                    result["errors"].extend([f"Financial API: {e}" for e in fin_result.get("errors", [])])
                else:
                    logger.info(f"Financial data complete ({result['timing']['financial_data']:.2f}s)")
            except Exception as e:
                logger.error(f"Error in financial data: {str(e)}", exc_info=True)
                result["errors"].append(f"Financial data error: {str(e)}")
                result["timing"]["financial_data"] = time.time() - fin_start

        # Stage 3: Enhanced Research Pipeline (web + LLM synthesis)
        if include_web_research:
            research_start = time.time()
            try:
                logger.info(f"[3/4] Conducting enhanced research for {symbol}...")
                research_result = self.enhanced_research.conduct_stock_research(
                    symbol=symbol,
                    verify_quality=include_quality_verification
                )
                result["enhanced_research"] = research_result
                result["timing"]["enhanced_research"] = time.time() - research_start

                if not research_result.get("success"):
                    logger.warning(f"Enhanced research failed: {research_result.get('error')}")
                    result["errors"].append(f"Enhanced research: {research_result.get('error')}")
                else:
                    logger.info(f"Enhanced research complete ({result['timing']['enhanced_research']:.2f}s)")
            except Exception as e:
                logger.error(f"Error in enhanced research: {str(e)}", exc_info=True)
                result["errors"].append(f"Enhanced research error: {str(e)}")
                result["timing"]["enhanced_research"] = time.time() - research_start

        # Stage 4: Generate Unified Briefing
        briefing_start = time.time()
        try:
            logger.info(f"[4/4] Generating unified briefing for {symbol}...")
            unified_briefing = self._create_unified_briefing(
                symbol=symbol,
                technical=result.get("technical_analysis"),
                financial=result.get("financial_data"),
                research=result.get("enhanced_research")
            )
            result["unified_briefing"] = unified_briefing
            result["timing"]["unified_briefing"] = time.time() - briefing_start
            logger.info(f"Unified briefing complete ({result['timing']['unified_briefing']:.2f}s)")
        except Exception as e:
            logger.error(f"Error creating unified briefing: {str(e)}", exc_info=True)
            result["errors"].append(f"Unified briefing error: {str(e)}")
            result["timing"]["unified_briefing"] = time.time() - briefing_start

        # Optional: Quality Verification
        if include_quality_verification and result.get("unified_briefing"):
            quality_start = time.time()
            try:
                logger.info(f"Running quality verification for {symbol}...")
                quality_score = self._verify_briefing_quality(
                    briefing=result["unified_briefing"],
                    symbol=symbol
                )
                result["quality_score"] = quality_score
                result["timing"]["quality_verification"] = time.time() - quality_start
                logger.info(f"Quality verification complete: {quality_score}/100 ({result['timing']['quality_verification']:.2f}s)")
            except Exception as e:
                logger.error(f"Error in quality verification: {str(e)}", exc_info=True)
                result["errors"].append(f"Quality verification error: {str(e)}")
                result["timing"]["quality_verification"] = time.time() - quality_start

        # Calculate total time
        total_time = time.time() - start_time
        result["timing"]["total"] = total_time

        # Mark success if we have at least one data source
        result["success"] = (
            (result.get("technical_analysis") and result["technical_analysis"].get("success")) or
            (result.get("financial_data") and result["financial_data"].get("success")) or
            (result.get("enhanced_research") and result["enhanced_research"].get("success"))
        )

        logger.info(f"Complete research finished for {symbol} in {total_time:.2f}s (Success: {result['success']})")

        return result

    def _create_unified_briefing(
        self,
        symbol: str,
        technical: Optional[Dict[str, Any]],
        financial: Optional[Dict[str, Any]],
        research: Optional[Dict[str, Any]]
    ) -> str:
        """
        Create unified briefing combining all data sources.

        Args:
            symbol: Stock symbol
            technical: Technical analysis results
            financial: Financial API data
            research: Enhanced research results

        Returns:
            Unified briefing string formatted for LLM
        """
        briefing = f"# COMPLETE RESEARCH BRIEFING: {symbol}\n"
        briefing += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        sections_included = []

        # Section 1: Technical Analysis
        if technical and technical.get("success"):
            briefing += "=" * 80 + "\n"
            briefing += "## 1. TECHNICAL ANALYSIS\n"
            briefing += "=" * 80 + "\n\n"
            briefing += technical.get("llm_formatted", "No technical analysis available")
            briefing += "\n\n"
            sections_included.append("Technical Analysis")

        # Section 2: Financial Data & Fundamentals
        if financial and financial.get("success"):
            briefing += "=" * 80 + "\n"
            briefing += "## 2. FINANCIAL DATA & FUNDAMENTALS\n"
            briefing += "=" * 80 + "\n\n"
            # Format financial data using aggregator's format_for_llm method
            formatted_financial = self.financial_aggregator.format_for_llm(financial)
            briefing += formatted_financial
            briefing += "\n\n"
            sections_included.append("Financial Data")

        # Section 3: Market Research & Sentiment
        if research and research.get("success"):
            briefing += "=" * 80 + "\n"
            briefing += "## 3. MARKET RESEARCH & SENTIMENT\n"
            briefing += "=" * 80 + "\n\n"

            # Use formatted briefing from enhanced research
            if research.get("formatted_briefing"):
                briefing += research["formatted_briefing"]
            else:
                briefing += "No research synthesis available\n"

            # Add quality metrics if available
            verification = research.get("pipeline_stages", {}).get("verification", {})
            if verification.get("status") != "skipped":
                quality_score = verification.get("quality_score", 0)
                assessment = verification.get("verification", {}).get("overall_assessment", "UNKNOWN")
                briefing += f"\n\n**Research Quality Score**: {quality_score}/100 ({assessment})\n"
                passed = verification.get("passed", False)
                briefing += f"**Quality Check**: {'✅ PASSED' if passed else '⚠️ NEEDS REVIEW'}\n"

            briefing += "\n\n"
            sections_included.append("Market Research")

        # Summary of included sections
        briefing += "=" * 80 + "\n"
        briefing += "## BRIEFING SUMMARY\n"
        briefing += "=" * 80 + "\n\n"
        briefing += f"**Sections Included**: {', '.join(sections_included) if sections_included else 'None'}\n"
        briefing += f"**Data Sources**: {len(sections_included)} active\n"

        # Confidence indicator
        if len(sections_included) >= 3:
            briefing += f"**Confidence Level**: HIGH (all data sources available)\n"
        elif len(sections_included) == 2:
            briefing += f"**Confidence Level**: MEDIUM (partial data available)\n"
        else:
            briefing += f"**Confidence Level**: LOW (limited data available)\n"

        briefing += "\n"
        briefing += "=" * 80 + "\n"
        briefing += "END OF BRIEFING\n"
        briefing += "=" * 80 + "\n"

        return briefing

    def _verify_briefing_quality(self, briefing: str, symbol: str) -> int:
        """
        Verify quality of unified briefing.

        Args:
            briefing: Unified briefing text
            symbol: Stock symbol

        Returns:
            Quality score (0-100)
        """
        try:
            prompt = f"""You are a quality assurance analyst for financial research briefings.

Review this stock briefing for {symbol} and rate its quality.

BRIEFING:
{briefing}

Rate the briefing on these criteria (0-100 scale):
1. **Completeness**: Are all key sections present? (Technical, Fundamentals, Sentiment)
2. **Accuracy**: Does the data appear consistent and logical?
3. **Actionability**: Can a trader make decisions based on this?
4. **Clarity**: Is the information well-organized and clear?

Respond with ONLY a JSON object:
{{
    "overall_score": <0-100>,
    "completeness": <0-100>,
    "accuracy": <0-100>,
    "actionability": <0-100>,
    "clarity": <0-100>,
    "issues": ["list", "of", "issues"],
    "strengths": ["list", "of", "strengths"]
}}"""

            response = self.openrouter_client.create_completion(
                model=self.model_identifier,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500
            )

            if response and response.get("success"):
                import json
                content = response["content"].strip()

                # Extract JSON from markdown code blocks if present
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                quality_data = json.loads(content)
                return quality_data.get("overall_score", 50)
            else:
                logger.warning("Quality verification failed, returning default score")
                return 50

        except Exception as e:
            logger.error(f"Error in quality verification: {str(e)}", exc_info=True)
            return 50  # Default score on error

    def get_cost_estimate(self, symbol: str) -> Dict[str, Any]:
        """
        Estimate cost of complete research for a symbol.

        Returns:
            Dictionary with cost breakdown
        """
        return {
            "technical_analysis": "$0.00 (free)",
            "financial_apis": "$0.00 (free tier)",
            "enhanced_research": "~$0.01 (LLM synthesis)",
            "quality_verification": "~$0.002 (LLM verification)",
            "total_estimated": "~$0.012 per research",
            "note": "Costs may vary based on API usage and rate limits"
        }

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.openrouter_client:
            self.openrouter_client.__exit__(exc_type, exc_val, exc_tb)
