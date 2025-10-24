"""
Enhanced Research Pipeline Demo

Demonstrates the multi-stage research pipeline with:
- Intelligent query generation
- Research synthesis
- Source credibility assessment
- Quality verification
- Cost-effective model usage (cheaper model from same company)
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.config import settings
from backend.services.openrouter_client import OpenRouterClient
from backend.services.enhanced_research import EnhancedResearchPipeline
from backend.services.research_model_mapper import ResearchModelMapper


def print_header(text):
    """Print formatted header."""
    print("\n" + "=" * 70)
    print(f" {text}")
    print("=" * 70 + "\n")


def print_section(text):
    """Print formatted section."""
    print("\n" + "-" * 70)
    print(f" {text}")
    print("-" * 70 + "\n")


def demo_model_mapping():
    """Demonstrate research model mapping."""
    print_header("RESEARCH MODEL MAPPING DEMO")

    test_models = [
        "openai/gpt-4-turbo",
        "anthropic/claude-3-opus-20240229",
        "google/gemini-pro",
        "deepseek/deepseek-chat",
        "openai/gpt-3.5-turbo"
    ]

    print("Trading Model → Research Model Mappings:\n")

    for model in test_models:
        research_model = ResearchModelMapper.get_research_model(model)
        company = ResearchModelMapper.get_model_company(model)
        is_cheap = ResearchModelMapper.is_cheap_model(model)
        cost_info = ResearchModelMapper.get_cost_estimate(model)

        print(f"Trading:  {model}")
        print(f"Research: {research_model}")
        print(f"Company:  {company}")
        print(f"Same model: {'Yes (already cheap)' if is_cheap else 'No (uses cheaper variant)'}")
        print(f"Trading tier: {cost_info['trading_cost_tier']}")
        print(f"Research tier: {cost_info['research_cost_tier']}")
        print()


def demo_enhanced_research(symbol="SAP.DE", trading_model="openai/gpt-4-turbo"):
    """
    Demonstrate complete enhanced research pipeline.

    Args:
        symbol: Stock symbol to research
        trading_model: Trading model to use
    """
    print_header(f"ENHANCED RESEARCH PIPELINE DEMO: {symbol}")

    # Check API key
    if not settings.OPENROUTER_API_KEY:
        print("❌ ERROR: OPENROUTER_API_KEY not set in .env file")
        print("\nPlease set your OpenRouter API key:")
        print("1. Copy .env.example to .env")
        print("2. Add your API key: OPENROUTER_API_KEY=sk-or-v1-...")
        return

    print(f"Symbol: {symbol}")
    print(f"Trading Model: {trading_model}")
    print(f"Research Model: {ResearchModelMapper.get_research_model(trading_model)}")

    # Initialize pipeline
    print_section("Initializing Pipeline")

    client = OpenRouterClient(api_key=settings.OPENROUTER_API_KEY)
    pipeline = EnhancedResearchPipeline(
        openrouter_client=client,
        trading_model=trading_model
    )

    print("✅ Pipeline initialized")
    print(f"   Trading model: {pipeline.trading_model}")
    print(f"   Research model: {pipeline.research_model}")
    print(f"   Company: {ResearchModelMapper.get_model_company(trading_model)}")

    # Show cost estimate
    print_section("Cost Estimate")
    cost_info = pipeline.get_cost_estimate()
    print(f"Trading model: {cost_info['trading_model']}")
    print(f"Research model: {cost_info['research_model']}")
    print(f"Trading cost tier: {cost_info['trading_cost_tier']}")
    print(f"Research cost tier: {cost_info['research_cost_tier']}")
    print(f"\nEstimated cost per research: {cost_info['estimated_cost_per_research']}")
    print(f"Research model calls: {cost_info['pipeline_stages']['total_research_calls']}")

    # Run research pipeline
    print_section("Running Enhanced Research Pipeline")
    print("This will execute all 4 stages:")
    print("  1. Generate intelligent queries (LLM)")
    print("  2. Execute web searches")
    print("  3. Synthesize findings (LLM)")
    print("  4. Verify quality (LLM)")
    print("\nThis may take 30-60 seconds...")

    results = pipeline.conduct_stock_research(
        symbol=symbol,
        existing_data={
            "note": "Demo research - no existing portfolio data"
        },
        num_queries=3,
        verify_quality=True
    )

    # Show pipeline summary
    print_section("Pipeline Summary")
    summary = pipeline.get_pipeline_summary(results)
    print(summary)

    if not results.get("success"):
        print("\n❌ Pipeline failed!")
        print(f"Error: {results.get('error', 'Unknown error')}")
        return

    # Show generated queries
    print_section("Stage 1: Generated Queries")
    queries = results.get("pipeline_stages", {}).get("query_generation", {}).get("queries", [])
    for i, query in enumerate(queries, 1):
        print(f"{i}. {query}")

    # Show data collection stats
    print_section("Stage 2: Data Collection")
    data_collection = results.get("pipeline_stages", {}).get("data_collection", {})
    print(f"Total results found: {data_collection.get('total_results', 0)}")
    print(f"Unique sources: {data_collection.get('unique_results', 0)}")

    # Show synthesis results
    print_section("Stage 3: Research Synthesis")
    briefing = results.get("briefing", {})
    print(f"Confidence Level: {briefing.get('confidence_level', 'UNKNOWN')}")

    metadata = briefing.get("metadata", {})
    if metadata:
        credibility = metadata.get("credibility_breakdown", {})
        print(f"\nSource Credibility Breakdown:")
        print(f"  High:   {credibility.get('high', 0)}")
        print(f"  Medium: {credibility.get('medium', 0)}")
        print(f"  Low:    {credibility.get('low', 0)}")

    print("\nKey Takeaways:")
    for i, takeaway in enumerate(briefing.get('key_takeaways', []), 1):
        print(f"  {i}. {takeaway}")

    contradictions = briefing.get('contradictions_found', [])
    if contradictions and contradictions != []:
        print("\n⚠️  Contradictions detected:")
        for contradiction in contradictions:
            print(f"  • {contradiction}")

    gaps = briefing.get('data_gaps', [])
    if gaps and gaps != []:
        print("\n📝 Data gaps identified:")
        for gap in gaps:
            print(f"  • {gap}")

    # Show quality verification
    print_section("Stage 4: Quality Verification")
    verification = results.get("pipeline_stages", {}).get("verification", {}).get("verification", {})

    if verification:
        quality_score = verification.get("quality_score", 0)
        assessment = verification.get("overall_assessment", "UNKNOWN")

        print(f"Quality Score: {quality_score}/100")
        print(f"Assessment: {assessment}")
        print(f"\nDetailed Scores:")
        print(f"  Accuracy:     {verification.get('accuracy_score', 0)}/25")
        print(f"  Completeness: {verification.get('completeness_score', 0)}/25")
        print(f"  Objectivity:  {verification.get('objectivity_score', 0)}/25")
        print(f"  Usefulness:   {verification.get('usefulness_score', 0)}/25")

        strengths = verification.get("strengths", [])
        if strengths:
            print("\n✅ Strengths:")
            for strength in strengths:
                print(f"  • {strength}")

        issues = verification.get("issues_found", [])
        if issues:
            print("\n⚠️  Issues:")
            for issue in issues:
                print(f"  • {issue}")

    # Show formatted briefing for trading LLM
    print_section("Formatted Briefing for Trading LLM")
    formatted = results.get("formatted_briefing", "")
    print(formatted)

    # Performance metrics
    print_section("Performance Metrics")
    timing = results.get("timing", {})
    print(f"Query Generation: {timing.get('query_generation', 0):.2f}s")
    print(f"Data Collection:  {timing.get('data_collection', 0):.2f}s")
    print(f"Synthesis:        {timing.get('synthesis', 0):.2f}s")
    print(f"Verification:     {timing.get('verification', 0):.2f}s")
    print(f"─────────────────────────────────")
    print(f"Total Time:       {timing.get('total', 0):.2f}s")


def demo_comparison():
    """Compare basic research vs enhanced research."""
    print_header("COMPARISON: Basic vs Enhanced Research")

    print("""
