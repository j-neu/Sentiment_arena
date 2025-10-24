"""
Unit tests for TradingEngine

Tests all trading operations including:
- Portfolio initialization
- Order validation
- Buy/sell execution
- Position management
- P&L calculations
"""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

from backend.database.base import SessionLocal, engine, Base
from backend.models.model import Model
from backend.models.portfolio import Portfolio
from backend.models.position import Position
from backend.models.trade import Trade, TradeSide, TradeStatus
from backend.services.trading_engine import TradingEngine


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create session
    db = SessionLocal()

    yield db

    # Cleanup
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def trading_engine(db_session):
    """Create a TradingEngine instance."""
    return TradingEngine(db_session)


@pytest.fixture
def test_model(db_session):
    """Create a test model."""
    model = Model(
        name="Test Model",
        api_identifier="test/model-1",
        starting_balance=Decimal('1000.00')
    )
    db_session.add(model)
    db_session.commit()
    db_session.refresh(model)
    return model


class TestPortfolioInitialization:
    """Test portfolio initialization."""

    def test_initialize_portfolio_success(self, trading_engine, test_model, db_session):
        """Test successful portfolio initialization."""
        portfolio = trading_engine.initialize_portfolio(test_model.id)

        assert portfolio is not None
        assert portfolio.model_id == test_model.id
        assert portfolio.current_balance == Decimal('1000.00')
        assert portfolio.total_pl == Decimal('0.00')
        assert portfolio.total_value == Decimal('1000.00')

    def test_initialize_portfolio_already_exists(self, trading_engine, test_model, db_session):
        """Test that initializing an existing portfolio raises error."""
        trading_engine.initialize_portfolio(test_model.id)

        with pytest.raises(ValueError, match="already exists"):
            trading_engine.initialize_portfolio(test_model.id)

    def test_initialize_portfolio_invalid_model(self, trading_engine, db_session):
        """Test initializing portfolio for non-existent model."""
        with pytest.raises(ValueError, match="does not exist"):
            trading_engine.initialize_portfolio(999)

    def test_get_portfolio(self, trading_engine, test_model, db_session):
        """Test retrieving portfolio."""
        trading_engine.initialize_portfolio(test_model.id)
        portfolio = trading_engine.get_portfolio(test_model.id)

        assert portfolio is not None
        assert portfolio.model_id == test_model.id

    def test_get_portfolio_not_found(self, trading_engine, db_session):
        """Test retrieving non-existent portfolio."""
        portfolio = trading_engine.get_portfolio(999)
        assert portfolio is None


