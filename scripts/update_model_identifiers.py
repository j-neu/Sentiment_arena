"""
Update Model Identifiers - Fix incorrect OpenRouter model IDs in database

This script updates the api_identifier column in the models table to use
the correct OpenRouter model identifiers discovered during testing.

Fixes:
- anthropic/claude-sonnet-4-5 → anthropic/claude-4.5-sonnet-20250929
- deepseek/deepseek-v3.1 → deepseek/deepseek-chat-v3.1
- zhipuai/glm-4.6 → z-ai/glm-4.6
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database.base import SessionLocal
from backend.models.model import Model
from backend.logger import get_logger

logger = get_logger(__name__)

# Mapping of old identifiers to new identifiers
MODEL_IDENTIFIER_UPDATES = {
    "anthropic/claude-sonnet-4-5": "anthropic/claude-4.5-sonnet-20250929",
    "deepseek/deepseek-v3.1": "deepseek/deepseek-chat-v3.1",
    "zhipuai/glm-4.6": "z-ai/glm-4.6",
}


def update_model_identifiers():
    """Update model identifiers in the database"""
    db = SessionLocal()
    updated_count = 0

    try:
        logger.info("Starting model identifier update...")
        logger.info(f"Will update {len(MODEL_IDENTIFIER_UPDATES)} identifiers")

        for old_id, new_id in MODEL_IDENTIFIER_UPDATES.items():
            # Find models with old identifier
            models = db.query(Model).filter(Model.api_identifier == old_id).all()

            if models:
                logger.info(f"\nFound {len(models)} model(s) with identifier: {old_id}")
                for model in models:
                    logger.info(f"  - Model ID {model.id}: {model.name}")
                    model.api_identifier = new_id
                    updated_count += 1
                    logger.info(f"    Updated to: {new_id}")
            else:
                logger.info(f"\nNo models found with identifier: {old_id}")

        if updated_count > 0:
            db.commit()
            logger.info(f"\n{'='*60}")
            logger.info(f"✓ Successfully updated {updated_count} model(s)")
            logger.info(f"{'='*60}")
            logger.info("\nUpdated identifiers:")
            for old_id, new_id in MODEL_IDENTIFIER_UPDATES.items():
                logger.info(f"  • {old_id}")
                logger.info(f"    → {new_id}")
        else:
            logger.info("\nNo models needed updating. Database is already up to date!")

        # Show current state
        logger.info(f"\n{'='*60}")
        logger.info("Current models in database:")
        logger.info(f"{'='*60}")
        all_models = db.query(Model).all()
        for model in all_models:
            logger.info(f"  ID {model.id}: {model.name}")
            logger.info(f"    → {model.api_identifier}")

    except Exception as e:
        logger.error(f"Failed to update model identifiers: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  Model Identifier Update Script")
    print("="*60)
    print("\nThis will update incorrect OpenRouter model identifiers")
    print("in the database to match the current OpenRouter API.\n")
    print("Changes:")
    for old, new in MODEL_IDENTIFIER_UPDATES.items():
        print(f"  • {old}")
        print(f"    → {new}")

    response = input("\nContinue? (yes/no): ")

    if response.lower() in ['yes', 'y']:
        update_model_identifiers()
        print("\n" + "="*60)
        print("  Update complete!")
        print("="*60)
        print("\nPlease restart the backend server for changes to take effect.")
    else:
        print("\nOperation cancelled.")