┌─────────────────────────────────────────────────────────────────────┐
│                    BASIC RESEARCH (Phase 3)                         │
├─────────────────────────────────────────────────────────────────────┤
│ 1. DuckDuckGo search with generic query                            │
│ 2. Extract raw results (titles, snippets, URLs)                    │
│ 3. Format as text dump                                             │
│ 4. Pass directly to trading LLM                                    │
│                                                                     │
│ Issues:                                                             │
│  ❌ No source credibility assessment                                │
│  ❌ No synthesis or analysis                                        │
│  ❌ Promotional/spam sites treated same as Bloomberg                │
│  ❌ Contradictions not identified                                   │
│  ❌ Missing context and technical data                              │
│                                                                     │
│ Cost: ~$0.02 (1 trading LLM call)                                  │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                  ENHANCED RESEARCH (Phase 3.5.1)                    │
├─────────────────────────────────────────────────────────────────────┤
│ STAGE 1: Intelligent Query Generation                              │
│  • Research LLM generates targeted queries                         │
│  • Adapts to existing data and gaps                                │
│                                                                     │
│ STAGE 2: Data Collection                                           │
│  • Execute targeted searches                                       │
│  • Collect from multiple sources                                   │
│  • Deduplicate results                                             │
│                                                                     │
│ STAGE 3: Research Synthesis                                        │
│  • Research LLM analyzes all sources                               │
│  • Assesses source credibility (high/medium/low)                   │
│  • Identifies contradictions and gaps                              │
│  • Synthesizes into coherent briefing                              │
│                                                                     │
│ STAGE 4: Quality Verification                                      │
│  • Research LLM reviews own synthesis                              │
│  • Scores quality (0-100)                                          │
│  • Validates accuracy and completeness                             │
│  • Pass/fail determination                                         │
│                                                                     │
│ Benefits:                                                           │
│  ✅ High-quality, verified briefings                                │
│  ✅ Source credibility rated and shown                              │
│  ✅ Contradictions flagged                                          │
│  ✅ Data gaps identified                                            │
│  ✅ Objective, professional analysis                                │
│                                                                     │
│ Cost: ~$0.03 (3 research LLM calls + 1 trading LLM call)           │
│ Marginal cost: +$0.01 for dramatically better quality              │
└─────────────────────────────────────────────────────────────────────┘
""")


def main():
    """Main demo function."""
    print_header("ENHANCED RESEARCH PIPELINE - INTERACTIVE DEMO")

    print("""
