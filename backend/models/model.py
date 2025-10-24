from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database.base import Base


class Model(Base):
    """LLM model competing in the trading arena"""
    __tablename__ = "models"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    api_identifier = Column(String(200), nullable=False)  # OpenRouter model identifier
    starting_balance = Column(Float, nullable=False, default=1000.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    portfolio = relationship("Portfolio", back_populates="model", uselist=False, cascade="all, delete-orphan")
    positions = relationship("Position", back_populates="model", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="model", cascade="all, delete-orphan")
    reasoning_entries = relationship("Reasoning", back_populates="model", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Model(id={self.id}, name='{self.name}', api_identifier='{self.api_identifier}')>"
