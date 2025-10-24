"""Database initialization script"""
from sqlalchemy.orm import Session
from backend.database.base import engine, Base, SessionLocal
from backend.models import Model, Portfolio
from backend.config import settings
from backend.logger import logger


def init_database():
    """Initialize database tables"""
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")


def create_initial_models(db: Session):
    """Create initial model entries for active LLM models"""
    logger.info("Initializing LLM models...")

    for model_identifier in settings.active_models_list:
        # Check if model already exists
        existing_model = db.query(Model).filter(Model.api_identifier == model_identifier).first()

        if not existing_model:
            # Extract a friendly name from the identifier
            model_name = model_identifier.split("/")[-1] if "/" in model_identifier else model_identifier

            # Create model entry
            model = Model(
                name=model_name,
                api_identifier=model_identifier,
                starting_balance=settings.STARTING_CAPITAL
            )
            db.add(model)
            db.flush()  # Get the model ID

            # Create portfolio for the model
            portfolio = Portfolio(
                model_id=model.id,
                current_balance=settings.STARTING_CAPITAL,
                total_pl=0.0,
                total_pl_percentage=0.0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0
            )
            db.add(portfolio)

            logger.info(f"Created model: {model_name} ({model_identifier})")
        else:
            logger.info(f"Model already exists: {existing_model.name} ({model_identifier})")

    db.commit()
    logger.info("Model initialization complete")


def reset_database():
    """Drop and recreate all tables (use with caution!)"""
    logger.warning("Dropping all database tables...")
    Base.metadata.drop_all(bind=engine)
    logger.info("All tables dropped")
    init_database()


if __name__ == "__main__":
    # Initialize database
    init_database()

    # Create initial models
    db = SessionLocal()
    try:
        create_initial_models(db)
    finally:
        db.close()

    logger.info("Database initialization complete!")
