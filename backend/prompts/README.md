# Trading Prompt Templates

This directory contains prompt templates used by LLM agents for trading decisions.

## Files

### `trading_prompt.txt`
The main trading prompt template used by the LLM agent to make autonomous trading decisions.

**Template Variables:**
- `{model_name}` - Name of the LLM model
- `{current_balance}` - Current cash balance in euros
- `{total_value}` - Total portfolio value (cash + positions)
- `{total_pl}` - Total profit/loss in euros
- `{pl_percentage}` - P&L as percentage of starting capital
- `{num_positions}` - Number of open positions
- `{positions_info}` - Formatted list of current positions
- `{market_data}` - Current market prices and data
- `{research_content}` - Research findings and news

**Expected Output:**
JSON object with:
- `action`: "BUY" | "SELL" | "HOLD"
- `symbol`: Stock symbol (for BUY/SELL)
- `quantity`: Number of shares (for BUY/SELL)
- `reasoning`: Detailed explanation
- `confidence`: "HIGH" | "MEDIUM" | "LOW"
- `market_outlook`: Market assessment
- `risk_assessment`: Risk analysis

## Usage

Prompts are loaded by the `LLMAgent` class at initialization:

```python
from backend.services.llm_agent import LLMAgent

agent = LLMAgent(db, model_id=1)
# Agent automatically loads trading_prompt.txt
```

## Customization

To customize the trading prompt:

1. Edit `trading_prompt.txt` directly
2. Keep all template variables (`{variable_name}`) intact
3. Maintain the JSON output format specification
4. Test changes with `python examples/test_llm_agent.py`

## Version Control

- All prompt changes should be committed to version control
- Document significant changes in commit messages
- Consider A/B testing before deploying major prompt changes

## Tips for Prompt Engineering

1. **Be Specific**: Clearly define what you want the LLM to do
2. **Provide Context**: Include all relevant information (portfolio, market data, news)
3. **Define Constraints**: Specify trading rules and limitations
4. **Format Output**: Clearly specify the expected JSON structure
5. **Examples**: Consider adding few-shot examples for complex decisions
6. **Iteration**: Test and refine based on agent performance

## Future Templates

You can create additional prompts for different strategies:
- `conservative_prompt.txt` - Risk-averse trading
- `aggressive_prompt.txt` - Higher risk/reward
- `day_trading_prompt.txt` - Intraday trading strategy
- `research_only_prompt.txt` - Analysis without execution
