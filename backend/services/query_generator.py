"""
Intelligent Research Query Generator

Uses LLM to generate targeted, high-quality search queries based on:
- Stock symbol and existing data
- Identified data gaps
- Market conditions and context
"""

from typing import List, Dict, Optional, Any
import json
from datetime import datetime

from backend.logger import get_logger
from backend.services.openrouter_client import OpenRouterClient
from backend.services.research_model_mapper import ResearchModelMapper

logger = get_logger(__name__)


class QueryGenerator:
    """
    Generates intelligent, context-aware search queries using LLM.

    Uses cheaper models from the same company as the trading model.
    """

    def __init__(self, openrouter_client: OpenRouterClient, trading_model: str):
        """
        Initialize query generator.

        Args:
            openrouter_client: OpenRouter API client
            trading_model: The trading model identifier (e.g., "openai/gpt-4-turbo")
        """
        self.client = openrouter_client
        self.trading_model = trading_model
        self.research_model = ResearchModelMapper.get_research_model(trading_model)

        logger.info(
            f"QueryGenerator initialized: trading_model={trading_model}, "
            f"research_model={self.research_model}"
        )

    def generate_stock_queries(
        self,
        symbol: str,
        existing_data: Optional[Dict[str, Any]] = None,
        num_queries: int = 3,
        focus_areas: Optional[List[str]] = None
    ) -> List[str]:
        """
        Generate targeted search queries for a specific stock.

        Args:
            symbol: Stock symbol (e.g., "SAP.DE")
            existing_data: Optional dict of data we already have
            num_queries: Number of queries to generate (default: 3)
            focus_areas: Optional list of areas to focus on (e.g., ["earnings", "risks"])

        Returns:
            List of search query strings

        Example:
            >>> generator = QueryGenerator(client, "openai/gpt-4-turbo")
            >>> queries = generator.generate_stock_queries("SAP.DE", num_queries=3)
            ['SAP Q3 2024 earnings analyst reactions',
             'SAP valuation compared to competitors 2024',
             'SAP risk factors November 2024']
        """
        logger.info(f"Generating {num_queries} queries for {symbol}")

        # Build context about what we already know
        context = self._build_context(symbol, existing_data)

        # Build prompt for query generation
        prompt = self._build_query_generation_prompt(
            symbol=symbol,
            context=context,
            num_queries=num_queries,
            focus_areas=focus_areas
        )

        try:
            # Call research LLM
            response = self.client.get_completion_text(
                model=self.research_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,  # Some creativity for diverse queries
                max_tokens=500
            )

            # Parse queries from response
            queries = self._parse_queries(response, num_queries)

            logger.info(f"Generated {len(queries)} queries for {symbol}")
            return queries

        except Exception as e:
            logger.error(f"Error generating queries for {symbol}: {e}")
            # Fallback to basic queries
            return self._fallback_queries(symbol, num_queries)

    def generate_market_queries(
        self,
        market: str = "German stock market",
        num_queries: int = 2
    ) -> List[str]:
        """
        Generate queries for general market sentiment and conditions.

        Args:
            market: Market name (default: "German stock market")
            num_queries: Number of queries to generate

        Returns:
            List of search query strings
        """
        logger.info(f"Generating {num_queries} market queries for {market}")

        prompt = f"""Generate {num_queries} specific, targeted search queries to research current conditions and sentiment for the {market}.

Focus on:
- Recent market performance and trends
- Economic factors affecting the market
- Sector rotation and hot sectors
- Major news or events impacting the market
- Investor sentiment and positioning

Today's date: {datetime.now().strftime("%Y-%m-%d")}

Return ONLY a JSON array of query strings, no other text:
["query 1", "query 2", ...]"""

        try:
            response = self.client.get_completion_text(
                model=self.research_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=300
            )

            queries = self._parse_queries(response, num_queries)
            logger.info(f"Generated {len(queries)} market queries")
            return queries

        except Exception as e:
            logger.error(f"Error generating market queries: {e}")
            return self._fallback_market_queries(market, num_queries)

    def _build_context(self, symbol: str, existing_data: Optional[Dict[str, Any]]) -> str:
        """Build context string from existing data."""
        if not existing_data:
            return "No existing data available."

        context_parts = []

        # Portfolio data
        if "portfolio" in existing_data:
            context_parts.append(f"Portfolio: {existing_data['portfolio']}")

        # Position data
        if "positions" in existing_data:
            context_parts.append(f"Current positions: {existing_data['positions']}")

        # Market data
        if "market_data" in existing_data:
            context_parts.append(f"Market data: {existing_data['market_data']}")

        # Any other data
        for key, value in existing_data.items():
            if key not in ["portfolio", "positions", "market_data"]:
                context_parts.append(f"{key}: {value}")

        return "\n".join(context_parts) if context_parts else "No existing data available."

    def _build_query_generation_prompt(
        self,
        symbol: str,
        context: str,
        num_queries: int,
        focus_areas: Optional[List[str]] = None
    ) -> str:
        """Build the prompt for query generation."""
        company_name = symbol.replace(".DE", "")  # Basic extraction

        focus_text = ""
        if focus_areas:
            focus_text = f"\nPrioritize queries about: {', '.join(focus_areas)}"

        prompt = f"""You are a financial research assistant. Generate {num_queries} specific, targeted search queries to find the most relevant and current information about {symbol} ({company_name}).

=== EXISTING DATA ===
{context}

=== YOUR TASK ===
Generate {num_queries} search queries that will help fill gaps in our knowledge and provide actionable trading insights.

Focus on:
1. Recent events (earnings, announcements, price movements)
2. Market reactions and analyst opinions
3. Risk factors and concerns
4. Growth catalysts and opportunities
5. Competitive positioning{focus_text}

Today's date: {datetime.now().strftime("%Y-%m-%d")}

Requirements:
- Queries should be specific and include the stock name
- Queries should target credible financial news sources
- Queries should be current (include year/month if relevant)
- Avoid generic queries like "stock price" or "company info"

Return ONLY a JSON array of query strings, no other text or explanation:
["query 1", "query 2", "query 3"]

Example good queries:
["SAP Q3 2024 earnings analyst reactions", "SAP cloud revenue growth 2024", "SAP vs Oracle competition November 2024"]"""

        return prompt

    def _parse_queries(self, response: str, expected_count: int) -> List[str]:
        """Parse queries from LLM response."""
        try:
            # Try to extract JSON array
            response = response.strip()

            # Remove markdown code blocks if present
            if response.startswith("```"):
                # Find the JSON content between ```
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
            queries = json.loads(response)

            if isinstance(queries, list) and all(isinstance(q, str) for q in queries):
                # Filter out empty queries and limit to expected count
                queries = [q.strip() for q in queries if q.strip()][:expected_count]
                return queries

            logger.warning(f"Invalid queries format: {queries}")
            return []

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse queries as JSON: {e}")

            # Try to extract queries from text
            lines = response.strip().split("\n")
            queries = []
            for line in lines:
                line = line.strip()
                # Look for lines that might be queries
                if line and not line.startswith("#") and len(line) > 10:
                    # Remove common prefixes
                    for prefix in ["1.", "2.", "3.", "4.", "5.", "-", "*", "•"]:
                        if line.startswith(prefix):
                            line = line[len(prefix):].strip()
                    if line:
                        queries.append(line)

            return queries[:expected_count]

    def _fallback_queries(self, symbol: str, num_queries: int) -> List[str]:
        """Generate basic fallback queries if LLM fails."""
        company_name = symbol.replace(".DE", "")
        today = datetime.now()
        year = today.year
        month = today.strftime("%B")

        queries = [
            f"{company_name} stock news {month} {year}",
            f"{company_name} earnings report {year}",
            f"{company_name} analyst ratings {year}",
            f"{company_name} risk factors {year}",
            f"{company_name} growth outlook {year}"
        ]

        return queries[:num_queries]

    def _fallback_market_queries(self, market: str, num_queries: int) -> List[str]:
        """Generate basic fallback market queries."""
        today = datetime.now()
        year = today.year
        month = today.strftime("%B")

        queries = [
            f"{market} outlook {month} {year}",
            f"{market} performance {year}",
            f"DAX index news today",
            f"German economy {year}"
        ]

        return queries[:num_queries]

    def get_model_info(self) -> Dict[str, str]:
        """Get information about the models being used."""
        cost_info = ResearchModelMapper.get_cost_estimate(self.trading_model)
        return {
            "trading_model": self.trading_model,
            "research_model": self.research_model,
            "company": ResearchModelMapper.get_model_company(self.trading_model),
            **cost_info
        }
