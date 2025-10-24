"""
Unit tests for OpenRouter API client.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from backend.services.openrouter_client import OpenRouterClient


class TestOpenRouterClient:
    """Test suite for OpenRouterClient."""

    @pytest.fixture
    def mock_api_key(self):
        """Fixture for mock API key."""
        return "test-api-key-12345"

    @pytest.fixture
    def client(self, mock_api_key):
        """Fixture for OpenRouter client."""
        return OpenRouterClient(api_key=mock_api_key)

    def test_client_initialization(self, mock_api_key):
        """Test client initializes correctly."""
        client = OpenRouterClient(api_key=mock_api_key)
        assert client.api_key == mock_api_key
        assert client.session is not None

    def test_client_initialization_no_api_key(self):
        """Test client raises error without API key."""
        with patch('backend.services.openrouter_client.settings') as mock_settings:
            mock_settings.OPENROUTER_API_KEY = None
            with pytest.raises(ValueError, match="API key is required"):
                OpenRouterClient()

    @patch('backend.services.openrouter_client.requests.Session.post')
    def test_chat_completion_success(self, mock_post, client):
        """Test successful chat completion."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Test response"
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15
            }
        }
        mock_post.return_value = mock_response

        # Call method
        result = client.chat_completion(
            model="openai/gpt-4",
            messages=[{"role": "user", "content": "Hello"}]
        )

        # Verify
        assert "choices" in result
        assert result["choices"][0]["message"]["content"] == "Test response"
        mock_post.assert_called_once()

    @patch('backend.services.openrouter_client.requests.Session.post')
    def test_chat_completion_http_error(self, mock_post, client):
        """Test chat completion handles HTTP errors."""
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
        mock_post.return_value = mock_response

        # Should raise HTTPError
        with pytest.raises(requests.exceptions.HTTPError):
            client.chat_completion(
                model="openai/gpt-4",
                messages=[{"role": "user", "content": "Hello"}]
            )

    @patch('backend.services.openrouter_client.requests.Session.post')
    def test_chat_completion_timeout(self, mock_post, client):
        """Test chat completion handles timeout."""
        # Mock timeout
        mock_post.side_effect = requests.exceptions.Timeout()

        # Should raise Timeout
        with pytest.raises(requests.exceptions.Timeout):
            client.chat_completion(
                model="openai/gpt-4",
                messages=[{"role": "user", "content": "Hello"}]
            )

    @patch('backend.services.openrouter_client.requests.Session.post')
    def test_get_completion_text_success(self, mock_post, client):
        """Test getting completion text."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Test response text"
                    }
                }
            ],
            "usage": {"total_tokens": 15}
        }
        mock_post.return_value = mock_response

        # Call method
        text = client.get_completion_text(
            model="openai/gpt-4",
            messages=[{"role": "user", "content": "Hello"}]
        )

        # Verify
        assert text == "Test response text"

    @patch('backend.services.openrouter_client.requests.Session.post')
    def test_get_completion_text_no_content(self, mock_post, client):
        """Test getting completion text with no content."""
        # Mock response with no content
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": []}
        mock_post.return_value = mock_response

        # Call method
        text = client.get_completion_text(
            model="openai/gpt-4",
            messages=[{"role": "user", "content": "Hello"}]
        )

        # Verify
        assert text is None

    @patch('backend.services.openrouter_client.requests.Session.get')
    def test_list_models_success(self, mock_get, client):
        """Test listing available models."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"id": "openai/gpt-4", "name": "GPT-4"},
                {"id": "anthropic/claude-3-opus", "name": "Claude 3 Opus"}
            ]
        }
        mock_get.return_value = mock_response

        # Call method
        models = client.list_models()

        # Verify
        assert len(models) == 2
        assert models[0]["id"] == "openai/gpt-4"
        assert models[1]["id"] == "anthropic/claude-3-opus"

    @patch('backend.services.openrouter_client.requests.Session.get')
    def test_list_models_error(self, mock_get, client):
        """Test listing models handles errors."""
        # Mock error
        mock_get.side_effect = requests.exceptions.RequestException()

        # Call method
        models = client.list_models()

        # Should return empty list on error
        assert models == []

    def test_get_model_info(self, client):
        """Test getting model information."""
        with patch.object(client, 'list_models') as mock_list:
            mock_list.return_value = [
                {"id": "openai/gpt-4", "name": "GPT-4", "pricing": {"prompt": "0.03"}},
                {"id": "anthropic/claude-3-opus", "name": "Claude 3 Opus"}
            ]

            # Get existing model
            info = client.get_model_info("openai/gpt-4")
            assert info is not None
            assert info["name"] == "GPT-4"

            # Get non-existent model
            info = client.get_model_info("nonexistent/model")
            assert info is None

    def test_estimate_cost(self, client):
        """Test cost estimation."""
        with patch.object(client, 'get_model_info') as mock_info:
            mock_info.return_value = {
                "id": "openai/gpt-4",
                "pricing": {
                    "prompt": "30",  # $30 per 1M tokens
                    "completion": "60"  # $60 per 1M tokens
                }
            }

            # Estimate cost
            cost = client.estimate_cost("openai/gpt-4", 1000, 500)

            # Should be (1000/1M * 30) + (500/1M * 60) = 0.03 + 0.03 = 0.06
            assert cost is not None
            assert abs(cost - 0.06) < 0.001

    def test_estimate_cost_no_pricing(self, client):
        """Test cost estimation with no pricing info."""
        with patch.object(client, 'get_model_info') as mock_info:
            mock_info.return_value = None

            cost = client.estimate_cost("unknown/model", 1000, 500)
            assert cost is None

    def test_context_manager(self, mock_api_key):
        """Test client works as context manager."""
        with patch('backend.services.openrouter_client.requests.Session.close') as mock_close:
            with OpenRouterClient(api_key=mock_api_key) as client:
                assert client is not None
            mock_close.assert_called_once()

    def test_close(self, client):
        """Test client close method."""
        with patch.object(client.session, 'close') as mock_close:
            client.close()
            mock_close.assert_called_once()
