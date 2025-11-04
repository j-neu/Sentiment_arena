#!/usr/bin/env python3
"""
Comprehensive Component Testing Script for Sentiment Arena

This script tests each component individually before running the full system.
Run this first to identify and fix issues before attempting full trading sessions.
"""

import sys
import time
from pathlib import Path
from datetime import datetime
import traceback

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database.base import SessionLocal
from backend.services.market_data import MarketDataService
from backend.services.openrouter_client import OpenRouterClient
from backend.services.alphavantage_client import AlphaVantageClient
from backend.services.finnhub_client import FinnhubClient
from backend.services.research import ResearchService
from backend.services.technical_analysis import TechnicalAnalysisService
from backend.services.trading_engine import TradingEngine
from backend.config import settings
from backend.logger import get_logger

logger = get_logger(__name__)

class ComponentTester:
    """Test individual components of the Sentiment Arena system."""
    
    def __init__(self):
        self.db = SessionLocal()
        self.results = {}
        
    def run_all_tests(self):
        """Run all component tests."""
        print("=" * 80)
        print("SENTIMENT ARENA - COMPREHENSIVE COMPONENT TESTING")
        print("=" * 80)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        tests = [
            ("Database Connection", self.test_database),
            ("Market Data Service", self.test_market_data),
            ("OpenRouter API", self.test_openrouter_api),
            ("Alpha Vantage API", self.test_alphavantage_api),
            ("Finnhub API", self.test_finnhub_api),
            ("Web Search Service", self.test_web_search),
            ("Technical Analysis", self.test_technical_analysis),
            ("Trading Engine", self.test_trading_engine),
            ("Research Pipeline", self.test_research_pipeline),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            print(f"Testing {test_name}...")
            try:
                result = test_func()
                self.results[test_name] = result
                if result['success']:
                    print(f"  ✅ PASSED: {result['message']}")
                    passed += 1
                else:
                    print(f"  ❌ FAILED: {result['message']}")
                    failed += 1
            except Exception as e:
                print(f"  💥 ERROR: {str(e)}")
                self.results[test_name] = {'success': False, 'message': str(e)}
                failed += 1
            print()
        
        # Summary
        print("=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"Total Tests: {passed + failed}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {(passed / (passed + failed) * 100):.1f}%")
        print()
        
        if failed > 0:
            print("FAILED TESTS:")
            for test_name, result in self.results.items():
                if not result['success']:
                    print(f"  - {test_name}: {result['message']}")
            print()
            print("⚠️  Please fix failed tests before running full trading sessions!")
        else:
            print("🎉 All tests passed! System is ready for trading.")
        
        return passed, failed
    
    def test_database(self):
        """Test database connection and basic operations."""
        try:
            # Test basic query
            from backend.models.model import Model
            models = self.db.query(Model).count()
            
            return {
                'success': True,
                'message': f"Database connected. Found {models} models in database."
            }
        except Exception as e:
            return {
                'success': False,
                'message': f"Database error: {str(e)}"
            }
    
    def test_market_data(self):
        """Test market data service with German stocks."""
        try:
            service = MarketDataService()
            
            # Test German stocks
            test_symbols = ['SAP.DE', 'SIE.DE', 'AIR.DE']
            results = {}
            
            for symbol in test_symbols:
                try:
                    data = service.fetch_price(symbol)
                    if data and 'price' in data:
                        results[symbol] = f"€{data['price']:.2f}"
                    else:
                        results[symbol] = "No data"
                except Exception as e:
                    results[symbol] = f"Error: {str(e)}"
            
            success_count = sum(1 for v in results.values() if '€' in str(v))
            
            return {
                'success': success_count >= 2,
                'message': f"Market data: {success_count}/3 stocks successful. Results: {results}"
            }
        except Exception as e:
            return {
                'success': False,
                'message': f"Market data service error: {str(e)}"
            }
    
    def test_openrouter_api(self):
        """Test OpenRouter API connectivity."""
        try:
            client = OpenRouterClient()
            
            # Test with a simple completion
            response = client.get_completion_text(
                model="openai/gpt-4o-mini",
                messages=[
                    {"role": "user", "content": "Say 'API test successful'"}
                ],
                max_tokens=10
            )
            
            if response and "successful" in response.lower():
                return {
                    'success': True,
                    'message': "OpenRouter API working correctly."
                }
            else:
                return {
                    'success': False,
                    'message': f"Unexpected response: {response}"
                }
        except Exception as e:
            return {
                'success': False,
                'message': f"OpenRouter API error: {str(e)}"
            }
    
    def test_alphavantage_api(self):
        """Test Alpha Vantage API for German stocks."""
        try:
            client = AlphaVantageClient()
            
            # Test German stock symbols
            test_symbols = ['SAP', 'SIE', 'AIR']  # Without .DE
            results = {}
            
            for symbol in test_symbols:
                try:
                    # Test overview endpoint
                    overview = client.get_company_overview(symbol)
                    if overview and 'Symbol' in overview:
                        results[symbol] = "Data available"
                    else:
                        results[symbol] = "No data"
                except Exception as e:
                    results[symbol] = f"Error: {str(e)}"
            
            success_count = sum(1 for v in results.values() if v == "Data available")
            
            return {
                'success': success_count >= 1,
                'message': f"Alpha Vantage: {success_count}/3 stocks have data. Results: {results}"
            }
        except Exception as e:
            return {
                'success': False,
                'message': f"Alpha Vantage API error: {str(e)}"
            }
    
    def test_finnhub_api(self):
        """Test Finnhub API for sentiment and recommendations."""
        try:
            client = FinnhubClient()
            
            # Test German stock symbols
            test_symbols = ['SAP', 'SIE', 'AIR']
            results = {}
            
            for symbol in test_symbols:
                try:
                    # Test news endpoint
                    news = client.get_company_news(symbol)
                    if news and len(news) > 0:
                        results[symbol] = f"{len(news)} articles"
                    else:
                        results[symbol] = "No news"
                except Exception as e:
                    results[symbol] = f"Error: {str(e)}"
            
            success_count = sum(1 for v in results.values() if 'articles' in str(v))
            
            return {
                'success': success_count >= 1,
                'message': f"Finnhub: {success_count}/3 stocks have news. Results: {results}"
            }
        except Exception as e:
            return {
                'success': False,
                'message': f"Finnhub API error: {str(e)}"
            }
    
    def test_web_search(self):
        """Test web search functionality."""
        try:
            service = ResearchService()
            
            # Test search for German stocks
            test_queries = [
                "SAP stock news",
                "Siemens earnings",
                "Airbus aircraft orders"
            ]
            
            results = {}
            for query in test_queries:
                try:
                    search_results = service._web_search(query, 5, "1d")
                    results[query] = f"{len(search_results)} results"
                except Exception as e:
                    results[query] = f"Error: {str(e)}"
            
            success_count = sum(1 for v in results.values() if 'results' in str(v) and '0' not in str(v))
            
            return {
                'success': success_count >= 2,
                'message': f"Web search: {success_count}/3 queries successful. Results: {results}"
            }
        except Exception as e:
            return {
                'success': False,
                'message': f"Web search error: {str(e)}"
            }
    
    def test_technical_analysis(self):
        """Test technical analysis service."""
        try:
            service = TechnicalAnalysisService()
            
            # Test with German stock
            analysis = service.analyze_stock('SAP.DE')
            
            if analysis and 'signals' in analysis:
                signal_count = len(analysis.get('signals', []))
                return {
                    'success': True,
                    'message': f"Technical analysis working. Generated {signal_count} signals."
                }
            else:
                return {
                    'success': False,
                    'message': "Technical analysis returned insufficient data."
                }
        except Exception as e:
            return {
                'success': False,
                'message': f"Technical analysis error: {str(e)}"
            }
    
    def test_trading_engine(self):
        """Test trading engine basic operations."""
        try:
            engine = TradingEngine()
            
            # Test portfolio initialization
            from backend.models.model import Model
            model = self.db.query(Model).first()
            
            if model:
                portfolio = engine.initialize_portfolio(model.id)
                if portfolio and portfolio.current_balance == model.starting_balance:
                    return {
                        'success': True,
                        'message': "Trading engine working. Portfolio initialized correctly."
                    }
                else:
                    return {
                        'success': False,
                        'message': "Portfolio initialization failed."
                    }
            else:
                return {
                    'success': False,
                    'message': "No models found in database."
                }
        except Exception as e:
            return {
                'success': False,
                'message': f"Trading engine error: {str(e)}"
            }
    
    def test_research_pipeline(self):
        """Test complete research pipeline."""
        try:
            from backend.services.complete_research_orchestrator import CompleteResearchOrchestrator
            
            orchestrator = CompleteResearchOrchestrator(
                openrouter_api_key=settings.OPENROUTER_API_KEY,
                alphavantage_api_key=getattr(settings, 'ALPHAVANTAGE_API_KEY', None),
                finnhub_api_key=getattr(settings, 'FINNHUB_API_KEY', None),
                model_identifier="openai/gpt-4o-mini"
            )
            
            # Test research for one stock
            result = orchestrator.conduct_complete_research(
                symbol='SAP.DE',
                include_technical=True,
                include_financial_apis=True,
                include_web_research=True,
                include_quality_verification=False
            )
            
            if result.get('success') and result.get('unified_briefing'):
                briefing_length = len(result['unified_briefing'])
                return {
                    'success': True,
                    'message': f"Research pipeline working. Generated {briefing_length} character briefing."
                }
            else:
                return {
                    'success': False,
                    'message': f"Research failed: {result.get('errors', 'Unknown error')}"
                }
        except Exception as e:
            return {
                'success': False,
                'message': f"Research pipeline error: {str(e)}"
            }
    
    def close(self):
        """Clean up resources."""
        self.db.close()

def main():
    """Main testing function."""
    tester = ComponentTester()
    
    try:
        passed, failed = tester.run_all_tests()
        
        # Exit with appropriate code
        if failed > 0:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\n\nTesting interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error during testing: {e}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        tester.close()

if __name__ == "__main__":
    main()