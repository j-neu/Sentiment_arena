"""
Example script demonstrating custom prompt templates.

This shows how to use different trading strategies by loading different prompt templates.
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database.base import SessionLocal, engine, Base
from backend.models.model import Model
from backend.services.llm_agent import LLMAgent
from backend.logger import get_logger

logger = get_logger(__name__)


def main():
    """Main example function."""
    print("=" * 80)
    print("  Custom Prompt Template Demo")
    print("=" * 80)

    # Create database tables
    Base.metadata.create_all(bind=engine)

    # Create database session
    db = SessionLocal()

    try:
        # Create or get model
        model = db.query(Model).filter(Model.api_identifier == "openai/gpt-4-turbo").first()
        if not model:
            model = Model(
                name="GPT-4 Turbo",
                api_identifier="openai/gpt-4-turbo",
                starting_balance=1000.0
            )
            db.add(model)
            db.commit()
            db.refresh(model)

        print(f"\nUsing model: {model.name}\n")

        # Example 1: Default prompt
        print("-" * 80)
        print("Example 1: Default Trading Prompt")
        print("-" * 80)

        agent_default = LLMAgent(db, model_id=model.id)
        print(f"[OK] Loaded default prompt from: {agent_default.DEFAULT_PROMPT_PATH}")
        print(f"     Prompt length: {len(agent_default.prompt_template)} characters")
        print(f"     Strategy: Balanced swing trading")

        # Show first 200 chars of prompt
        print(f"\nPrompt preview:")
        print(agent_default.prompt_template[:200] + "...")

        agent_default.close()

        # Example 2: Conservative prompt
        print("\n" + "-" * 80)
        print("Example 2: Conservative Trading Prompt")
        print("-" * 80)

        conservative_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "backend",
            "prompts",
            "conservative_prompt.txt"
        )

        agent_conservative = LLMAgent(db, model_id=model.id, prompt_path=conservative_path)
        print(f"[OK] Loaded conservative prompt from: {conservative_path}")
        print(f"     Prompt length: {len(agent_conservative.prompt_template)} characters")
        print(f"     Strategy: Risk-averse, capital preservation")

        # Show first 200 chars of prompt
        print(f"\nPrompt preview:")
        print(agent_conservative.prompt_template[:200] + "...")

        agent_conservative.close()

        # Example 3: Compare prompts
        print("\n" + "-" * 80)
        print("Example 3: Prompt Comparison")
        print("-" * 80)

        # Count differences
        default_has_conservative = "conservative" in agent_default.prompt_template.lower()
        conservative_has_conservative = "conservative" in agent_conservative.prompt_template.lower()

        print(f"\nDefault prompt mentions 'conservative': {default_has_conservative}")
        print(f"Conservative prompt mentions 'conservative': {conservative_has_conservative}")

        print(f"\nDefault prompt mentions 'risk': {'risk' in agent_default.prompt_template.lower()}")
        print(f"Conservative prompt mentions 'risk': {'risk' in agent_conservative.prompt_template.lower()}")

        # Example 4: Create custom prompt on the fly
        print("\n" + "-" * 80)
        print("Example 4: Creating a Custom Prompt")
        print("-" * 80)

        custom_prompt = """You are testing a custom prompt.
Portfolio: {model_name}
Balance: EUR {current_balance:.2f}

This is a minimal prompt for testing.

Respond with JSON:
{{
    "action": "HOLD",
    "reasoning": "Custom prompt test",
    "confidence": "LOW"
}}
"""

        # Save custom prompt
        custom_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "backend",
            "prompts",
            "custom_test.txt"
        )

        with open(custom_path, 'w') as f:
            f.write(custom_prompt)

        print(f"[OK] Created custom prompt at: {custom_path}")

        # Load agent with custom prompt
        agent_custom = LLMAgent(db, model_id=model.id, prompt_path=custom_path)
        print(f"[OK] Loaded custom prompt")
        print(f"     Prompt length: {len(agent_custom.prompt_template)} characters")

        print(f"\nFull custom prompt:")
        print(agent_custom.prompt_template)

        agent_custom.close()

        # Clean up test file
        os.remove(custom_path)
        print(f"\n[OK] Cleaned up test file")

        # Summary
        print("\n" + "=" * 80)
        print("  Summary: How to Use Custom Prompts")
        print("=" * 80)
        print("""
1. Create a .txt file in backend/prompts/ with your prompt template
2. Use template variables like {model_name}, {current_balance}, etc.
3. Load the agent with prompt_path parameter:

   agent = LLMAgent(
       db,
       model_id=1,
       prompt_path="backend/prompts/my_custom_prompt.txt"
   )

4. Available prompts:
   - trading_prompt.txt (default) - Balanced swing trading
   - conservative_prompt.txt - Risk-averse, capital preservation
   - [create your own!]

5. Template variables available:
   - {model_name}
   - {current_balance}
   - {total_value}
   - {total_pl}
   - {pl_percentage}
   - {num_positions}
   - {positions_info}
   - {market_data}
   - {research_content}
        """)

    except Exception as e:
        logger.error(f"Error in demo: {e}", exc_info=True)
        print(f"\n[ERROR] {e}")

    finally:
        db.close()
        print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
