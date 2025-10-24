"""
Scheduler Service for Sentiment Arena

Handles automated trading schedules:
- Pre-market research (8:30 AM CET)
- Afternoon research (2:00 PM CET)
- Position value updates (every 15 minutes during market hours)
- End-of-day snapshots (5:35 PM CET)

Uses APScheduler with timezone-aware scheduling for German market hours.
"""

from datetime import datetime, time
from typing import List, Optional, Dict, Any
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from sqlalchemy.orm import Session

from backend.logger import get_logger
from backend.database.base import SessionLocal
from backend.services.market_data import MarketDataService
from backend.services.llm_agent import LLMAgent
from backend.services.trading_engine import TradingEngine
from backend.models.model import Model
from backend.models.portfolio import Portfolio
from backend.models.position import Position

logger = get_logger(__name__)

# German market holidays for 2024-2025
GERMAN_MARKET_HOLIDAYS = [
    # 2024
    "2024-01-01",  # New Year's Day
    "2024-03-29",  # Good Friday
    "2024-04-01",  # Easter Monday
    "2024-05-01",  # Labour Day
    "2024-12-24",  # Christmas Eve (half day)
    "2024-12-25",  # Christmas Day
    "2024-12-26",  # Boxing Day
    "2024-12-31",  # New Year's Eve (half day)

    # 2025
    "2025-01-01",  # New Year's Day
    "2025-04-18",  # Good Friday
    "2025-04-21",  # Easter Monday
    "2025-05-01",  # Labour Day
    "2025-12-24",  # Christmas Eve (half day)
    "2025-12-25",  # Christmas Day
    "2025-12-26",  # Boxing Day
    "2025-12-31",  # New Year's Eve (half day)

    # 2026
    "2026-01-01",  # New Year's Day
    "2026-04-03",  # Good Friday
    "2026-04-06",  # Easter Monday
    "2026-05-01",  # Labour Day
    "2026-12-24",  # Christmas Eve (half day)
    "2026-12-25",  # Christmas Day
    "2026-12-26",  # Boxing Day
    "2026-12-31",  # New Year's Eve (half day)
]


