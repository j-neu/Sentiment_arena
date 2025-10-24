from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database.base import Base


class Reasoning(Base):
    """Model decision-making reasoning and research"""
    __tablename__ = "reasoning"

    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, ForeignKey("models.id", ondelete="CASCADE"), nullable=False, index=True)
    research_content = Column(Text, nullable=True)  # Research findings from internet searches
    decision = Column(String(50), nullable=True)  # Summary of decision (e.g., "BUY 10 BMW.DE", "HOLD")
    reasoning_text = Column(Text, nullable=False)  # Model's reasoning/thoughts
    raw_response = Column(JSON, nullable=True)  # Raw JSON response from LLM
    session_type = Column(String(50), nullable=True)  # "pre_market" or "afternoon"
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    model = relationship("Model", back_populates="reasoning_entries")

    def __repr__(self):
        return f"<Reasoning(id={self.id}, model_id={self.model_id}, decision='{self.decision}', created_at={self.created_at})>"
