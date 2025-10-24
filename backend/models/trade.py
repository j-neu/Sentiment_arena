from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database.base import Base
import enum


class TradeSide(str, enum.Enum):
    """Trade side enumeration"""
    BUY = "BUY"
    SELL = "SELL"


class TradeStatus(str, enum.Enum):
    """Trade status enumeration"""
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Trade(Base):
    """Trade execution record"""
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, ForeignKey("models.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(Enum(TradeSide), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)  # Execution price
    fee = Column(Float, nullable=False, default=5.0)  # Trading fee in euros
    total = Column(Float, nullable=False)  # Total amount (price * quantity + fee for buy, price * quantity - fee for sell)
    realized_pl = Column(Float, nullable=True)  # Realized P&L for sell orders
    status = Column(Enum(TradeStatus), nullable=False, default=TradeStatus.PENDING)
    error_message = Column(String(500), nullable=True)
    executed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    model = relationship("Model", back_populates="trades")

    @property
    def net_amount(self) -> float:
        """Calculate net amount (excluding fees)"""
        return self.price * self.quantity

    def __repr__(self):
        return f"<Trade(id={self.id}, model_id={self.model_id}, {self.side} {self.quantity} {self.symbol} @ {self.price})>"
