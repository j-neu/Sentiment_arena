from sqlalchemy import Column, Integer, String, Float, DateTime, BigInteger
from sqlalchemy.sql import func
from backend.database.base import Base


class MarketData(Base):
    """Market data cache for stock prices"""
    __tablename__ = "market_data"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    price = Column(Float, nullable=False)
    volume = Column(BigInteger, nullable=True)
    bid = Column(Float, nullable=True)
    ask = Column(Float, nullable=True)
    day_high = Column(Float, nullable=True)
    day_low = Column(Float, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    def __repr__(self):
        return f"<MarketData(symbol='{self.symbol}', price={self.price}, timestamp={self.timestamp})>"
