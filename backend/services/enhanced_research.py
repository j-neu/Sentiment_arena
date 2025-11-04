"""
Enhanced Research Pipeline

Multi-stage research system that produces high-quality, verified briefings:

Stage 1: Data Collection
  - Generate intelligent search queries using LLM
  - Execute web searches
  - Collect raw data

Stage 2: Research Synthesis
  - Assess source credibility
  - Synthesize findings into coherent briefing
  - Identify contradictions and gaps

Stage 3: Quality Verification
  - Self-review of briefing
  - Quality scoring (0-100)
  - Pass/fail determination

Stage 4: Formatted Output
  - Create trading-ready briefing
  - Include quality metadata
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from backend.logger import get_logger
from backend.services.openrouter_client import OpenRouterClient
from backend.services.research import ResearchService
from backend.services.query_generator import QueryGenerator
from backend.services.research_synthesis import ResearchSynthesizer
from backend.services.quality_verifier import QualityVerifier
from backend.services.research_model_mapper import ResearchModelMapper

logger = get_logger(__name__)


class EnhancedResearchPipeline:
    """
    Complete multi-stage research pipeline for high-quality briefings.

    Uses cheaper LLM from same company for research tasks,
    then provides verified briefing to premium trading model.
    """

    def __init__(
        self,
        openrouter_client: OpenRouterClient,
        trading_model: str
    ):
        """
        Initialize enhanced research pipeline.

        Args:
            openrouter_client: OpenRouter API client
            trading_model: Trading model identifier (e.g., "openai/gpt-4-turbo")
        """
        self.client = openrouter_client
        self.trading_model = trading_model
        self.research_model = ResearchModelMapper.get_research_model(trading_model)

        # Initialize component services
        self.research_service = ResearchService()
        self.query_generator = QueryGenerator(openrouter_client, trading_model)
        self.synthesizer = ResearchSynthesizer(
            openrouter_client,
            self.research_service,
            trading_model
        )
        self.verifier = QualityVerifier(openrouter_client, trading_model)

        logger.info(
            f"EnhancedResearchPipeline initialized:\n"
            f"  Trading model: {trading_model}\n"
            f"  Research model: {self.research_model}\n"
            f"  Company: {ResearchModelMapper.get_model_company(trading_model)}"
        )

    def conduct_stock_research(
        self,
        symbol: str,
        existing_data: Optional[Dict[str, Any]] = None,
        num_queries: int = 3,
        focus_areas: Optional[List[str]] = None,
        verify_quality: bool = True
    ) -> Dict[str, Any]:
        """
        Conduct complete enhanced research for a stock.

        Args:
            symbol: Stock symbol (e.g., "SAP.DE")
            existing_data: Optional existing data (prices, positions, etc.)
            num_queries: Number of search queries to generate
            focus_areas: Optional list of focus areas
            verify_quality: Whether to run quality verification (default: True)

        Returns:
            Dictionary with complete research results and metadata
        """
        logger.info(f"Starting enhanced research for {symbol}")
        pipeline_start = datetime.now()

        results = {
            "symbol": symbol,
            "pipeline_stages": {},
            "timing": {},
            "models_used": {
                "trading": self.trading_model,
                "research": self.research_model
            }
        }

        try:
            # STAGE 1: Generate intelligent queries
            stage1_start = datetime.now()
            logger.info(f"[Stage 1] Generating {num_queries} intelligent queries...")

            queries = self.query_generator.generate_stock_queries(
                symbol=symbol,
                existing_data=existing_data,
                num_queries=num_queries,
                focus_areas=focus_areas
            )

            results["pipeline_stages"]["query_generation"] = {
                "queries": queries,
                "num_queries": len(queries),
                "status": "success"
            }
            results["timing"]["query_generation"] = (datetime.now() - stage1_start).total_seconds()

            logger.info(f"[Stage 1] Generated queries: {queries}")

            # STAGE 2: Execute searches and collect data
            stage2_start = datetime.now()
            logger.info(f"[Stage 2] Executing {len(queries)} searches...")

            raw_results = []
            for query in queries:
                search_results = self.research_service.search_stock_news(
                    symbol=symbol,
                    max_results=5
                )
                raw_results.extend(search_results)

            # Deduplicate by URL
            seen_urls = set()
            unique_results = []
            for result in raw_results:
                url = result.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    unique_results.append(result)

            results["pipeline_stages"]["data_collection"] = {
                "total_results": len(raw_results),
                "unique_results": len(unique_results),
                "status": "success"
            }
            results["timing"]["data_collection"] = (datetime.now() - stage2_start).total_seconds()

            logger.info(f"[Stage 2] Collected {len(unique_results)} unique results")

            # STAGE 3: Synthesize research
            stage3_start = datetime.now()
            logger.info(f"[Stage 3] Synthesizing research from {len(unique_results)} sources...")

            briefing = self.synthesizer.synthesize_stock_research(
                symbol=symbol,
                raw_results=unique_results,
                existing_data=existing_data
            )

            results["pipeline_stages"]["synthesis"] = {
                "briefing": briefing,
                "status": "success"
            }
            results["timing"]["synthesis"] = (datetime.now() - stage3_start).total_seconds()

            logger.info(f"[Stage 3] Synthesis complete. Confidence: {briefing.get('confidence_level', 'UNKNOWN')}")

            # STAGE 4: Quality verification (optional)
            if verify_quality:
                stage4_start = datetime.now()
                logger.info(f"[Stage 4] Verifying briefing quality...")

                verification = self.verifier.verify_briefing(
                    briefing=briefing,
                    source_data=unique_results
                )

                results["pipeline_stages"]["verification"] = {
                    "verification": verification,
                    "quality_score": verification.get("quality_score", 0),
                    "passed": self.verifier.should_use_briefing(verification),
                    "status": "success"
                }
                results["timing"]["verification"] = (datetime.now() - stage4_start).total_seconds()

                logger.info(
                    f"[Stage 4] Quality score: {verification.get('quality_score', 0)}/100 "
                    f"({verification.get('overall_assessment', 'UNKNOWN')})"
                )

                # Add verification to briefing
                briefing["quality_verification"] = verification
            else:
                results["pipeline_stages"]["verification"] = {
                    "status": "skipped"
                }

            # Create formatted briefing for trading LLM
            formatted_briefing = self.synthesizer.format_for_trading_llm(briefing)

            # Add to results
            results["briefing"] = briefing
            results["formatted_briefing"] = formatted_briefing
            results["success"] = True

            # Calculate total time
            total_time = (datetime.now() - pipeline_start).total_seconds()
            results["timing"]["total"] = total_time

            logger.info(
                f"Enhanced research complete for {symbol}. "
                f"Total time: {total_time:.2f}s"
            )

            return results

        except Exception as e:
            logger.error(f"Error in enhanced research pipeline for {symbol}: {e}", exc_info=True)

            results["success"] = False
            results["error"] = str(e)
            results["timing"]["total"] = (datetime.now() - pipeline_start).total_seconds()

            return results

    def conduct_market_research(
        self,
        market: str = "German stock market",
        num_queries: int = 2
    ) -> Dict[str, Any]:
        """
        Conduct enhanced research for general market conditions.

        Args:
            market: Market name
            num_queries: Number of queries to generate

        Returns:
            Dictionary with research results
        """
        logger.info(f"Starting market research for {market}")

        try:
            # Generate market queries
            queries = self.query_generator.generate_market_queries(
                market=market,
                num_queries=num_queries
            )

            # Execute searches
            raw_results = []
            for query in queries:
                results = self.research_service.search_market_sentiment(query)
                raw_results.extend(results)

            # Format results
            formatted = self.research_service.format_research_for_llm({
                "queries": queries,
                "results": raw_results
            })

            return {
                "market": market,
                "queries": queries,
                "num_results": len(raw_results),
                "formatted": formatted,
                "success": True
            }

        except Exception as e:
            logger.error(f"Error in market research: {e}")
            return {
                "market": market,
                "success": False,
                "error": str(e)
            }

    def get_pipeline_summary(self, results: Dict[str, Any]) -> str:
        """
        Create a formatted summary of pipeline execution.

        Args:
            results: Results from conduct_stock_research()

        Returns:
            Formatted summary string
        """
        if not results.get("success"):
            return f"❌ Pipeline failed: {results.get('error', 'Unknown error')}"

        symbol = results.get("symbol", "Unknown")
        timing = results.get("timing", {})
        stages = results.get("pipeline_stages", {})

        summary = f"""