class TestOrderValidation:
    """Test order validation logic."""

    @pytest.fixture(autouse=True)
    def setup(self, trading_engine, test_model, db_session):
        """Set up test portfolio."""
        self.engine = trading_engine
        self.model = test_model
        self.engine.initialize_portfolio(test_model.id)

    def test_validate_invalid_side(self):
        """Test validation with invalid order side."""
        result = self.engine.validate_order(self.model.id, "SAP.DE", "invalid", 10)

        assert result['valid'] is False
        assert "Invalid side" in result['reason']

    def test_validate_invalid_quantity(self):
        """Test validation with invalid quantity."""
        result = self.engine.validate_order(self.model.id, "SAP.DE", "buy", 0)

        assert result['valid'] is False
        assert "Invalid quantity" in result['reason']

    def test_validate_invalid_symbol(self):
        """Test validation with invalid symbol."""
        result = self.engine.validate_order(self.model.id, "AAPL", "buy", 10)

        assert result['valid'] is False
        assert "Invalid symbol" in result['reason']

    @patch('backend.services.trading_engine.MarketDataService.is_market_open')
    def test_validate_market_closed(self, mock_market_open):
        """Test validation when market is closed."""
        mock_market_open.return_value = False

        result = self.engine.validate_order(self.model.id, "SAP.DE", "buy", 10)

        assert result['valid'] is False
        assert "Market is closed" in result['reason']

    @patch('backend.services.trading_engine.MarketDataService.is_market_open')
    @patch('backend.services.trading_engine.MarketDataService.fetch_price')
    def test_validate_insufficient_balance_for_buy(self, mock_fetch, mock_market_open):
        """Test buy order validation with insufficient balance."""
        mock_market_open.return_value = True
        mock_fetch.return_value = {'price': 200.0, 'volume': 1000}

        # Try to buy 10 shares at €200 = €2000 + €5 fee = €2005 (have €1000)
        result = self.engine.validate_order(self.model.id, "SAP.DE", "buy", 10)

        assert result['valid'] is False
        assert "Insufficient balance" in result['reason']

    @patch('backend.services.trading_engine.MarketDataService.is_market_open')
    @patch('backend.services.trading_engine.MarketDataService.fetch_price')
    def test_validate_sell_no_position(self, mock_fetch, mock_market_open):
        """Test sell order validation with no position."""
        mock_market_open.return_value = True
        mock_fetch.return_value = {'price': 100.0, 'volume': 1000}

        result = self.engine.validate_order(self.model.id, "SAP.DE", "sell", 10)

        assert result['valid'] is False
        assert "No position" in result['reason']

    @patch('backend.services.trading_engine.MarketDataService.is_market_open')
    @patch('backend.services.trading_engine.MarketDataService.fetch_price')
    def test_validate_sell_insufficient_shares(self, mock_fetch, mock_market_open, db_session):
        """Test sell order validation with insufficient shares."""
        mock_market_open.return_value = True
        mock_fetch.return_value = {'price': 100.0, 'volume': 1000}

        # Create a small position
        position = Position(
            model_id=self.model.id,
            symbol="SAP.DE",
            quantity=5,
            avg_price=Decimal('100.00'),
            current_price=Decimal('100.00'),
            unrealized_pl=Decimal('0.00')
        )
        db_session.add(position)
        db_session.commit()

        # Try to sell more than we have
        result = self.engine.validate_order(self.model.id, "SAP.DE", "sell", 10)

        assert result['valid'] is False
        assert "Insufficient shares" in result['reason']

    @patch('backend.services.trading_engine.MarketDataService.is_market_open')
    @patch('backend.services.trading_engine.MarketDataService.fetch_price')
    def test_validate_buy_success(self, mock_fetch, mock_market_open):
        """Test successful buy order validation."""
        mock_market_open.return_value = True
        mock_fetch.return_value = {'price': 50.0, 'volume': 1000}

        # Buy 10 shares at €50 = €500 + €5 fee = €505 (have €1000)
        result = self.engine.validate_order(self.model.id, "SAP.DE", "buy", 10)

        assert result['valid'] is True
        assert result['price'] == 50.0


