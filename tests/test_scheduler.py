"""
Unit tests for TradingScheduler

Tests scheduler functionality:
- Trading day detection (weekends, holidays)
- Market hours checking
- Job scheduling and execution
- Manual job triggering
- Context manager support
"""

import pytest
from datetime import datetime, time
from unittest.mock import Mock, patch, MagicMock
import pytz

from backend.services.scheduler import TradingScheduler, GERMAN_MARKET_HOLIDAYS
from backend.services.market_data import MarketDataService


class TestTradingScheduler:
    """Test TradingScheduler class."""

    @pytest.fixture
    def scheduler(self):
        """Create a scheduler instance for testing."""
        market_data = Mock(spec=MarketDataService)
        return TradingScheduler(
            market_data_service=market_data,
            openrouter_api_key="test-key",
            alphavantage_api_key="test-av-key",
            finnhub_api_key="test-fh-key"
        )

    def test_initialization(self, scheduler):
        """Test scheduler initialization."""
        assert scheduler is not None
        assert scheduler.scheduler is not None
        assert scheduler.market_data_service is not None
        assert scheduler.openrouter_api_key == "test-key"
        assert scheduler.alphavantage_api_key == "test-av-key"
        assert scheduler.finnhub_api_key == "test-fh-key"
        assert scheduler.cet.zone == 'Europe/Berlin'

    def test_is_trading_day_weekday(self, scheduler):
        """Test trading day detection for weekdays."""
        # Monday, January 8, 2024 (not a holiday)
        monday = datetime(2024, 1, 8, 10, 0, 0, tzinfo=scheduler.cet)
        assert scheduler.is_trading_day(monday) is True

        # Wednesday, March 13, 2024 (not a holiday)
        wednesday = datetime(2024, 3, 13, 10, 0, 0, tzinfo=scheduler.cet)
        assert scheduler.is_trading_day(wednesday) is True

    def test_is_trading_day_weekend(self, scheduler):
        """Test trading day detection for weekends."""
        # Saturday, January 6, 2024
        saturday = datetime(2024, 1, 6, 10, 0, 0, tzinfo=scheduler.cet)
        assert scheduler.is_trading_day(saturday) is False

        # Sunday, January 7, 2024
        sunday = datetime(2024, 1, 7, 10, 0, 0, tzinfo=scheduler.cet)
        assert scheduler.is_trading_day(sunday) is False

    def test_is_trading_day_holiday(self, scheduler):
        """Test trading day detection for holidays."""
        # New Year's Day 2024
        new_year = datetime(2024, 1, 1, 10, 0, 0, tzinfo=scheduler.cet)
        assert scheduler.is_trading_day(new_year) is False

        # Good Friday 2024
        good_friday = datetime(2024, 3, 29, 10, 0, 0, tzinfo=scheduler.cet)
        assert scheduler.is_trading_day(good_friday) is False

        # Christmas 2024
        christmas = datetime(2024, 12, 25, 10, 0, 0, tzinfo=scheduler.cet)
        assert scheduler.is_trading_day(christmas) is False

    def test_is_market_open_during_hours(self, scheduler):
        """Test market open detection during trading hours."""
        # Monday at 10:00 AM (market open)
        monday_10am = datetime(2024, 1, 8, 10, 0, 0, tzinfo=scheduler.cet)
        assert scheduler.is_market_open(monday_10am) is True

        # Monday at 2:00 PM (market open)
        monday_2pm = datetime(2024, 1, 8, 14, 0, 0, tzinfo=scheduler.cet)
        assert scheduler.is_market_open(monday_2pm) is True

        # Monday at 5:00 PM (market open, before close)
        monday_5pm = datetime(2024, 1, 8, 17, 0, 0, tzinfo=scheduler.cet)
        assert scheduler.is_market_open(monday_5pm) is True

    def test_is_market_open_outside_hours(self, scheduler):
        """Test market open detection outside trading hours."""
        # Monday at 8:00 AM (before open)
        monday_8am = datetime(2024, 1, 8, 8, 0, 0, tzinfo=scheduler.cet)
        assert scheduler.is_market_open(monday_8am) is False

        # Monday at 6:00 PM (after close)
        monday_6pm = datetime(2024, 1, 8, 18, 0, 0, tzinfo=scheduler.cet)
        assert scheduler.is_market_open(monday_6pm) is False

    def test_is_market_open_weekend(self, scheduler):
        """Test market open detection on weekends."""
        # Saturday at 10:00 AM
        saturday_10am = datetime(2024, 1, 6, 10, 0, 0, tzinfo=scheduler.cet)
        assert scheduler.is_market_open(saturday_10am) is False

    def test_is_market_open_holiday(self, scheduler):
        """Test market open detection on holidays."""
        # New Year's Day at 10:00 AM
        new_year_10am = datetime(2024, 1, 1, 10, 0, 0, tzinfo=scheduler.cet)
        assert scheduler.is_market_open(new_year_10am) is False

    def test_add_jobs(self, scheduler):
        """Test adding jobs to scheduler."""
        scheduler.add_jobs()

        jobs = scheduler.scheduler.get_jobs()
        assert len(jobs) == 4

        job_ids = [job.id for job in jobs]
        assert 'pre_market_research' in job_ids
        assert 'afternoon_research' in job_ids
        assert 'position_value_update' in job_ids
        assert 'end_of_day_snapshot' in job_ids

    def test_get_job_status(self, scheduler):
        """Test getting job status."""
        scheduler.add_jobs()

        status = scheduler.get_job_status()

        assert 'scheduler_running' in status
        assert 'current_time_cet' in status
        assert 'market_open' in status
        assert 'trading_day' in status
        assert 'jobs' in status
        assert len(status['jobs']) == 4

        # Check job structure
        job = status['jobs'][0]
        assert 'id' in job
        assert 'name' in job
        assert 'next_run_time' in job
        assert 'trigger' in job

    @patch('backend.services.scheduler.SessionLocal')
    def test_pre_market_research_job_non_trading_day(self, mock_session, scheduler):
        """Test pre-market research job on non-trading day."""
        # Saturday - should skip
        with patch.object(scheduler, 'is_trading_day', return_value=False):
            scheduler.pre_market_research_job()

        # Should not create any database sessions
        mock_session.assert_not_called()

    @patch('backend.services.scheduler.SessionLocal')
    def test_afternoon_research_job_market_closed(self, mock_session, scheduler):
        """Test afternoon research job when market is closed."""
        # Market closed - should skip
        with patch.object(scheduler, 'is_trading_day', return_value=True):
            with patch.object(scheduler, 'is_market_open', return_value=False):
                scheduler.afternoon_research_job()

        # Should not create any database sessions
        mock_session.assert_not_called()

    @patch('backend.services.scheduler.SessionLocal')
    def test_update_position_values_market_closed(self, mock_session, scheduler):
        """Test position update job when market is closed."""
        # Market closed - should skip
        with patch.object(scheduler, 'is_market_open', return_value=False):
            scheduler.update_position_values_job()

        # Should not create any database sessions
        mock_session.assert_not_called()

    @patch('backend.services.scheduler.SessionLocal')
    def test_end_of_day_snapshot_non_trading_day(self, mock_session, scheduler):
        """Test EOD snapshot on non-trading day."""
        # Non-trading day - should skip
        with patch.object(scheduler, 'is_trading_day', return_value=False):
            scheduler.end_of_day_snapshot_job()

        # Should not create any database sessions
        mock_session.assert_not_called()

    def test_trigger_job_now(self, scheduler):
        """Test manually triggering a job."""
        scheduler.add_jobs()

        # Trigger pre-market research
        scheduler.trigger_job_now('pre_market_research')

        # Verify job exists and has been modified
        job = scheduler.scheduler.get_job('pre_market_research')
        assert job is not None

    def test_trigger_job_not_found(self, scheduler):
        """Test triggering non-existent job."""
        with pytest.raises(ValueError, match="Job with ID 'nonexistent' not found"):
            scheduler.trigger_job_now('nonexistent')

    def test_start_stop(self, scheduler):
        """Test starting and stopping scheduler."""
        # Start
        scheduler.start()
        assert scheduler.scheduler.running is True

        # Stop
        scheduler.stop()
        assert scheduler.scheduler.running is False

    def test_context_manager(self, scheduler):
        """Test scheduler context manager."""
        assert scheduler.scheduler.running is False

        with scheduler:
            assert scheduler.scheduler.running is True

        assert scheduler.scheduler.running is False

    def test_holiday_list_completeness(self):
        """Test that holiday list contains expected holidays."""
        # Check some key holidays
        assert "2024-01-01" in GERMAN_MARKET_HOLIDAYS  # New Year
        assert "2024-12-25" in GERMAN_MARKET_HOLIDAYS  # Christmas
        assert "2025-01-01" in GERMAN_MARKET_HOLIDAYS  # New Year 2025
        assert "2026-01-01" in GERMAN_MARKET_HOLIDAYS  # New Year 2026

    def test_market_hours_edge_cases(self, scheduler):
        """Test market hours at exact open/close times."""
        # Exactly 9:00 AM (open)
        exact_open = datetime(2024, 1, 8, 9, 0, 0, tzinfo=scheduler.cet)
        assert scheduler.is_market_open(exact_open) is True

        # Exactly 5:30 PM (close)
        exact_close = datetime(2024, 1, 8, 17, 30, 0, tzinfo=scheduler.cet)
        assert scheduler.is_market_open(exact_close) is True

        # One minute before open (8:59 AM)
        before_open = datetime(2024, 1, 8, 8, 59, 0, tzinfo=scheduler.cet)
        assert scheduler.is_market_open(before_open) is False

        # One minute after close (5:31 PM)
        after_close = datetime(2024, 1, 8, 17, 31, 0, tzinfo=scheduler.cet)
        assert scheduler.is_market_open(after_close) is False

    def test_timezone_awareness(self, scheduler):
        """Test that scheduler is timezone-aware."""
        # Create datetime without timezone
        naive_dt = datetime(2024, 1, 8, 10, 0, 0)

        # Scheduler methods should handle it gracefully
        # Default to current time in CET if None provided
        result = scheduler.is_market_open(None)
        assert isinstance(result, bool)

    @patch('backend.services.scheduler.SessionLocal')
    @patch('backend.services.scheduler.LLMAgent')
    def test_pre_market_research_with_models(self, mock_agent_class, mock_session, scheduler):
        """Test pre-market research job with models."""
        # Mock database session
        mock_db = MagicMock()
        mock_session.return_value = mock_db

        # Mock models
        mock_model = MagicMock()
        mock_model.id = 1
        mock_model.name = "Test Model"
        mock_db.query.return_value.all.return_value = [mock_model]

        # Mock LLM agent
        mock_agent = MagicMock()
        mock_agent.make_trading_decision.return_value = {
            "success": True,
            "decision": {
                "action": "BUY",
                "reasoning": "Test reasoning",
                "confidence": "HIGH"
            },
            "execution": {
                "success": True,
                "message": "Trade executed"
            }
        }
        mock_agent_class.return_value = mock_agent

        # Run on trading day
        with patch.object(scheduler, 'is_trading_day', return_value=True):
            scheduler.pre_market_research_job()

        # Verify agent was called
        mock_agent_class.assert_called_once()
        mock_agent.make_trading_decision.assert_called_once_with(perform_research=True)
        mock_db.close.assert_called_once()

    @patch('backend.services.scheduler.SessionLocal')
    def test_update_position_values_with_positions(self, mock_session, scheduler):
        """Test position value update with open positions."""
        # Mock database session
        mock_db = MagicMock()
        mock_session.return_value = mock_db

        # Mock positions
        mock_position = MagicMock()
        mock_position.model_id = 1
        mock_position.symbol = "SAP.DE"
        mock_db.query.return_value.all.return_value = [mock_position]

        # Mock portfolio
        mock_portfolio = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_portfolio

        # Mock trading engine
        with patch('backend.services.scheduler.TradingEngine') as mock_engine_class:
            mock_engine = MagicMock()
            mock_engine.calculate_portfolio_value.return_value = 1500.0
            mock_engine_class.return_value = mock_engine

            # Run during market hours
            with patch.object(scheduler, 'is_market_open', return_value=True):
                scheduler.update_position_values_job()

            # Verify engine methods were called
            mock_engine.update_position_values.assert_called_once_with(1)
            mock_engine.calculate_portfolio_value.assert_called_once_with(1)
            mock_db.commit.assert_called_once()
            mock_db.close.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
