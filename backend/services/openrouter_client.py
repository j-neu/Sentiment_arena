"""
OpenRouter API client for accessing multiple LLM models.

This module provides a client for interacting with the OpenRouter API,
which provides unified access to multiple LLM models (GPT-4, Claude, Gemini, etc.).
"""

import time
from typing import Dict, List, Optional, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from backend.config import settings
from backend.logger import get_logger

logger = get_logger(__name__)


class OpenRouterClient:
    """Client for interacting with the OpenRouter API."""

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the OpenRouter client.

        Args:
            api_key: OpenRouter API key. If not provided, uses settings.OPENROUTER_API_KEY
        """
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        if not self.api_key:
            raise ValueError("OpenRouter API key is required")

        # Set up session with retry logic
        self.session = self._create_session()

        logger.info("OpenRouter client initialized")

    def _create_session(self) -> requests.Session:
        """
        Create a requests session with retry logic.

        Returns:
            Configured requests.Session
        """
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=3,  # Total number of retries
            backoff_factor=1,  # Wait 1, 2, 4 seconds between retries
            status_forcelist=[429, 500, 502, 503, 504],  # Retry on these HTTP status codes
            allowed_methods=["POST"]  # Only retry POST requests
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        return session

    def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a chat completion using the OpenRouter API.

        Args:
            model: Model identifier (e.g., "openai/gpt-4-turbo")
            messages: List of message objects with 'role' and 'content'
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            **kwargs: Additional parameters to pass to the API

        Returns:
            API response dictionary containing the completion

        Raises:
            requests.exceptions.RequestException: If the API request fails
        """
        url = f"{self.BASE_URL}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/sentiment-arena",  # Optional, for rankings
            "X-Title": "Sentiment Arena Trading Bot"  # Optional, for rankings
        }

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            **kwargs
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        logger.info(f"Requesting completion from model: {model}")
        logger.debug(f"Request payload: {payload}")

        try:
            start_time = time.time()
            response = self.session.post(url, json=payload, headers=headers, timeout=60)
            elapsed_time = time.time() - start_time

            response.raise_for_status()

            result = response.json()

            # Log usage information
            if "usage" in result:
                usage = result["usage"]
                logger.info(
                    f"Completion successful in {elapsed_time:.2f}s - "
                    f"Tokens: {usage.get('total_tokens', 0)} "
                    f"(prompt: {usage.get('prompt_tokens', 0)}, "
                    f"completion: {usage.get('completion_tokens', 0)})"
                )

            return result

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error from OpenRouter API: {e}")
            logger.error(f"Response: {e.response.text if e.response else 'No response'}")
            raise

        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout after 60s: {e}")
            raise

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error during API request: {e}")
            raise

    def get_completion_text(
        self,
        model: str,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Optional[str]:
        """
        Get the text content from a chat completion.

        Args:
            model: Model identifier
            messages: List of message objects
            **kwargs: Additional parameters

        Returns:
            The text content of the completion, or None if not found
        """
        try:
            result = self.chat_completion(model, messages, **kwargs)

            if "choices" in result and len(result["choices"]) > 0:
                choice = result["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    return choice["message"]["content"]

            logger.warning("No content found in API response")
            return None

        except Exception as e:
            logger.error(f"Failed to get completion text: {e}")
            return None

    def list_models(self) -> List[Dict[str, Any]]:
        """
        List available models from OpenRouter.

        Returns:
            List of model information dictionaries
        """
        url = f"{self.BASE_URL}/models"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

        try:
            response = self.session.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            result = response.json()

            if "data" in result:
                logger.info(f"Retrieved {len(result['data'])} available models")
                return result["data"]

            return []

        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

    def get_model_info(self, model: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific model.

        Args:
            model: Model identifier

        Returns:
            Model information dictionary, or None if not found
        """
        models = self.list_models()

        for model_info in models:
            if model_info.get("id") == model:
                return model_info

        logger.warning(f"Model not found: {model}")
        return None

    def estimate_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int
    ) -> Optional[float]:
        """
        Estimate the cost of a completion in USD.

        Args:
            model: Model identifier
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens

        Returns:
            Estimated cost in USD, or None if pricing info not available
        """
        model_info = self.get_model_info(model)

        if not model_info or "pricing" not in model_info:
            logger.warning(f"No pricing information available for model: {model}")
            return None

        pricing = model_info["pricing"]

        # Pricing is typically in USD per 1M tokens
        prompt_cost = (prompt_tokens / 1_000_000) * float(pricing.get("prompt", 0))
        completion_cost = (completion_tokens / 1_000_000) * float(pricing.get("completion", 0))

        total_cost = prompt_cost + completion_cost

        logger.debug(
            f"Cost estimate for {model}: "
            f"${total_cost:.6f} (prompt: ${prompt_cost:.6f}, completion: ${completion_cost:.6f})"
        )

        return total_cost

    def close(self):
        """Close the session."""
        self.session.close()
        logger.info("OpenRouter client session closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