class TestBuyExecution:
    """Test buy order execution."""

    @pytest.fixture(autouse=True)
    def setup(self, trading_engine, test_model, db_session):
        """Set up test portfolio."""
        self.engine = trading_engine
        self.model = test_model
        self.db = db_session
        self.engine.initialize_portfolio(test_model.id)

    @patch('backend.services.trading_engine.MarketDataService.is_market_open')
    @patch('backend.services.trading_engine.MarketDataService.fetch_price')
    def test_execute_buy_new_position(self, mock_fetch, mock_market_open):
        """Test buying a new position."""
        mock_market_open.return_value = True
        mock_fetch.return_value = {'price': 100.0, 'volume': 1000}

        result = self.engine.execute_buy(self.model.id, "SAP.DE", 5)

        assert result['success'] is True
        assert result['execution_price'] == 100.0
        assert result['total_cost'] == 505.0  # 5 * 100 + 5 fee

        # Check trade was created
        trade = result['trade']
        assert trade.side == TradeSide.BUY
        assert trade.quantity == 5
        assert trade.price == 100.0
        assert trade.fee == 5.0

        # Check position was created
        position = result['position']
        assert position.symbol == "SAP.DE"
        assert position.quantity == 5
        assert position.avg_price == 100.0

        # Check portfolio was updated
        portfolio = self.engine.get_portfolio(self.model.id)
        assert abs(portfolio.current_balance - 495.0) < 0.01  # 1000 - 505

    @patch('backend.services.trading_engine.MarketDataService.is_market_open')
    @patch('backend.services.trading_engine.MarketDataService.fetch_price')
    def test_execute_buy_add_to_position(self, mock_fetch, mock_market_open):
        """Test adding to an existing position."""
        mock_market_open.return_value = True

        # First buy at €50
        mock_fetch.return_value = {'price': 50.0, 'volume': 1000}
        self.engine.execute_buy(self.model.id, "SAP.DE", 5)
        # Cost: 50*5 + 5 = 255, balance after: 1000 - 255 = 745

        # Second buy at €70
        mock_fetch.return_value = {'price': 70.0, 'volume': 1000}
        result = self.engine.execute_buy(self.model.id, "SAP.DE", 5)
        # Cost: 70*5 + 5 = 355, balance after: 745 - 355 = 390

        assert result['success'] is True

        # Check position has correct average price
        # (50*5 + 70*5) / 10 = (250 + 350) / 10 = 60
        position = result['position']
        assert position.quantity == 10
        assert abs(position.avg_price - 60.0) < 0.01

        # Check portfolio balance: 1000 - 255 - 355 = 390
        portfolio = self.engine.get_portfolio(self.model.id)
        assert abs(portfolio.current_balance - 390.0) < 0.01

    @patch('backend.services.trading_engine.MarketDataService.is_market_open')
    @patch('backend.services.trading_engine.MarketDataService.fetch_price')
    def test_execute_buy_add_to_position_valid(self, mock_fetch, mock_market_open):
        """Test adding to an existing position with sufficient balance."""
        mock_market_open.return_value = True

        # First buy at €50
        mock_fetch.return_value = {'price': 50.0, 'volume': 1000}
        self.engine.execute_buy(self.model.id, "SAP.DE", 5)

        # Second buy at €60
        mock_fetch.return_value = {'price': 60.0, 'volume': 1000}
        result = self.engine.execute_buy(self.model.id, "SAP.DE", 5)

        assert result['success'] is True

        # Check position has correct average price
        # (50*5 + 60*5) / 10 = 55
        position = result['position']
        assert position.quantity == 10
        assert abs(position.avg_price - 55.0) < 0.01

        # Check portfolio balance
        # 1000 - 255 - 305 = 440
        portfolio = self.engine.get_portfolio(self.model.id)
        assert abs(portfolio.current_balance - 440.0) < 0.01

    @patch('backend.services.trading_engine.MarketDataService.is_market_open')
    @patch('backend.services.trading_engine.MarketDataService.fetch_price')
    def test_execute_buy_insufficient_balance(self, mock_fetch, mock_market_open):
        """Test buy fails with insufficient balance."""
        mock_market_open.return_value = True
        mock_fetch.return_value = {'price': 200.0, 'volume': 1000}

        result = self.engine.execute_buy(self.model.id, "SAP.DE", 10)

        assert result['success'] is False
        assert "Insufficient balance" in result['reason']


