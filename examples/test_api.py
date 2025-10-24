"""
Example script to test the Sentiment Arena REST API
Demonstrates all available endpoints and their responses
"""

import requests
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000"


def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_response(endpoint: str, response: requests.Response):
    """Print formatted API response"""
    print(f"\nEndpoint: {endpoint}")
    print(f"Status: {response.status_code}")
    try:
        data = response.json()
        print(f"Response:\n{json.dumps(data, indent=2)}")
    except:
        print(f"Response: {response.text}")


def test_system_endpoints():
    """Test system and health endpoints"""
    print_section("SYSTEM ENDPOINTS")

    # Root endpoint
    response = requests.get(f"{BASE_URL}/")
    print_response("GET /", response)

    # Health check
    response = requests.get(f"{BASE_URL}/health")
    print_response("GET /health", response)


def test_model_endpoints():
    """Test model-related endpoints"""
    print_section("MODEL ENDPOINTS")

    # Get all models
    response = requests.get(f"{BASE_URL}/api/models")
    print_response("GET /api/models", response)

    models = response.json()
    if not models:
        print("\n⚠️  No models found in database. Run database initialization first:")
        print("   python backend/database/init_db.py")
        return

    # Test with first model
    model_id = models[0]["id"]
    print(f"\n📊 Testing with Model ID: {model_id} ({models[0]['name']})")

    # Get portfolio
    response = requests.get(f"{BASE_URL}/api/models/{model_id}/portfolio")
    print_response(f"GET /api/models/{model_id}/portfolio", response)

    # Get positions
    response = requests.get(f"{BASE_URL}/api/models/{model_id}/positions")
    print_response(f"GET /api/models/{model_id}/positions", response)

    # Get trades (with pagination)
    response = requests.get(f"{BASE_URL}/api/models/{model_id}/trades", params={"limit": 5})
    print_response(f"GET /api/models/{model_id}/trades?limit=5", response)

    # Get performance
    response = requests.get(f"{BASE_URL}/api/models/{model_id}/performance")
    print_response(f"GET /api/models/{model_id}/performance", response)

    # Get reasoning
    response = requests.get(f"{BASE_URL}/api/models/{model_id}/reasoning", params={"limit": 3})
    print_response(f"GET /api/models/{model_id}/reasoning?limit=3", response)


def test_leaderboard():
    """Test leaderboard endpoint"""
    print_section("LEADERBOARD")

    response = requests.get(f"{BASE_URL}/api/leaderboard")
    print_response("GET /api/leaderboard", response)


def test_market_status():
    """Test market status endpoint"""
    print_section("MARKET STATUS")

    response = requests.get(f"{BASE_URL}/api/market/status")
    print_response("GET /api/market/status", response)


def test_scheduler():
    """Test scheduler endpoints"""
    print_section("SCHEDULER")

    # Get scheduler status
    response = requests.get(f"{BASE_URL}/api/scheduler/status")
    print_response("GET /api/scheduler/status", response)


def test_admin_endpoints():
    """Test admin endpoints"""
    print_section("ADMIN ENDPOINTS")

    print("\n⚠️  WARNING: This will trigger a research job!")
    print("Press Enter to continue, or Ctrl+C to skip...")
    try:
        input()
    except KeyboardInterrupt:
        print("\nSkipped admin endpoints test")
        return

    # Trigger research
    response = requests.post(f"{BASE_URL}/api/admin/trigger-research")
    print_response("POST /api/admin/trigger-research", response)


def test_websocket_info():
    """Display WebSocket connection info"""
    print_section("WEBSOCKET")

    print("""
WebSocket Endpoint: ws://localhost:8000/ws/live

Example usage (JavaScript):
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/live');

ws.onopen = () => {
    console.log('Connected to Sentiment Arena live updates');
    // Send ping to keep connection alive
    setInterval(() => {
        ws.send(JSON.stringify({ type: 'ping' }));
    }, 30000);
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Update:', data);

    switch(data.type) {
        case 'position_update':
            // Handle position update
            break;
        case 'trade':
            // Handle new trade
            break;
        case 'reasoning':
            // Handle model reasoning
            break;
        case 'portfolio_update':
            // Handle portfolio change
            break;
        case 'scheduler_event':
            // Handle scheduler event
            break;
    }
};

ws.onerror = (error) => {
    console.error('WebSocket error:', error);
};

ws.onclose = () => {
    console.log('Disconnected');
};
```

Example usage (Python):
```python
import asyncio
import websockets
import json

async def connect():
    async with websockets.connect('ws://localhost:8000/ws/live') as websocket:
        # Receive welcome message
        welcome = await websocket.recv()
        print(f"Connected: {welcome}")

        # Listen for updates
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            print(f"Update: {data['type']}")

asyncio.run(connect())
```
    """)


def main():
    """Run all API tests"""
    print("\n")
    print("┌" + "─" * 78 + "┐")
    print("│" + " " * 20 + "SENTIMENT ARENA API TEST" + " " * 34 + "│")
    print("│" + " " * 22 + "Version 1.0.0" + " " * 43 + "│")
    print("└" + "─" * 78 + "┘")

    try:
        # Test connection
        print("\n🔌 Testing API connection...")
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        if response.status_code != 200:
            print("❌ API is not responding correctly")
            print("   Make sure the server is running:")
            print("   python -m uvicorn backend.main:app --port 8000")
            return
        print("✅ API is online and responding")

        # Run tests
        test_system_endpoints()
        test_model_endpoints()
        test_leaderboard()
        test_market_status()
        test_scheduler()
        test_websocket_info()
        test_admin_endpoints()

        # Summary
        print_section("TEST COMPLETE")
        print("""
✅ All endpoints tested successfully!

📚 API Documentation available at:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

🔌 WebSocket: ws://localhost:8000/ws/live

📊 Next steps:
   1. Initialize database with models: python backend/database/init_db.py
   2. Start trading: The scheduler will automatically run research and trading
   3. Monitor via API or build a frontend dashboard
        """)

    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API")
        print("   Make sure the server is running:")
        print("   python -m uvicorn backend.main:app --port 8000")
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")


if __name__ == "__main__":
    main()
