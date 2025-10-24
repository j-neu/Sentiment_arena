from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database.base import Base


class Position(Base):
    """Open position for a model"""
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, ForeignKey("models.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)  # Stock symbol (e.g., BMW.DE)
    quantity = Column(Integer, nullable=False)
    avg_price = Column(Float, nullable=False)  # Average purchase price
    current_price = Column(Float, nullable=True)  # Latest market price
    unrealized_pl = Column(Float, nullable=False, default=0.0)  # Unrealized P&L in euros
    unrealized_pl_percentage = Column(Float, nullable=False, default=0.0)  # Unrealized P&L as percentage
    opened_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    model = relationship("Model", back_populates="positions")

    @property
    def position_value(self) -> float:
        """Calculate current position value"""
        if self.current_price:
            return self.quantity * self.current_price
        return self.quantity * self.avg_price

    @property
    def cost_basis(self) -> float:
        """Calculate cost basis (total amount paid)"""
        return self.quantity * self.avg_price

    def update_pl(self, current_price: float):
        """Update unrealized P&L based on current price"""
        self.current_price = current_price
        self.unrealized_pl = (current_price - self.avg_price) * self.quantity
        if self.avg_price > 0:
            self.unrealized_pl_percentage = ((current_price - self.avg_price) / self.avg_price) * 100

    def __repr__(self):
        return f"<Position(model_id={self.model_id}, symbol='{self.symbol}', qty={self.quantity}, avg_price={self.avg_price})>"