class TestSellExecution:
    """Test sell order execution."""

    @pytest.fixture(autouse=True)
    def setup(self, trading_engine, test_model, db_session):
        """Set up test portfolio with a position."""
        self.engine = trading_engine
        self.model = test_model
        self.db = db_session
        self.engine.initialize_portfolio(test_model.id)

    @patch('backend.services.trading_engine.MarketDataService.is_market_open')
    @patch('backend.services.trading_engine.MarketDataService.fetch_price')
    def test_execute_sell_full_position_profit(self, mock_fetch, mock_market_open):
        """Test selling entire position at a profit."""
        mock_market_open.return_value = True

        # Buy at €50
        mock_fetch.return_value = {'price': 50.0, 'volume': 1000}
        self.engine.execute_buy(self.model.id, "SAP.DE", 10)

        # Sell at €60
        mock_fetch.return_value = {'price': 60.0, 'volume': 1000}
        result = self.engine.execute_sell(self.model.id, "SAP.DE", 10)

        assert result['success'] is True
        assert result['execution_price'] == 60.0

        # Proceeds: 60 * 10 - 5 fee = 595
        assert result['total_proceeds'] == 595.0

        # Realized P&L: (60 - 50) * 10 - 5 fee = 95
        assert result['realized_pl'] == 95.0

        # Position should be closed
        assert result['position'] is None

        # Check portfolio
        portfolio = self.engine.get_portfolio(self.model.id)
        # Starting: 1000
        # After buy: 1000 - 505 = 495
        # After sell: 495 + 595 = 1090
        assert abs(portfolio.current_balance - 1090.0) < 0.01
        assert abs(portfolio.total_pl - 95.0) < 0.01

    @patch('backend.services.trading_engine.MarketDataService.is_market_open')
    @patch('backend.services.trading_engine.MarketDataService.fetch_price')
    def test_execute_sell_full_position_loss(self, mock_fetch, mock_market_open):
        """Test selling entire position at a loss."""
        mock_market_open.return_value = True

        # Buy at €100
        mock_fetch.return_value = {'price': 100.0, 'volume': 1000}
        self.engine.execute_buy(self.model.id, "BMW.DE", 5)

        # Sell at €80
        mock_fetch.return_value = {'price': 80.0, 'volume': 1000}
        result = self.engine.execute_sell(self.model.id, "BMW.DE", 5)

        assert result['success'] is True

        # Realized P&L: (80 - 100) * 5 - 5 fee = -105
        assert result['realized_pl'] == -105.0

        # Position should be closed
        assert result['position'] is None

        # Check portfolio
        portfolio = self.engine.get_portfolio(self.model.id)
        assert abs(portfolio.total_pl - (-105.0)) < 0.01

    @patch('backend.services.trading_engine.MarketDataService.is_market_open')
    @patch('backend.services.trading_engine.MarketDataService.fetch_price')
    def test_execute_sell_partial_position(self, mock_fetch, mock_market_open):
        """Test selling part of a position."""
        mock_market_open.return_value = True

        # Buy 10 shares at €50
        mock_fetch.return_value = {'price': 50.0, 'volume': 1000}
        self.engine.execute_buy(self.model.id, "SAP.DE", 10)

        # Sell 5 shares at €60
        mock_fetch.return_value = {'price': 60.0, 'volume': 1000}
        result = self.engine.execute_sell(self.model.id, "SAP.DE", 5)

        assert result['success'] is True

        # Realized P&L on 5 shares: (60 - 50) * 5 - 5 fee = 45
        assert result['realized_pl'] == 45.0

        # Position should still exist with 5 shares
        position = result['position']
        assert position is not None
        assert position.quantity == 5
        assert abs(position.avg_price - 50.0) < 0.01

    @patch('backend.services.trading_engine.MarketDataService.is_market_open')
    @patch('backend.services.trading_engine.MarketDataService.fetch_price')
    def test_execute_sell_no_position(self, mock_fetch, mock_market_open):
        """Test sell fails with no position."""
        mock_market_open.return_value = True
        mock_fetch.return_value = {'price': 100.0, 'volume': 1000}

        result = self.engine.execute_sell(self.model.id, "SAP.DE", 10)

        assert result['success'] is False
        assert "No position" in result['reason']


class TestPositionManagement:
    """Test position tracking and updates."""

    @pytest.fixture(autouse=True)
    def setup(self, trading_engine, test_model, db_session):
        """Set up test portfolio."""
        self.engine = trading_engine
        self.model = test_model
        self.db = db_session
        self.engine.initialize_portfolio(test_model.id)

    @patch('backend.services.trading_engine.MarketDataService.is_market_open')
    @patch('backend.services.trading_engine.MarketDataService.fetch_price')
    @patch('backend.services.trading_engine.MarketDataService.fetch_multiple_prices')
    def test_update_position_values(self, mock_fetch_multiple, mock_fetch, mock_market_open):
        """Test updating position values with current prices."""
        mock_market_open.return_value = True

        # Buy positions
        # Buy 10x SAP.DE @ €50 = 500 + 5 fee = 505, balance after: 495
        mock_fetch.return_value = {'price': 50.0, 'volume': 1000}
        self.engine.execute_buy(self.model.id, "SAP.DE", 10)

        # Buy 5x BMW.DE @ €80 = 400 + 5 fee = 405, balance after: 90
        mock_fetch.return_value = {'price': 80.0, 'volume': 1000}
        self.engine.execute_buy(self.model.id, "BMW.DE", 5)

        # Update prices
        mock_fetch_multiple.return_value = {
            'SAP.DE': {'price': 60.0, 'volume': 1000},
            'BMW.DE': {'price': 75.0, 'volume': 1000}
        }

        positions = self.engine.update_position_values(self.model.id)

        assert len(positions) == 2

        # Find SAP position
        sap_pos = next(p for p in positions if p.symbol == "SAP.DE")
        assert abs(sap_pos.current_price - 60.0) < 0.01
        assert abs(sap_pos.unrealized_pl - 100.0) < 0.01  # (60 - 50) * 10 = 100

        # Find BMW position
        bmw_pos = next(p for p in positions if p.symbol == "BMW.DE")
        assert abs(bmw_pos.current_price - 75.0) < 0.01
        assert abs(bmw_pos.unrealized_pl - (-25.0)) < 0.01  # (75 - 80) * 5 = -25

    def test_get_positions(self, db_session):
        """Test retrieving all positions."""
        # Create test positions
        pos1 = Position(
            model_id=self.model.id,
            symbol="SAP.DE",
            quantity=10,
            avg_price=Decimal('100.00'),
            current_price=Decimal('100.00'),
            unrealized_pl=Decimal('0.00')
        )
        pos2 = Position(
            model_id=self.model.id,
            symbol="BMW.DE",
            quantity=5,
            avg_price=Decimal('50.00'),
            current_price=Decimal('50.00'),
            unrealized_pl=Decimal('0.00')
        )
        db_session.add_all([pos1, pos2])
        db_session.commit()

        positions = self.engine.get_positions(self.model.id)

        assert len(positions) == 2
        assert {p.symbol for p in positions} == {"SAP.DE", "BMW.DE"}


