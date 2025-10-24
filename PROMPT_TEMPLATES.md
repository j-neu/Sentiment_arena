# Trading Prompt Templates Guide

## Overview

The LLM Agent system now supports **externalized prompt templates**, allowing you to easily customize trading strategies without modifying code.

## Location

All prompt templates are stored in:
```
backend/prompts/
```

## Available Templates

### 1. **trading_prompt.txt** (Default)
**Strategy:** Balanced swing trading for maximum returns

**Characteristics:**
- Moderate risk tolerance
- Aims to maximize returns
- Holds positions for multiple days
- No specific position size limits
- Considers both technical and fundamental factors

**Use when:** You want standard autonomous trading behavior

---

### 2. **conservative_prompt.txt**
**Strategy:** Risk-averse, capital preservation focused

**Characteristics:**
- High risk aversion
- Capital preservation is the priority
- Maximum 20% position size per stock
- Only trades blue-chip, established companies
- Mental stop-loss at -5% per position
- Takes profits at +10% per position
- Defaults to HOLD when uncertain
- Only buys with HIGH confidence

**Use when:** You want to minimize losses and protect capital

---

## Using Custom Prompts

### Option 1: Use an Existing Template

```python
from backend.services.llm_agent import LLMAgent
from backend.database.base import SessionLocal

db = SessionLocal()

# Use conservative strategy
agent = LLMAgent(
    db,
    model_id=1,
    prompt_path="backend/prompts/conservative_prompt.txt"
)

# Make trading decision
result = agent.make_trading_decision(perform_research=True)
```

### Option 2: Create Your Own Template

1. **Create a new .txt file** in `backend/prompts/`
   ```
   backend/prompts/my_strategy.txt
   ```

2. **Write your prompt** using template variables:
   ```
   You are an AI trading agent...

   Current Balance: €{current_balance:.2f}
   Total P&L: €{total_pl:.2f}

   [Your custom instructions here]

   Respond with JSON:
   {{
       "action": "BUY" | "SELL" | "HOLD",
       "symbol": "SYMBOL.DE",
       "quantity": number,
       "reasoning": "...",
       "confidence": "HIGH" | "MEDIUM" | "LOW"
   }}
   ```

3. **Load your custom prompt:**
   ```python
   agent = LLMAgent(
       db,
       model_id=1,
       prompt_path="backend/prompts/my_strategy.txt"
   )
   ```

## Template Variables

All prompts have access to these variables:

| Variable | Type | Description |
|----------|------|-------------|
| `{model_name}` | str | Name of the LLM model |
| `{current_balance}` | float | Current cash balance in euros |
| `{total_value}` | float | Total portfolio value (cash + positions) |
| `{total_pl}` | float | Total profit/loss in euros |
| `{pl_percentage}` | float | P&L as percentage of starting capital |
| `{num_positions}` | int | Number of open positions |
| `{positions_info}` | str | Formatted list of current positions |
| `{market_data}` | str | Current market prices and data |
| `{research_content}` | str | Research findings and news |

### Position Info Format
```
- SAP.DE: 10 shares @ €120.50 avg (Current: €125.30, P&L: €48.00 / 3.98%)
- BMW.DE: 5 shares @ €95.20 avg (Current: €92.80, P&L: €-12.00 / -2.52%)
```

### Market Data Format
```
- SAP.DE: €125.30 (High: €127.50, Low: €124.00, Volume: 1,234,567)
- BMW.DE: €92.80 (High: €94.20, Low: €92.50, Volume: 987,654)
```

## Required JSON Output Format

Your prompt **must** instruct the LLM to return this JSON structure:

```json
{
    "action": "BUY" | "SELL" | "HOLD",
    "symbol": "SYMBOL.DE",          // Required for BUY/SELL
    "quantity": 10,                  // Required for BUY/SELL
    "reasoning": "Detailed explanation of the decision",
    "confidence": "HIGH" | "MEDIUM" | "LOW",
    "market_outlook": "Assessment of market conditions",
    "risk_assessment": "Risk analysis for this trade"
}
```

## Best Practices

### 1. Be Specific and Clear
```
❌ Bad: "Trade carefully"
✅ Good: "Only buy blue-chip stocks with market cap > €10B"
```

### 2. Define Risk Parameters
```
❌ Bad: "Don't take too much risk"
✅ Good: "Maximum position size: 15% of portfolio. Stop-loss at -3%."
```