This demo showcases Phase 3.5.1: LLM-Powered Research Pipeline

Features demonstrated:
  • Intelligent query generation (LLM)
  • Multi-source data collection
  • Research synthesis with credibility assessment
  • Quality verification and scoring
  • Cost-effective model usage (cheaper model from same company)

Requirements:
  • OpenRouter API key in .env file
  • Internet connection for web searches
""")

    # Show model mapping
    demo_model_mapping()

    # Show comparison
    demo_comparison()

    # Interactive menu
    while True:
        print("\n" + "=" * 70)
        print("Choose an option:")
        print("  1. Run full enhanced research demo (SAP.DE with GPT-4)")
        print("  2. Run enhanced research with different model")
        print("  3. Run enhanced research with different stock")
        print("  4. Exit")
        print("=" * 70)

        choice = input("\nEnter choice (1-4): ").strip()

        if choice == "1":
            demo_enhanced_research("SAP.DE", "openai/gpt-4-turbo")

        elif choice == "2":
            print("\nAvailable models:")
            print("  1. openai/gpt-4-turbo (uses gpt-3.5-turbo for research)")
            print("  2. anthropic/claude-3-opus-20240229 (uses claude-3-haiku for research)")
            print("  3. google/gemini-pro (uses gemini-pro for research - already cheap)")
            print("  4. deepseek/deepseek-chat (uses deepseek-chat for research - already cheap)")

            model_choice = input("Enter model choice (1-4): ").strip()
            model_map = {
                "1": "openai/gpt-4-turbo",
                "2": "anthropic/claude-3-opus-20240229",
                "3": "google/gemini-pro",
                "4": "deepseek/deepseek-chat"
            }

            if model_choice in model_map:
                demo_enhanced_research("SAP.DE", model_map[model_choice])
            else:
                print("Invalid choice")

        elif choice == "3":
            symbol = input("Enter stock symbol (e.g., BMW.DE, VOW3.DE): ").strip().upper()
            if symbol:
                demo_enhanced_research(symbol, "openai/gpt-4-turbo")
            else:
                print("Invalid symbol")

        elif choice == "4":
            print("\n👋 Goodbye!")
            break

        else:
            print("Invalid choice. Please enter 1-4.")


if __name__ == "__main__":
    main()