class TestPortfolioValuation:
    """Test portfolio value calculations."""

    @pytest.fixture(autouse=True)
    def setup(self, trading_engine, test_model, db_session):
        """Set up test portfolio."""
        self.engine = trading_engine
        self.model = test_model
        self.db = db_session
        self.engine.initialize_portfolio(test_model.id)

    @patch('backend.services.trading_engine.MarketDataService.is_market_open')
    @patch('backend.services.trading_engine.MarketDataService.fetch_price')
    def test_calculate_portfolio_value_no_positions(self, mock_fetch, mock_market_open):
        """Test portfolio value with no positions."""
        metrics = self.engine.calculate_portfolio_value(self.model.id)

        assert metrics['cash_balance'] == 1000.0
        assert metrics['positions_value'] == 0.0
        assert metrics['total_value'] == 1000.0
        assert metrics['total_pl'] == 0.0
        assert metrics['num_positions'] == 0

    @patch('backend.services.trading_engine.MarketDataService.is_market_open')
    @patch('backend.services.trading_engine.MarketDataService.fetch_price')
    def test_calculate_portfolio_value_with_positions(self, mock_fetch, mock_market_open):
        """Test portfolio value with open positions."""
        mock_market_open.return_value = True

        # Buy SAP at €100
        mock_fetch.return_value = {'price': 100.0, 'volume': 1000}
        self.engine.execute_buy(self.model.id, "SAP.DE", 5)

        # Manually update position price to simulate market movement
        position = self.db.query(Position).filter(
            Position.model_id == self.model.id,
            Position.symbol == "SAP.DE"
        ).first()
        position.current_price = 120.0
        position.unrealized_pl = (120.0 - position.avg_price) * position.quantity
        self.db.commit()

        metrics = self.engine.calculate_portfolio_value(self.model.id)

        # Cash: 1000 - 505 = 495
        assert abs(metrics['cash_balance'] - 495.0) < 0.01

        # Position value: 120 * 5 = 600
        assert abs(metrics['positions_value'] - 600.0) < 0.01

        # Total: 495 + 600 = 1095
        assert abs(metrics['total_value'] - 1095.0) < 0.01

        # Unrealized P&L: (120 - 100) * 5 = 100
        assert abs(metrics['unrealized_pl'] - 100.0) < 0.01

        # Total P&L: 100 (no realized yet)
        assert abs(metrics['total_pl'] - 100.0) < 0.01

        # P&L %: 100 / 1000 * 100 = 10%
        assert abs(metrics['pl_percentage'] - 10.0) < 0.01

    @patch('backend.services.trading_engine.MarketDataService.is_market_open')
    @patch('backend.services.trading_engine.MarketDataService.fetch_price')
    def test_calculate_portfolio_value_with_realized_pl(self, mock_fetch, mock_market_open):
        """Test portfolio value including realized P&L."""
        mock_market_open.return_value = True

        # Buy and sell for profit
        mock_fetch.return_value = {'price': 50.0, 'volume': 1000}
        self.engine.execute_buy(self.model.id, "SAP.DE", 10)

        mock_fetch.return_value = {'price': 60.0, 'volume': 1000}
        self.engine.execute_sell(self.model.id, "SAP.DE", 10)

        metrics = self.engine.calculate_portfolio_value(self.model.id)

        # Realized P&L: (60 - 50) * 10 - 5 = 95
        assert abs(metrics['realized_pl'] - 95.0) < 0.01
        assert abs(metrics['total_pl'] - 95.0) < 0.01
        assert metrics['num_positions'] == 0


