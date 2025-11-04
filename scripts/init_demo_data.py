"""
Initialize demo data for Sentiment Arena
Creates sample models for testing the frontend
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database.base import SessionLocal
from backend.models.model import Model
from backend.models.portfolio import Portfolio
from backend.logger import get_logger

logger = get_logger(__name__)

def init_demo_data():
    """Initialize demo models and portfolios"""
    db = SessionLocal()

    try:
        # Check if models already exist
        existing = db.query(Model).count()
        if existing > 0:
            logger.info(f"Database already has {existing} models. Skipping initialization.")
            return

        # Demo models - User's preferred models
        demo_models = [
            {
                "name": "Grok Code Fast 1",
                "api_identifier": "x-ai/grok-code-fast-1",
                "starting_balance": 1000.0
            },
            {
                "name": "Claude Sonnet 4.5",
                "api_identifier": "anthropic/claude-4.5-sonnet-20250929",
                "starting_balance": 1000.0
            },
            {
                "name": "Gemini 2.5 Flash",
                "api_identifier": "google/gemini-2.5-flash",
                "starting_balance": 1000.0
            },
            {
                "name": "DeepSeek V3.1",
                "api_identifier": "deepseek/deepseek-chat-v3.1",
                "starting_balance": 1000.0
            },
            {
                "name": "GPT-4o Mini",
                "api_identifier": "openai/gpt-4o-mini",
                "starting_balance": 1000.0
            },
            {
                "name": "GLM 4.6",
                "api_identifier": "z-ai/glm-4.6",
                "starting_balance": 1000.0
            },
            {
                "name": "Qwen3 235B A22B",
                "api_identifier": "qwen/qwen3-235b-a22b",
                "starting_balance": 1000.0
            }
        ]

        logger.info("Creating demo models...")

        for model_data in demo_models:
            # Create model
            model = Model(**model_data)
            db.add(model)
            db.flush()  # Get the model ID

            # Create portfolio
            portfolio = Portfolio(
                model_id=model.id,
                current_balance=model.starting_balance,
                total_pl=0.0,
                total_value=model.starting_balance,
                total_pl_percentage=0.0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0
            )
            db.add(portfolio)

            logger.info(f"Created model: {model.name} (ID: {model.id})")

        db.commit()
        logger.info(f"Successfully created {len(demo_models)} demo models!")
        logger.info("Models created:")
        for model_data in demo_models:
            logger.info(f"  - {model_data['name']}: {model_data['api_identifier']}")

    except Exception as e:
        logger.error(f"Failed to initialize demo data: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    init_demo_data()
