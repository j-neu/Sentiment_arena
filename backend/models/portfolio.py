from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database.base import Base


class Portfolio(Base):
    """Portfolio state for each model"""
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, ForeignKey("models.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    current_balance = Column(Float, nullable=False, default=1000.0)  # Cash available
    total_value = Column(Float, nullable=False, default=1000.0)  # Total portfolio value (cash + positions)
    total_pl = Column(Float, nullable=False, default=0.0)  # Total profit/loss in euros
    total_pl_percentage = Column(Float, nullable=False, default=0.0)  # Total P&L as percentage
    total_trades = Column(Integer, nullable=False, default=0)
    winning_trades = Column(Integer, nullable=False, default=0)
    losing_trades = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    model = relationship("Model", back_populates="portfolio")

    @property
    def win_rate(self) -> float:
        """Calculate win rate percentage"""
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100

    def __repr__(self):
        return f"<Portfolio(model_id={self.model_id}, balance={self.current_balance}, total_pl={self.total_pl})>"