class TestPerformanceMetrics:
    """Test performance metrics calculation."""

    @pytest.fixture(autouse=True)
    def setup(self, trading_engine, test_model, db_session):
        """Set up test portfolio."""
        self.engine = trading_engine
        self.model = test_model
        self.db = db_session
        self.engine.initialize_portfolio(test_model.id)

    @patch('backend.services.trading_engine.MarketDataService.is_market_open')
    @patch('backend.services.trading_engine.MarketDataService.fetch_price')
    def test_get_performance_metrics(self, mock_fetch, mock_market_open):
        """Test comprehensive performance metrics."""
        mock_market_open.return_value = True

        # Execute multiple trades
        # Trade 1: Buy and sell for profit
        mock_fetch.return_value = {'price': 50.0, 'volume': 1000}
        self.engine.execute_buy(self.model.id, "SAP.DE", 10)

        mock_fetch.return_value = {'price': 60.0, 'volume': 1000}
        self.engine.execute_sell(self.model.id, "SAP.DE", 10)

        # Trade 2: Buy and sell for loss
        mock_fetch.return_value = {'price': 100.0, 'volume': 1000}
        self.engine.execute_buy(self.model.id, "BMW.DE", 5)

        mock_fetch.return_value = {'price': 90.0, 'volume': 1000}
        self.engine.execute_sell(self.model.id, "BMW.DE", 5)

        metrics = self.engine.get_performance_metrics(self.model.id)

        # Should have 4 total trades (2 buys, 2 sells)
        assert metrics['total_trades'] == 4
        assert metrics['buy_count'] == 2
        assert metrics['sell_count'] == 2

        # Win rate: 1 winning trade out of 2 closed = 50%
        assert metrics['win_rate'] == 50.0
        assert metrics['winning_trades'] == 1
        assert metrics['losing_trades'] == 1

        # Total fees: 4 trades * €5 = €20
        assert metrics['total_fees_paid'] == 20.0

    def test_get_trades(self, db_session):
        """Test retrieving trade history."""
        # Create test trades
        trade1 = Trade(
            model_id=self.model.id,
            symbol="SAP.DE",
            side=TradeSide.BUY,
            quantity=10,
            price=100.00,
            fee=5.00,
            total=1005.00,
            status=TradeStatus.COMPLETED,
            executed_at=datetime.now()
        )
        trade2 = Trade(
            model_id=self.model.id,
            symbol="BMW.DE",
            side=TradeSide.SELL,
            quantity=5,
            price=50.00,
            fee=5.00,
            total=245.00,
            status=TradeStatus.COMPLETED,
            executed_at=datetime.now()
        )
        db_session.add_all([trade1, trade2])
        db_session.commit()

        trades = self.engine.get_trades(self.model.id)

        assert len(trades) == 2

    def test_get_trades_with_pagination(self, db_session):
        """Test trade history pagination."""
        # Create 5 test trades
        for i in range(5):
            trade = Trade(
                model_id=self.model.id,
                symbol="SAP.DE",
                side=TradeSide.BUY,
                quantity=1,
                price=100.00,
                fee=5.00,
                total=105.00,
                status=TradeStatus.COMPLETED,
                executed_at=datetime.now()
            )
            db_session.add(trade)
        db_session.commit()

        # Get first 3 trades
        trades = self.engine.get_trades(self.model.id, limit=3, offset=0)
        assert len(trades) == 3

        # Get next 2 trades
        trades = self.engine.get_trades(self.model.id, limit=3, offset=3)
        assert len(trades) == 2
