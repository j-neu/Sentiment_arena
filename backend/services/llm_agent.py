"""
LLM Agent for autonomous stock trading decisions.

This module implements the core LLM agent that makes trading decisions based on
market data, research, and portfolio state.
"""

import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session

from backend.config import settings
from backend.logger import get_logger
from backend.models.model import Model
from backend.models.portfolio import Portfolio
from backend.models.position import Position
from backend.models.reasoning import Reasoning
from backend.services.openrouter_client import OpenRouterClient
from backend.services.research import ResearchService
from backend.services.market_data import MarketDataService
from backend.services.trading_engine import TradingEngine
from backend.services.complete_research_orchestrator import CompleteResearchOrchestrator

logger = get_logger(__name__)


class LLMAgent:
    """LLM Agent for making autonomous trading decisions."""

    # Default prompt template path
    DEFAULT_PROMPT_PATH = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "prompts",
        "trading_prompt.txt"
    )

    def __init__(
        self,
        db: Session,
        model_id: int,
        api_key: Optional[str] = None,
        prompt_path: Optional[str] = None,
        use_complete_research: bool = True,
        alphavantage_api_key: Optional[str] = None,
        finnhub_api_key: Optional[str] = None
    ):
        """
        Initialize the LLM agent.

        Args:
            db: Database session
            model_id: ID of the model this agent represents
            api_key: Optional OpenRouter API key
            prompt_path: Optional path to custom prompt template file
            use_complete_research: Use complete research orchestrator (default: True)
            alphavantage_api_key: Optional Alpha Vantage API key
            finnhub_api_key: Optional Finnhub API key
        """
        self.db = db
        self.model_id = model_id
        self.use_complete_research = use_complete_research

        # Load model from database
        self.model = db.query(Model).filter(Model.id == model_id).first()
        if not self.model:
            raise ValueError(f"Model with id {model_id} not found")

        # Load prompt template
        self.prompt_template = self._load_prompt_template(prompt_path)

        # Initialize services
        self.openrouter = OpenRouterClient(api_key)
        self.research = ResearchService()
        self.market_data = MarketDataService(db)
        self.trading_engine = TradingEngine(db)

        # Initialize complete research orchestrator if enabled
        self.complete_research = None
        if use_complete_research:
            try:
                self.complete_research = CompleteResearchOrchestrator(
                    openrouter_api_key=api_key or settings.OPENROUTER_API_KEY,
                    alphavantage_api_key=alphavantage_api_key or getattr(settings, 'ALPHAVANTAGE_API_KEY', None),
                    finnhub_api_key=finnhub_api_key or getattr(settings, 'FINNHUB_API_KEY', None),
                    model_identifier=self.model.api_identifier
                )
                logger.info(f"Complete research orchestrator enabled for {self.model.name}")
            except Exception as e:
                logger.warning(f"Could not initialize complete research: {e}. Falling back to basic research.")
                self.use_complete_research = False

        logger.info(f"LLM Agent initialized for model: {self.model.name}")

    def _load_prompt_template(self, prompt_path: Optional[str] = None) -> str:
        """
        Load the prompt template from file.

        Args:
            prompt_path: Optional path to custom prompt template file

        Returns:
            Prompt template string

        Raises:
            FileNotFoundError: If prompt template file not found
        """
        path = prompt_path or self.DEFAULT_PROMPT_PATH

        try:
            with open(path, 'r', encoding='utf-8') as f:
                template = f.read()
            logger.info(f"Loaded prompt template from: {path}")
            return template
        except FileNotFoundError:
            logger.error(f"Prompt template file not found: {path}")
            raise FileNotFoundError(
                f"Prompt template not found at {path}. "
                "Please ensure backend/prompts/trading_prompt.txt exists."
            )
        except Exception as e:
            logger.error(f"Error loading prompt template: {e}")
            raise

    def make_trading_decision(
        self,
        perform_research: bool = True,
        research_queries: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Make a trading decision based on current state and research.

        Args:
            perform_research: Whether to perform internet research
            research_queries: Optional list of research queries

        Returns:
            Dictionary containing the decision and execution result
        """
        logger.info(f"Making trading decision for {self.model.name}")

        try:
            # Get current portfolio state
            portfolio = self._get_portfolio_state()

            # Get open positions
            positions = self._get_positions()

            # Get market data for positions
            market_data = self._get_market_data(positions)

            # Perform research if requested
            research_content = ""
            if perform_research:
                research_content = self._perform_research(positions, research_queries)

            # Format prompt
            prompt = self._format_prompt(portfolio, positions, market_data, research_content)

            # Get decision from LLM
            decision = self._call_llm(prompt)

            # Store reasoning
            self._store_reasoning(research_content, decision)

            # Execute decision
            execution_result = self._execute_decision(decision)

            return {
                "success": True,
                "decision": decision,
                "execution": execution_result,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error making trading decision: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def _get_portfolio_state(self) -> Portfolio:
        """Get current portfolio state."""
        portfolio = self.db.query(Portfolio).filter(
            Portfolio.model_id == self.model_id
        ).first()

        if not portfolio:
            # Initialize portfolio if it doesn't exist
            logger.info(f"Initializing portfolio for model {self.model_id}")
            portfolio = self.trading_engine.initialize_portfolio(self.model_id)

        return portfolio

    def _get_positions(self) -> List[Position]:
        """Get current open positions."""
        positions = self.db.query(Position).filter(
            Position.model_id == self.model_id
        ).all()

        return positions

    def _get_market_data(self, positions: List[Position]) -> Dict[str, Any]:
        """
        Get market data for current positions.

        Args:
            positions: List of current positions

        Returns:
            Dictionary of market data
        """
        market_data = {}

        for position in positions:
            try:
                data = self.market_data.fetch_price(position.symbol)
                if data:
                    market_data[position.symbol] = data
            except Exception as e:
                logger.error(f"Failed to fetch market data for {position.symbol}: {e}")

        return market_data

    def _perform_research(
        self,
        positions: List[Position],
        custom_queries: Optional[List[str]] = None
    ) -> str:
        """
        Perform internet research using complete research orchestrator if available.

        Args:
            positions: Current positions
            custom_queries: Optional custom research queries

        Returns:
            Formatted research content
        """
        logger.info("Performing market research")

        # Use complete research orchestrator if available
        if self.use_complete_research and self.complete_research:
            logger.info("Using complete research orchestrator")

            # Research positions (limit to 3 most significant)
            symbols = [pos.symbol for pos in positions[:3]]

            if not symbols:
                # If no positions, research general market
                symbols = ["^GDAXI"]  # DAX index

            # Conduct complete research for each symbol
            all_research = []
            for symbol in symbols:
                try:
                    logger.info(f"Conducting complete research for {symbol}...")
                    research_result = self.complete_research.conduct_complete_research(
                        symbol=symbol,
                        include_technical=True,
                        include_financial_apis=True,
                        include_web_research=True,
                        include_quality_verification=False  # Skip verification for speed
                    )

                    if research_result.get("success") and research_result.get("unified_briefing"):
                        all_research.append(research_result["unified_briefing"])
                        logger.info(f"Complete research for {symbol} finished in {research_result['timing']['total']:.2f}s")
                    else:
                        logger.warning(f"Complete research failed for {symbol}: {research_result.get('errors')}")

                except Exception as e:
                    logger.error(f"Error in complete research for {symbol}: {e}", exc_info=True)

            if all_research:
                return "\n\n".join(all_research)
            else:
                logger.warning("Complete research failed for all symbols, falling back to basic research")

        # Fallback to basic research
        logger.info("Using basic research")

        # Collect symbols from positions
        symbols = [pos.symbol for pos in positions]

        # Default queries if none provided
        queries = custom_queries or [
            "German stock market news today",
            "DAX index outlook"
        ]

        # Aggregate research (limit to MAX_RESEARCH_SEARCHES)
        max_searches = getattr(settings, 'MAX_RESEARCH_SEARCHES', 2)
        limited_queries = queries[:max_searches]

        research_data = self.research.aggregate_research(
            symbols=symbols[:3],  # Limit to first 3 positions
            general_queries=limited_queries
        )

        # Format for LLM
        formatted_research = self.research.format_research_for_llm(research_data)

        return formatted_research

    def _format_prompt(
        self,
        portfolio: Portfolio,
        positions: List[Position],
        market_data: Dict[str, Any],
        research_content: str
    ) -> str:
        """
        Format the trading prompt for the LLM.

        Args:
            portfolio: Current portfolio
            positions: Open positions
            market_data: Market data dictionary
            research_content: Formatted research content

        Returns:
            Formatted prompt string
        """
        # Calculate portfolio metrics
        total_value = float(portfolio.total_value or portfolio.current_balance)
        total_pl = float(portfolio.total_pl or 0)
        pl_percentage = (total_pl / float(self.model.starting_balance)) * 100 if self.model.starting_balance > 0 else 0

        # Format positions
        positions_info = "No open positions"
        if positions:
            pos_lines = []
            for pos in positions:
                current_price = market_data.get(pos.symbol, {}).get('price', 0)
                unrealized_pl = (current_price - float(pos.avg_price)) * pos.quantity if current_price else 0
                unrealized_pl_pct = (unrealized_pl / (float(pos.avg_price) * pos.quantity)) * 100 if pos.avg_price > 0 else 0

                pos_lines.append(
                    f"- {pos.symbol}: {pos.quantity} shares @ €{pos.avg_price:.2f} avg "
                    f"(Current: €{current_price:.2f}, P&L: €{unrealized_pl:.2f} / {unrealized_pl_pct:.2f}%)"
                )
            positions_info = "\n".join(pos_lines)

        # Format market data
        market_data_info = "No market data available"
        if market_data:
            md_lines = []
            for symbol, data in market_data.items():
                md_lines.append(
                    f"- {symbol}: €{data['price']:.2f} "
                    f"(High: €{data.get('high', 0):.2f}, Low: €{data.get('low', 0):.2f}, "
                    f"Volume: {data.get('volume', 0):,})"
                )
            market_data_info = "\n".join(md_lines)

        # Format the complete prompt
        prompt = self.prompt_template.format(
            model_name=self.model.name,
            current_balance=float(portfolio.current_balance),
            total_value=total_value,
            total_pl=total_pl,
            pl_percentage=pl_percentage,
            num_positions=len(positions),
            positions_info=positions_info,
            market_data=market_data_info,
            research_content=research_content if research_content else "No research performed this session."
        )

        return prompt

    def _call_llm(self, prompt: str) -> Dict[str, Any]:
        """
        Call the LLM to get a trading decision.

        Args:
            prompt: Formatted prompt

        Returns:
            Parsed decision dictionary
        """
        logger.info(f"Calling LLM: {self.model.api_identifier}")

        messages = [
            {"role": "system", "content": "You are an expert stock trading AI."},
            {"role": "user", "content": prompt}
        ]

        try:
            response_text = self.openrouter.get_completion_text(
                model=self.model.api_identifier,
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )

            if not response_text:
                raise ValueError("Empty response from LLM")

            # Parse JSON response
            decision = self._parse_decision(response_text)

            logger.info(f"LLM decision: {decision['action']}")
            return decision

        except Exception as e:
            logger.error(f"Failed to get LLM decision: {e}")
            # Return HOLD decision on error
            return {
                "action": "HOLD",
                "reasoning": f"Error calling LLM: {str(e)}",
                "confidence": "LOW",
                "market_outlook": "Unknown",
                "risk_assessment": "High - LLM error"
            }

    def _parse_decision(self, response_text: str) -> Dict[str, Any]:
        """
        Parse and validate LLM decision response.

        Args:
            response_text: Raw LLM response

        Returns:
            Validated decision dictionary
        """
        try:
            # Extract JSON from response (may have markdown code blocks)
            json_text = response_text.strip()

            # Remove markdown code blocks if present
            if json_text.startswith("```"):
                lines = json_text.split("\n")
                json_text = "\n".join(lines[1:-1]) if len(lines) > 2 else json_text

            # Parse JSON
            decision = json.loads(json_text)

            # Validate required fields
            required_fields = ["action", "reasoning", "confidence"]
            for field in required_fields:
                if field not in decision:
                    raise ValueError(f"Missing required field: {field}")

            # Validate action
            valid_actions = ["BUY", "SELL", "HOLD"]
            if decision["action"] not in valid_actions:
                raise ValueError(f"Invalid action: {decision['action']}")

            # Validate symbol and quantity for BUY/SELL
            if decision["action"] in ["BUY", "SELL"]:
                if "symbol" not in decision or "quantity" not in decision:
                    raise ValueError("BUY/SELL actions require symbol and quantity")

            return decision

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON decision: {e}")
            logger.error(f"Response text: {response_text}")
            raise ValueError(f"Invalid JSON response: {e}")

    def _store_reasoning(self, research_content: str, decision: Dict[str, Any]):
        """
        Store the reasoning and decision in the database.

        Args:
            research_content: Research content
            decision: Trading decision
        """
        try:
            reasoning = Reasoning(
                model_id=self.model_id,
                research_content=research_content,
                decision=decision.get("action", "UNKNOWN"),
                reasoning_text=json.dumps(decision, indent=2),
                raw_response=decision
            )

            self.db.add(reasoning)
            self.db.commit()

            logger.info(f"Stored reasoning for model {self.model_id}")

        except Exception as e:
            logger.error(f"Failed to store reasoning: {e}")
            self.db.rollback()

    def _execute_decision(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the trading decision.

        Args:
            decision: Trading decision

        Returns:
            Execution result
        """
        action = decision["action"]

        if action == "HOLD":
            logger.info("Decision: HOLD - No action taken")
            return {
                "success": True,
                "action": "HOLD",
                "message": "No trading action taken"
            }

        symbol = decision["symbol"]
        quantity = int(decision["quantity"])

        try:
            if action == "BUY":
                logger.info(f"Executing BUY: {quantity} shares of {symbol}")
                result = self.trading_engine.execute_buy(
                    model_id=self.model_id,
                    symbol=symbol,
                    quantity=quantity
                )
                return result

            elif action == "SELL":
                logger.info(f"Executing SELL: {quantity} shares of {symbol}")
                result = self.trading_engine.execute_sell(
                    model_id=self.model_id,
                    symbol=symbol,
                    quantity=quantity
                )
                return result

        except Exception as e:
            logger.error(f"Failed to execute {action} order: {e}")
            return {
                "success": False,
                "action": action,
                "error": str(e)
            }

    def get_latest_reasoning(self) -> Optional[Reasoning]:
        """
        Get the latest reasoning entry for this model.

        Returns:
            Latest Reasoning object or None
        """
        return self.db.query(Reasoning).filter(
            Reasoning.model_id == self.model_id
        ).order_by(Reasoning.created_at.desc()).first()

    def close(self):
        """Clean up resources."""
        self.openrouter.close()
        self.research.close()
        logger.info(f"LLM Agent closed for model {self.model.name}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