╔══════════════════════════════════════════════════════════╗
║      ENHANCED RESEARCH PIPELINE SUMMARY - {symbol}      ║
╚══════════════════════════════════════════════════════════╝

Models Used:
  • Trading:  {results.get('models_used', {}).get('trading', 'Unknown')}
  • Research: {results.get('models_used', {}).get('research', 'Unknown')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STAGE 1: Query Generation ({timing.get('query_generation', 0):.2f}s)
"""
        query_gen = stages.get("query_generation", {})
        queries = query_gen.get("queries", [])
        for i, query in enumerate(queries, 1):
            summary += f"  {i}. {query}\n"

        data_collection = stages.get("data_collection", {})
        summary += f"""
STAGE 2: Data Collection ({timing.get('data_collection', 0):.2f}s)
  • Total results: {data_collection.get('total_results', 0)}
  • Unique sources: {data_collection.get('unique_results', 0)}

STAGE 3: Synthesis ({timing.get('synthesis', 0):.2f}s)
  • Briefing generated successfully
  • Confidence: {results.get('briefing', {}).get('confidence_level', 'UNKNOWN')}
"""

        verification_stage = stages.get("verification", {})
        if verification_stage.get("status") != "skipped":
            verification = verification_stage.get("verification", {})
            quality_score = verification.get("quality_score", 0)
            passed = verification_stage.get("passed", False)

            summary += f"""
STAGE 4: Quality Verification ({timing.get('verification', 0):.2f}s)
  • Quality Score: {quality_score}/100
  • Assessment: {verification.get('overall_assessment', 'UNKNOWN')}
  • Status: {'✅ PASSED' if passed else '❌ FAILED'}
"""

        summary += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Pipeline Time: {timing.get('total', 0):.2f}s
Status: ✅ SUCCESS
"""

        return summary

    def get_cost_estimate(self) -> Dict[str, Any]:
        """
        Get estimated cost breakdown for the pipeline.

        Returns:
            Dictionary with cost information
        """
        cost_info = ResearchModelMapper.get_cost_estimate(self.trading_model)

        return {
            **cost_info,
            "pipeline_stages": {
                "query_generation": f"~1 call to {self.research_model}",
                "synthesis": f"~1 call to {self.research_model}",
                "verification": f"~1 call to {self.research_model}",
                "total_research_calls": 3,
                "web_searches": "Free (no API costs)"
            },
            "estimated_cost_per_research": "~$0.01 (research model calls only)"
        }

    def get_model_info(self) -> Dict[str, str]:
        """Get information about models being used."""
        return {
            "trading_model": self.trading_model,
            "research_model": self.research_model,
            "company": ResearchModelMapper.get_model_company(self.trading_model),
            "cost_tier": ResearchModelMapper.get_cost_estimate(self.trading_model)
        }