class TradingScheduler:
    """
    Manages automated trading schedules for Sentiment Arena.

    Schedules:
    - Pre-market research: 8:30 AM CET (before 9:00 AM market open)
    - Afternoon research: 2:00 PM CET (mid-day trading update)
    - Position updates: Every 15 minutes during market hours (9:00 AM - 5:30 PM)
    - End-of-day snapshot: 5:35 PM CET (after 5:30 PM market close)

    All times are in CET/CEST (Europe/Berlin timezone).
    """

    def __init__(
        self,
        market_data_service: Optional[MarketDataService] = None,
        openrouter_api_key: Optional[str] = None,
        alphavantage_api_key: Optional[str] = None,
        finnhub_api_key: Optional[str] = None
    ):
        """
        Initialize the trading scheduler.

        Args:
            market_data_service: Market data service instance
            openrouter_api_key: OpenRouter API key for LLM agents
            alphavantage_api_key: Alpha Vantage API key (optional)
            finnhub_api_key: Finnhub API key (optional)
        """
        self.scheduler = BackgroundScheduler(timezone=pytz.timezone('Europe/Berlin'))
        self.market_data_service = market_data_service or MarketDataService()
        self.openrouter_api_key = openrouter_api_key
        self.alphavantage_api_key = alphavantage_api_key
        self.finnhub_api_key = finnhub_api_key
        self.cet = pytz.timezone('Europe/Berlin')

        # Add event listeners
        self.scheduler.add_listener(self._job_executed_listener, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error_listener, EVENT_JOB_ERROR)

        logger.info("TradingScheduler initialized with CET timezone")

    def is_trading_day(self, date: Optional[datetime] = None) -> bool:
        """
        Check if a given date is a trading day (not weekend or holiday).

        Args:
            date: Date to check (defaults to today in CET)

        Returns:
            bool: True if trading day, False otherwise
        """
        if date is None:
            date = datetime.now(self.cet)

        # Check if weekend
        if date.weekday() >= 5:  # Saturday=5, Sunday=6
            return False

        # Check if holiday
        date_str = date.strftime("%Y-%m-%d")
        if date_str in GERMAN_MARKET_HOLIDAYS:
            return False

        return True

    def is_market_open(self, dt: Optional[datetime] = None) -> bool:
        """
        Check if the market is currently open.

        Market hours: 9:00 AM - 5:30 PM CET, Monday-Friday (excluding holidays)

        Args:
            dt: Datetime to check (defaults to now in CET)

        Returns:
            bool: True if market is open, False otherwise
        """
        if dt is None:
            dt = datetime.now(self.cet)

        # Check if trading day
        if not self.is_trading_day(dt):
            return False

        # Check market hours (9:00 - 17:30)
        market_open = time(9, 0)
        market_close = time(17, 30)
        current_time = dt.time()

        return market_open <= current_time <= market_close

    def pre_market_research_job(self):
        """
        Pre-market research job (8:30 AM CET).

        Triggers all models to:
        1. Research market conditions
        2. Analyze their positions
        3. Prepare trading decisions
        4. Store reasoning in database

        Note: Actual trades execute when market opens at 9:00 AM
        """
        logger.info("="*80)
        logger.info("PRE-MARKET RESEARCH JOB STARTED")
        logger.info("="*80)

        now = datetime.now(self.cet)

        # Verify it's a trading day
        if not self.is_trading_day(now):
            logger.info(f"Skipping pre-market research - not a trading day ({now.strftime('%Y-%m-%d')})")
            return

        db = SessionLocal()
        try:
            # Get all active models
            models = db.query(Model).all()
            logger.info(f"Running pre-market research for {len(models)} models")

            for model in models:
                try:
                    logger.info(f"\n--- Pre-market research for {model.name} (ID: {model.id}) ---")

                    # Create LLM agent for this model
                    agent = LLMAgent(
                        db=db,
                        model_id=model.id,
                        use_complete_research=True,
                        alphavantage_api_key=self.alphavantage_api_key,
                        finnhub_api_key=self.finnhub_api_key
                    )

                    # Perform research and generate decision
                    result = agent.make_trading_decision(perform_research=True)

                    if result["success"]:
                        decision = result["decision"]
                        logger.info(f"✓ {model.name} decision: {decision['action']}")
                        logger.info(f"  Reasoning: {decision['reasoning'][:200]}...")
                        logger.info(f"  Confidence: {decision.get('confidence', 'N/A')}")

                        # Log execution result
                        execution = result.get("execution", {})
                        if execution.get("success"):
                            logger.info(f"  Execution: {execution.get('message', 'Success')}")
                        else:
                            logger.warning(f"  Execution failed: {execution.get('error', 'Unknown error')}")
                    else:
                        logger.error(f"✗ {model.name} research failed: {result.get('error', 'Unknown error')}")

                except Exception as e:
                    logger.error(f"Error in pre-market research for {model.name}: {e}", exc_info=True)

            logger.info("="*80)
            logger.info("PRE-MARKET RESEARCH JOB COMPLETED")
            logger.info("="*80)

        finally:
            db.close()

    def afternoon_research_job(self):
        """
        Afternoon research job (2:00 PM CET).

        Triggers all models to:
        1. Research mid-day market developments
        2. Reassess their positions
        3. Make additional trading decisions
        4. Execute trades immediately (market is open)
        """
        logger.info("="*80)
        logger.info("AFTERNOON RESEARCH JOB STARTED")
        logger.info("="*80)

        now = datetime.now(self.cet)

        # Verify it's a trading day and market is open
        if not self.is_trading_day(now):
            logger.info(f"Skipping afternoon research - not a trading day ({now.strftime('%Y-%m-%d')})")
            return

        if not self.is_market_open(now):
            logger.warning(f"Skipping afternoon research - market is closed")
            return

        db = SessionLocal()
        try:
            # Get all active models
            models = db.query(Model).all()
            logger.info(f"Running afternoon research for {len(models)} models")

            for model in models:
                try:
                    logger.info(f"\n--- Afternoon research for {model.name} (ID: {model.id}) ---")

                    # Create LLM agent for this model
                    agent = LLMAgent(
                        db=db,
                        model_id=model.id,
                        use_complete_research=True,
                        alphavantage_api_key=self.alphavantage_api_key,
                        finnhub_api_key=self.finnhub_api_key
                    )

                    # Perform research and generate decision
                    result = agent.make_trading_decision(perform_research=True)

                    if result["success"]:
                        decision = result["decision"]
                        logger.info(f"✓ {model.name} decision: {decision['action']}")
                        logger.info(f"  Reasoning: {decision['reasoning'][:200]}...")
                        logger.info(f"  Confidence: {decision.get('confidence', 'N/A')}")

                        # Log execution result
                        execution = result.get("execution", {})
                        if execution.get("success"):
                            logger.info(f"  Execution: {execution.get('message', 'Success')}")
                        else:
                            logger.warning(f"  Execution failed: {execution.get('error', 'Unknown error')}")
                    else:
                        logger.error(f"✗ {model.name} research failed: {result.get('error', 'Unknown error')}")

                except Exception as e:
                    logger.error(f"Error in afternoon research for {model.name}: {e}", exc_info=True)

            logger.info("="*80)
            logger.info("AFTERNOON RESEARCH JOB COMPLETED")
            logger.info("="*80)

        finally:
            db.close()

    def update_position_values_job(self):
        """
        Update position values job (every 15 minutes during market hours).

        Updates current prices and unrealized P&L for all open positions.
        This runs only during market hours to track real-time performance.
        """
        now = datetime.now(self.cet)

        # Only run during market hours
        if not self.is_market_open(now):
            return

        logger.info("Updating position values...")

        db = SessionLocal()
        try:
            # Get all open positions
            positions = db.query(Position).all()

            if not positions:
                logger.info("No open positions to update")
                return

            # Create trading engine for position updates
            engine = TradingEngine(db, self.market_data_service)

            # Group positions by model_id
            models_with_positions = {}
            for position in positions:
                if position.model_id not in models_with_positions:
                    models_with_positions[position.model_id] = []
                models_with_positions[position.model_id].append(position)

            # Update positions for each model
            for model_id, model_positions in models_with_positions.items():
                try:
                    # Update position values
                    engine.update_position_values(model_id)

                    # Get updated portfolio value
                    portfolio = db.query(Portfolio).filter(Portfolio.model_id == model_id).first()
                    if portfolio:
                        total_value = engine.calculate_portfolio_value(model_id)
                        logger.info(
                            f"Model {model_id}: {len(model_positions)} positions, "
                            f"Total value: €{total_value:.2f}"
                        )

                except Exception as e:
                    logger.error(f"Error updating positions for model {model_id}: {e}")

            db.commit()
            logger.info(f"✓ Updated {len(positions)} positions across {len(models_with_positions)} models")

        except Exception as e:
            logger.error(f"Error in position update job: {e}", exc_info=True)
            db.rollback()

        finally:
            db.close()

    def end_of_day_snapshot_job(self):
        """
        End-of-day snapshot job (5:35 PM CET, after market close).

        Creates daily performance snapshots:
        1. Final position values at close
        2. Daily P&L calculation
        3. Portfolio performance metrics
        4. Store in database for historical tracking
        """
        logger.info("="*80)
        logger.info("END-OF-DAY SNAPSHOT JOB STARTED")
        logger.info("="*80)

        now = datetime.now(self.cet)

        # Only run on trading days
        if not self.is_trading_day(now):
            logger.info(f"Skipping EOD snapshot - not a trading day ({now.strftime('%Y-%m-%d')})")
            return

        db = SessionLocal()
        try:
            # Get all models
            models = db.query(Model).all()
            logger.info(f"Creating EOD snapshot for {len(models)} models")

            # Create trading engine
            engine = TradingEngine(db, self.market_data_service)

            for model in models:
                try:
                    # Get portfolio
                    portfolio = db.query(Portfolio).filter(Portfolio.model_id == model.id).first()
                    if not portfolio:
                        logger.warning(f"No portfolio found for {model.name}")
                        continue

                    # Update final position values
                    engine.update_position_values(model.id)

                    # Calculate final portfolio value
                    total_value = engine.calculate_portfolio_value(model.id)

                    # Get performance metrics
                    metrics = engine.get_performance_metrics(model.id)

                    logger.info(f"\n--- EOD Snapshot: {model.name} ---")
                    logger.info(f"  Total Value: €{total_value:.2f}")
                    logger.info(f"  Cash Balance: €{portfolio.current_balance:.2f}")
                    logger.info(f"  Total P&L: €{portfolio.total_pl:.2f} ({portfolio.total_pl / model.starting_balance * 100:.2f}%)")
                    logger.info(f"  Total Trades: {metrics.get('total_trades', 0)}")
                    logger.info(f"  Win Rate: {metrics.get('win_rate', 0):.1f}%")
                    logger.info(f"  Total Fees Paid: €{metrics.get('total_fees_paid', 0):.2f}")

                    # Get open positions
                    positions = db.query(Position).filter(Position.model_id == model.id).all()
                    if positions:
                        logger.info(f"  Open Positions: {len(positions)}")
                        for pos in positions:
                            logger.info(
                                f"    - {pos.symbol}: {pos.quantity} @ €{pos.avg_price:.2f} "
                                f"(Current: €{pos.current_price:.2f}, P&L: €{pos.unrealized_pl:.2f})"
                            )
                    else:
                        logger.info(f"  Open Positions: 0")

                except Exception as e:
                    logger.error(f"Error creating EOD snapshot for {model.name}: {e}", exc_info=True)

            db.commit()

            logger.info("="*80)
            logger.info("END-OF-DAY SNAPSHOT JOB COMPLETED")
            logger.info("="*80)

        except Exception as e:
            logger.error(f"Error in EOD snapshot job: {e}", exc_info=True)
            db.rollback()

        finally:
            db.close()

    def _job_executed_listener(self, event):
        """Listener for successful job executions."""
        logger.debug(f"Job {event.job_id} executed successfully at {datetime.now(self.cet)}")

    def _job_error_listener(self, event):
        """Listener for job execution errors."""
        logger.error(f"Job {event.job_id} raised an error: {event.exception}", exc_info=True)

    def add_jobs(self):
        """
        Add all scheduled jobs to the scheduler.

        Jobs:
        - Pre-market research: 8:30 AM CET (Mon-Fri)
        - Afternoon research: 2:00 PM CET (Mon-Fri)
        - Position updates: Every 15 minutes (9:00 AM - 5:30 PM, Mon-Fri)
        - EOD snapshot: 5:35 PM CET (Mon-Fri)
        """
        # Pre-market research job (8:30 AM CET, Mon-Fri)
        self.scheduler.add_job(
            self.pre_market_research_job,
            trigger=CronTrigger(
                hour=8,
                minute=30,
                day_of_week='mon-fri',
                timezone=self.cet
            ),
            id='pre_market_research',
            name='Pre-Market Research',
            replace_existing=True
        )
        logger.info("✓ Added job: Pre-Market Research (8:30 AM CET, Mon-Fri)")

        # Afternoon research job (2:00 PM CET, Mon-Fri)
        self.scheduler.add_job(
            self.afternoon_research_job,
            trigger=CronTrigger(
                hour=14,
                minute=0,
                day_of_week='mon-fri',
                timezone=self.cet
            ),
            id='afternoon_research',
            name='Afternoon Research',
            replace_existing=True
        )
        logger.info("✓ Added job: Afternoon Research (2:00 PM CET, Mon-Fri)")

        # Position value update job (every 15 minutes during market hours)
        # Runs from 9:00 AM to 5:30 PM, but checks if market is open
        self.scheduler.add_job(
            self.update_position_values_job,
            trigger=IntervalTrigger(
                minutes=15,
                timezone=self.cet
            ),
            id='position_value_update',
            name='Position Value Update',
            replace_existing=True
        )
        logger.info("✓ Added job: Position Value Update (every 15 minutes)")

        # End-of-day snapshot job (5:35 PM CET, Mon-Fri)
        self.scheduler.add_job(
            self.end_of_day_snapshot_job,
            trigger=CronTrigger(
                hour=17,
                minute=35,
                day_of_week='mon-fri',
                timezone=self.cet
            ),
            id='end_of_day_snapshot',
            name='End-of-Day Snapshot',
            replace_existing=True
        )
        logger.info("✓ Added job: End-of-Day Snapshot (5:35 PM CET, Mon-Fri)")

    def start(self):
        """Start the scheduler."""
        if not self.scheduler.running:
            self.add_jobs()
            self.scheduler.start()
            logger.info("="*80)
            logger.info("TRADING SCHEDULER STARTED")
            logger.info("="*80)
            logger.info(f"Timezone: {self.cet}")
            logger.info(f"Current time: {datetime.now(self.cet).strftime('%Y-%m-%d %H:%M:%S %Z')}")
            logger.info(f"Market open: {self.is_market_open()}")
            logger.info(f"Trading day: {self.is_trading_day()}")
            logger.info("="*80)

            # Print next run times
            jobs = self.scheduler.get_jobs()
            logger.info("\nScheduled Jobs:")
            for job in jobs:
                next_run = job.next_run_time
                if next_run:
                    logger.info(f"  - {job.name}: Next run at {next_run.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        else:
            logger.warning("Scheduler is already running")

    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            logger.info("Trading Scheduler stopped")
        else:
            logger.warning("Scheduler is not running")

    def get_job_status(self) -> Dict[str, Any]:
        """
        Get status of all scheduled jobs.

        Returns:
            dict: Status information for all jobs
        """
        jobs = self.scheduler.get_jobs()

        job_info = []
        for job in jobs:
            # Get next run time - handle different attribute names
            next_run = getattr(job, 'next_run_time', None)
            if next_run is None:
                # Try alternative attribute name for different APScheduler versions
                next_run = getattr(job, '_next_run_time', None)

            job_info.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": next_run.isoformat() if next_run else None,
                "trigger": str(job.trigger)
            })

        return {
            "scheduler_running": self.scheduler.running,
            "current_time_cet": datetime.now(self.cet).isoformat(),
            "market_open": self.is_market_open(),
            "trading_day": self.is_trading_day(),
            "jobs": job_info
        }

    def trigger_job_now(self, job_id: str):
        """
        Manually trigger a job to run immediately.

        Args:
            job_id: ID of the job to trigger

        Raises:
            ValueError: If job_id is not found
        """
        job = self.scheduler.get_job(job_id)
        if not job:
            raise ValueError(f"Job with ID '{job_id}' not found")

        logger.info(f"Manually triggering job: {job.name} (ID: {job_id})")
        job.modify(next_run_time=datetime.now(self.cet))

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
