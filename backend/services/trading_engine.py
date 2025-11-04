"""
Trading Engine for Paper Trading Simulation

Handles all trading operations including:
- Portfolio initialization
- Order validation
- Trade execution (buy/sell)
- Position management
- P&L calculations
- Fee handling
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from decimal import Decimal
from sqlalchemy.orm import Session

from backend.models.model import Model
from backend.models.portfolio import Portfolio
from backend.models.position import Position
from backend.models.trade import Trade, TradeSide, TradeStatus
from backend.services.market_data import MarketDataService
from backend.config import settings
from backend.logger import get_logger

logger = get_logger(__name__)


class TradingEngine:
    """
    Paper trading engine for simulating stock trades.

    Handles order validation, execution, position tracking, and P&L calculations.
    Enforces market hours, validates symbols, and applies trading fees.
    """

    def __init__(self, db: Session, market_data_service: MarketDataService):
        """
        Initialize the trading engine.

        Args:
            db: SQLAlchemy database session
            market_data_service: An instance of MarketDataService
        """
        self.db = db
        self.market_data = market_data_service
        self.trading_fee = Decimal(str(settings.TRADING_FEE))

        logger.info(f"TradingEngine initialized with €{self.trading_fee} fee per trade")

    def initialize_portfolio(self, model_id: int) -> Portfolio:
        """
        Initialize a portfolio for a model with starting capital.

        Args:
            model_id: ID of the model

        Returns:
            Created Portfolio object

        Raises:
            ValueError: If model doesn't exist or portfolio already exists
        """
        logger.info(f"Initializing portfolio for model_id={model_id}")

        # Check if model exists
        model = self.db.query(Model).filter(Model.id == model_id).first()
        if not model:
            logger.error(f"Model {model_id} not found")
            raise ValueError(f"Model with id {model_id} does not exist")

        # Check if portfolio already exists
        existing = self.db.query(Portfolio).filter(Portfolio.model_id == model_id).first()
        if existing:
            logger.warning(f"Portfolio for model {model_id} already exists")
            raise ValueError(f"Portfolio for model {model_id} already exists")

        # Create portfolio with starting balance
        portfolio = Portfolio(
            model_id=model_id,
            current_balance=model.starting_balance,
            total_pl=Decimal('0.00'),
            total_value=model.starting_balance
        )

        self.db.add(portfolio)
        self.db.commit()
        self.db.refresh(portfolio)

        logger.info(f"Portfolio created for model {model_id} with €{model.starting_balance}")
        return portfolio

    def get_portfolio(self, model_id: int) -> Optional[Portfolio]:
        """
        Get portfolio for a model.

        Args:
            model_id: ID of the model

        Returns:
            Portfolio object or None if not found
        """
        return self.db.query(Portfolio).filter(Portfolio.model_id == model_id).first()

    def validate_order(
        self,
        model_id: int,
        symbol: str,
        side: str,
        quantity: int
    ) -> Dict[str, Any]:
        """
        Validate an order before execution.

        Args:
            model_id: ID of the model placing the order
            symbol: Stock symbol (must end with .DE)
            side: 'buy' or 'sell'
            quantity: Number of shares

        Returns:
            Dict with 'valid' (bool) and 'reason' (str) keys
        """
        logger.info(f"Validating order: model={model_id}, {side} {quantity}x {symbol}")

        # Validate side
        if side.lower() not in ['buy', 'sell']:
            return {'valid': False, 'reason': f"Invalid side: {side}. Must be 'buy' or 'sell'"}

        # Validate quantity
        if quantity <= 0:
            return {'valid': False, 'reason': f"Invalid quantity: {quantity}. Must be positive"}

        # Validate symbol
        if not self.market_data.validate_symbol(symbol):
            return {'valid': False, 'reason': f"Invalid symbol: {symbol}. Must end with .DE"}

        # Check market hours
        if not self.market_data.is_market_open():
            market_status = self.market_data.get_market_status()
            return {'valid': False, 'reason': f"Market is closed. {market_status['status_message']}"}

        # Get portfolio
        portfolio = self.get_portfolio(model_id)
        if not portfolio:
            return {'valid': False, 'reason': f"Portfolio not found for model {model_id}"}

        # Get current price
        price_data = self.market_data.fetch_price(symbol)
        if not price_data:
            return {'valid': False, 'reason': f"Could not fetch price for {symbol}"}

        current_price = Decimal(str(price_data['price']))

        # Validate buy order
        if side.lower() == 'buy':
            total_cost = (current_price * quantity) + self.trading_fee
            if portfolio.current_balance < total_cost:
                return {
                    'valid': False,
                    'reason': f"Insufficient balance. Need €{total_cost:.2f}, have €{portfolio.current_balance:.2f}"
                }

        # Validate sell order
        elif side.lower() == 'sell':
            position = self.db.query(Position).filter(
                Position.model_id == model_id,
                Position.symbol == symbol
            ).first()

            if not position:
                return {'valid': False, 'reason': f"No position in {symbol} to sell"}

            if position.quantity < quantity:
                return {
                    'valid': False,
                    'reason': f"Insufficient shares. Trying to sell {quantity}, have {position.quantity}"
                }

        logger.info(f"Order validation passed for {side} {quantity}x {symbol}")
        return {'valid': True, 'reason': 'Order is valid', 'price': float(current_price)}

    def execute_buy(
        self,
        model_id: int,
        symbol: str,
        quantity: int
    ) -> Dict[str, Any]:
        """
        Execute a buy order.

        Args:
            model_id: ID of the model
            symbol: Stock symbol
            quantity: Number of shares to buy

        Returns:
            Dict with execution details including 'success', 'trade', 'position'
        """
        logger.info(f"Executing BUY order: model={model_id}, {quantity}x {symbol}")

        # Validate order
        validation = self.validate_order(model_id, symbol, 'buy', quantity)
        if not validation['valid']:
            logger.error(f"Buy order validation failed: {validation['reason']}")
            return {'success': False, 'reason': validation['reason']}

        # Get current price
        price_data = self.market_data.fetch_price(symbol)
        current_price = Decimal(str(price_data['price']))

        # Calculate costs
        cost_before_fee = current_price * quantity
        total_cost = cost_before_fee + self.trading_fee

        # Get portfolio
        portfolio = self.get_portfolio(model_id)

        # Create trade record
        trade = Trade(
            model_id=model_id,
            symbol=symbol,
            side=TradeSide.BUY,
            quantity=quantity,
            price=float(current_price),
            fee=float(self.trading_fee),
            total=float(total_cost),
            status=TradeStatus.COMPLETED,
            executed_at=datetime.now()
        )

        self.db.add(trade)

        # Update portfolio balance (convert Decimal to float for database)
        portfolio.current_balance = float(Decimal(str(portfolio.current_balance)) - total_cost)

        # Update or create position
        position = self.db.query(Position).filter(
            Position.model_id == model_id,
            Position.symbol == symbol
        ).first()

        if position:
            # Add to existing position (calculate new average price)
            old_total_value = Decimal(str(position.avg_price)) * position.quantity
            new_total_value = old_total_value + cost_before_fee
            new_quantity = position.quantity + quantity

            position.avg_price = float(new_total_value / new_quantity)
            position.quantity = new_quantity
            position.current_price = float(current_price)
            position.unrealized_pl = float((current_price - Decimal(str(position.avg_price))) * position.quantity)

            logger.info(f"Added to position: {symbol}, new qty={new_quantity}, new avg=€{position.avg_price:.2f}")
        else:
            # Create new position
            position = Position(
                model_id=model_id,
                symbol=symbol,
                quantity=quantity,
                avg_price=float(current_price),
                current_price=float(current_price),
                unrealized_pl=0.00,
                opened_at=datetime.now()
            )
            self.db.add(position)
            logger.info(f"Opened new position: {quantity}x {symbol} @ €{current_price:.2f}")

        # Update total portfolio value
        self._update_portfolio_value(model_id)

        # Commit transaction
        self.db.commit()
        self.db.refresh(trade)
        self.db.refresh(position)

        logger.info(f"Buy order executed: {quantity}x {symbol} @ €{current_price:.2f}, fee=€{self.trading_fee}")

        return {
            'success': True,
            'trade': trade,
            'position': position,
            'execution_price': float(current_price),
            'total_cost': float(total_cost)
        }

    def execute_sell(
        self,
        model_id: int,
        symbol: str,
        quantity: int
    ) -> Dict[str, Any]:
        """
        Execute a sell order.

        Args:
            model_id: ID of the model
            symbol: Stock symbol
            quantity: Number of shares to sell

        Returns:
            Dict with execution details including 'success', 'trade', 'position', 'realized_pl'
        """
        logger.info(f"Executing SELL order: model={model_id}, {quantity}x {symbol}")

        # Validate order
        validation = self.validate_order(model_id, symbol, 'sell', quantity)
        if not validation['valid']:
            logger.error(f"Sell order validation failed: {validation['reason']}")
            return {'success': False, 'reason': validation['reason']}

        # Get current price
        price_data = self.market_data.fetch_price(symbol)
        current_price = Decimal(str(price_data['price']))

        # Calculate proceeds
        proceeds_before_fee = current_price * quantity
        total_proceeds = proceeds_before_fee - self.trading_fee

        # Get portfolio and position
        portfolio = self.get_portfolio(model_id)
        position = self.db.query(Position).filter(
            Position.model_id == model_id,
            Position.symbol == symbol
        ).first()

        # Calculate realized P&L
        avg_price_decimal = Decimal(str(position.avg_price))
        realized_pl = (current_price - avg_price_decimal) * quantity - self.trading_fee

        # Create trade record
        trade = Trade(
            model_id=model_id,
            symbol=symbol,
            side=TradeSide.SELL,
            quantity=quantity,
            price=float(current_price),
            fee=float(self.trading_fee),
            total=float(total_proceeds),
            realized_pl=float(realized_pl),
            status=TradeStatus.COMPLETED,
            executed_at=datetime.now()
        )

        self.db.add(trade)

        # Update portfolio balance
        portfolio.current_balance = float(Decimal(str(portfolio.current_balance)) + total_proceeds)
        portfolio.total_pl = float(Decimal(str(portfolio.total_pl)) + realized_pl)

        # Update or close position
        if position.quantity == quantity:
            # Close entire position
            logger.info(f"Closing full position: {symbol}, realized P&L=€{realized_pl:.2f}")
            self.db.delete(position)
            position = None
        else:
            # Partial close
            position.quantity -= quantity
            position.unrealized_pl = float((current_price - Decimal(str(position.avg_price))) * position.quantity)
            logger.info(f"Partial close: {symbol}, sold {quantity}, remaining {position.quantity}")

        # Update total portfolio value
        self._update_portfolio_value(model_id)

        # Commit transaction
        self.db.commit()
        self.db.refresh(trade)
        if position:
            self.db.refresh(position)

        logger.info(f"Sell order executed: {quantity}x {symbol} @ €{current_price:.2f}, realized P&L=€{realized_pl:.2f}")

        return {
            'success': True,
            'trade': trade,
            'position': position,
            'execution_price': float(current_price),
            'total_proceeds': float(total_proceeds),
            'realized_pl': float(realized_pl)
        }

    def update_position_values(self, model_id: int) -> List[Position]:
        """
        Update current prices and unrealized P&L for all positions.

        Args:
            model_id: ID of the model

        Returns:
            List of updated positions
        """
        logger.info(f"Updating position values for model {model_id}")

        positions = self.db.query(Position).filter(Position.model_id == model_id).all()

        if not positions:
            logger.info(f"No positions found for model {model_id}")
            return []

        # Get all symbols
        symbols = [pos.symbol for pos in positions]

        # Fetch current prices
        prices = self.market_data.fetch_multiple_prices(symbols)

        # Update each position
        updated_count = 0
        for position in positions:
            price_data = prices.get(position.symbol)
            if price_data:
                current_price = Decimal(str(price_data['price']))
                position.current_price = float(current_price)
                position.unrealized_pl = float((current_price - Decimal(str(position.avg_price))) * position.quantity)
                updated_count += 1

        # Update portfolio total value
        self._update_portfolio_value(model_id)

        self.db.commit()

        logger.info(f"Updated {updated_count}/{len(positions)} positions for model {model_id}")
        return positions

    def calculate_portfolio_value(self, model_id: int) -> Dict[str, Any]:
        """
        Calculate total portfolio value (cash + positions).

        Args:
            model_id: ID of the model

        Returns:
            Dict with portfolio metrics
        """
        portfolio = self.get_portfolio(model_id)
        if not portfolio:
            logger.warning(f"Portfolio not found for model {model_id}")
            return None

        positions = self.db.query(Position).filter(Position.model_id == model_id).all()

        # Calculate total position value
        positions_value = Decimal('0.00')
        total_unrealized_pl = Decimal('0.00')

        for position in positions:
            position_value = Decimal(str(position.current_price)) * position.quantity
            positions_value += position_value
            total_unrealized_pl += Decimal(str(position.unrealized_pl))

        total_value = Decimal(str(portfolio.current_balance)) + positions_value

        # Get starting balance
        model = self.db.query(Model).filter(Model.id == model_id).first()
        starting_balance = Decimal(str(model.starting_balance))

        # Total P&L = realized + unrealized
        total_pl = Decimal(str(portfolio.total_pl)) + total_unrealized_pl
        pl_percentage = (total_pl / starting_balance * 100) if starting_balance > 0 else Decimal('0.00')

        return {
            'cash_balance': float(portfolio.current_balance),
            'positions_value': float(positions_value),
            'total_value': float(total_value),
            'realized_pl': float(portfolio.total_pl),
            'unrealized_pl': float(total_unrealized_pl),
            'total_pl': float(total_pl),
            'pl_percentage': float(pl_percentage),
            'starting_balance': float(starting_balance),
            'num_positions': len(positions)
        }

    def _update_portfolio_value(self, model_id: int) -> None:
        """
        Internal method to update portfolio total_value field.

        Args:
            model_id: ID of the model
        """
        metrics = self.calculate_portfolio_value(model_id)
        if metrics:
            portfolio = self.get_portfolio(model_id)
            portfolio.total_value = float(metrics['total_value'])
            logger.debug(f"Portfolio value updated to €{portfolio.total_value:.2f}")

    def get_positions(self, model_id: int) -> List[Position]:
        """
        Get all open positions for a model.

        Args:
            model_id: ID of the model

        Returns:
            List of Position objects
        """
        return self.db.query(Position).filter(Position.model_id == model_id).all()

    def get_trades(
        self,
        model_id: int,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Trade]:
        """
        Get trade history for a model.

        Args:
            model_id: ID of the model
            limit: Maximum number of trades to return
            offset: Number of trades to skip

        Returns:
            List of Trade objects
        """
        query = self.db.query(Trade).filter(Trade.model_id == model_id).order_by(Trade.executed_at.desc())

        if limit:
            query = query.limit(limit).offset(offset)

        return query.all()

    def get_performance_metrics(self, model_id: int) -> Dict[str, Any]:
        """
        Calculate comprehensive performance metrics for a model.

        Args:
            model_id: ID of the model

        Returns:
            Dict with performance metrics
        """
        portfolio_metrics = self.calculate_portfolio_value(model_id)
        if not portfolio_metrics:
            return None

        # Get all trades
        trades = self.get_trades(model_id)

        # Calculate win rate
        closed_trades = [t for t in trades if t.side == TradeSide.SELL and t.realized_pl is not None]
        winning_trades = [t for t in closed_trades if t.realized_pl > 0]

        win_rate = (len(winning_trades) / len(closed_trades) * 100) if closed_trades else 0.0

        # Get buy and sell counts
        buy_count = len([t for t in trades if t.side == TradeSide.BUY])
        sell_count = len([t for t in trades if t.side == TradeSide.SELL])

        # Calculate total fees paid
        total_fees = sum(t.fee for t in trades)

        return {
            **portfolio_metrics,
            'total_trades': len(trades),
            'buy_count': buy_count,
            'sell_count': sell_count,
            'win_rate': win_rate,
            'winning_trades': len(winning_trades),
            'losing_trades': len(closed_trades) - len(winning_trades),
            'total_fees_paid': float(total_fees)
        }