### 3. Set Confidence Thresholds
```
❌ Bad: "Be confident in your trades"
✅ Good: "Only execute BUY orders with HIGH confidence. HOLD on MEDIUM or LOW."
```

### 4. Provide Context
```
✅ Include portfolio state, positions, market data, and research
✅ Explain the trading strategy and goals
✅ Define constraints and rules
```

### 5. Specify Output Format
```
✅ Clearly define the expected JSON structure
✅ Explain when to include optional fields
✅ Emphasize "respond with ONLY the JSON object"
```

## Example: Day Trading Prompt

Here's an example template for a different strategy:

```txt
You are an AI DAY TRADING agent for German stocks (XETRA/DAX).

STRATEGY: Close all positions by end of day. No overnight holdings.

=== CURRENT PORTFOLIO ===
Balance: €{current_balance:.2f}
Total P&L: €{total_pl:.2f} ({pl_percentage:.2f}%)
Positions: {num_positions}

{positions_info}
{market_data}
{research_content}

=== DAY TRADING RULES ===
- Close ALL positions before 5:00 PM CET (30 min before market close)
- Maximum position hold time: 4 hours
- Target: +2% profit per trade
- Stop-loss: -1% per trade
- Maximum 3 positions at once
- €5 fee per trade

=== DECISION CRITERIA ===
Morning (9:00-12:00):
  - Look for stocks with positive momentum
  - Buy on breakouts above resistance

Afternoon (12:00-17:00):
  - Start closing positions after 3:00 PM
  - Close ALL positions by 4:50 PM
  - Take profits when available

=== OUTPUT ===
Respond with JSON:
{{
    "action": "BUY" | "SELL" | "HOLD",
    "symbol": "SYMBOL.DE",
    "quantity": number,
    "reasoning": "Your analysis including time of day considerations",
    "confidence": "HIGH" | "MEDIUM" | "LOW",
    "time_sensitivity": "How urgently this trade should be executed"
}}

IMPORTANT: If it's after 4:30 PM and you have open positions, you MUST sell them!
```

## Testing Your Prompts

1. **Create a test script:**
   ```python
   from backend.services.llm_agent import LLMAgent
   from backend.database.base import SessionLocal

   db = SessionLocal()
   agent = LLMAgent(db, model_id=1, prompt_path="backend/prompts/your_prompt.txt")

   # Make a decision (with mocked research for testing)
   result = agent.make_trading_decision(perform_research=False)

   print(result["decision"])
   ```

2. **Run the custom prompt example:**
   ```bash
   python examples/custom_prompt_example.py
   ```

3. **Check the logs** for any errors or warnings

## Troubleshooting

### Error: "Prompt template file not found"
- Check the file path is correct
- Ensure the file exists in `backend/prompts/`
- Use absolute path or relative from project root

### Error: "Invalid JSON response"
- Ensure your prompt clearly specifies JSON-only output
- Add "Respond with ONLY the JSON object, no additional text"
- Check the LLM is using proper JSON syntax in examples

### LLM always returns HOLD
- Your prompt may be too conservative
- Check confidence thresholds aren't too strict
- Ensure market conditions are included in the prompt

### Positions not being closed
- Verify sell conditions are clearly defined
- Check position tracking is working correctly
- Ensure LLM has access to current positions via `{positions_info}`

## Advanced: Multiple Strategies per Model

You can run the same model with different strategies:

```python
# Conservative agent for Model 1
conservative_agent = LLMAgent(
    db,
    model_id=1,
    prompt_path="backend/prompts/conservative_prompt.txt"
)

# Aggressive agent for Model 2
aggressive_agent = LLMAgent(
    db,
    model_id=2,
    prompt_path="backend/prompts/aggressive_prompt.txt"
)

# Compare their decisions
conservative_decision = conservative_agent.make_trading_decision()
aggressive_decision = aggressive_agent.make_trading_decision()
```

## Version Control

- **Always commit prompt changes** to version control
- **Document significant changes** in commit messages
- **Consider A/B testing** before deploying major changes
- **Keep backups** of working prompts

## See Also

- `backend/prompts/README.md` - Detailed prompt documentation
- `examples/custom_prompt_example.py` - Interactive demo
- `PHASE_3_COMPLETE.md` - Full Phase 3 documentation

---

**Last Updated:** 2025-10-22
**Phase:** 3 (LLM Agent System)
