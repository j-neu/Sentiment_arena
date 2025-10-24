"""
Research Model Mapper

Maps trading LLM models to their cheaper research counterparts from the same company.
For already-cheap models, uses the same model for both research and trading.
"""

from typing import Dict, Tuple


class ResearchModelMapper:
    """
    Maps trading models to appropriate research models.

    Strategy:
    - Premium models → Use cheaper model from same company for research
    - Already cheap models → Use same model for both research and trading
    """

    # Model family mappings: trading_model → (research_model, company)
    MODEL_MAPPINGS: Dict[str, Tuple[str, str]] = {
        # OpenAI models
        "openai/gpt-4-turbo": ("openai/gpt-3.5-turbo", "OpenAI"),
        "openai/gpt-4": ("openai/gpt-3.5-turbo", "OpenAI"),
        "openai/gpt-4-turbo-preview": ("openai/gpt-3.5-turbo", "OpenAI"),
        "openai/gpt-4-0125-preview": ("openai/gpt-3.5-turbo", "OpenAI"),
        "openai/gpt-4-1106-preview": ("openai/gpt-3.5-turbo", "OpenAI"),
        "openai/gpt-4o": ("openai/gpt-3.5-turbo", "OpenAI"),
        "openai/gpt-4o-mini": ("openai/gpt-4o-mini", "OpenAI"),  # Already cheap
        "openai/gpt-3.5-turbo": ("openai/gpt-3.5-turbo", "OpenAI"),  # Already cheap

        # Anthropic models
        "anthropic/claude-3-opus-20240229": ("anthropic/claude-3-haiku-20240307", "Anthropic"),
        "anthropic/claude-3-opus": ("anthropic/claude-3-haiku-20240307", "Anthropic"),
        "anthropic/claude-3-sonnet-20240229": ("anthropic/claude-3-haiku-20240307", "Anthropic"),
        "anthropic/claude-3-sonnet": ("anthropic/claude-3-haiku-20240307", "Anthropic"),
        "anthropic/claude-3-haiku-20240307": ("anthropic/claude-3-haiku-20240307", "Anthropic"),  # Already cheap
        "anthropic/claude-3-haiku": ("anthropic/claude-3-haiku-20240307", "Anthropic"),  # Already cheap
        "anthropic/claude-3.5-sonnet": ("anthropic/claude-3-haiku-20240307", "Anthropic"),
        "anthropic/claude-3-5-sonnet-20240620": ("anthropic/claude-3-haiku-20240307", "Anthropic"),

        # Google models
        "google/gemini-pro": ("google/gemini-pro", "Google"),  # Already cheap
        "google/gemini-pro-vision": ("google/gemini-pro", "Google"),
        "google/gemini-1.5-pro": ("google/gemini-pro", "Google"),
        "google/gemini-flash": ("google/gemini-flash", "Google"),  # Already cheap

        # Meta models
        "meta-llama/llama-3-70b-instruct": ("meta-llama/llama-3-8b-instruct", "Meta"),
        "meta-llama/llama-3-8b-instruct": ("meta-llama/llama-3-8b-instruct", "Meta"),  # Already cheap
        "meta-llama/llama-3.1-405b-instruct": ("meta-llama/llama-3.1-8b-instruct", "Meta"),
        "meta-llama/llama-3.1-70b-instruct": ("meta-llama/llama-3.1-8b-instruct", "Meta"),
        "meta-llama/llama-3.1-8b-instruct": ("meta-llama/llama-3.1-8b-instruct", "Meta"),  # Already cheap

        # Mistral models
        "mistralai/mistral-large": ("mistralai/mistral-small", "Mistral"),
        "mistralai/mistral-medium": ("mistralai/mistral-small", "Mistral"),
        "mistralai/mistral-small": ("mistralai/mistral-small", "Mistral"),  # Already cheap
        "mistralai/mistral-7b-instruct": ("mistralai/mistral-7b-instruct", "Mistral"),  # Already cheap

        # DeepSeek models (already very cheap)
        "deepseek/deepseek-chat": ("deepseek/deepseek-chat", "DeepSeek"),
        "deepseek/deepseek-coder": ("deepseek/deepseek-coder", "DeepSeek"),

        # Cohere models
        "cohere/command-r-plus": ("cohere/command-r", "Cohere"),
        "cohere/command-r": ("cohere/command-r", "Cohere"),  # Already cheap
        "cohere/command": ("cohere/command", "Cohere"),  # Already cheap

        # Perplexity models
        "perplexity/llama-3-sonar-large-32k-online": ("perplexity/llama-3-sonar-small-32k-online", "Perplexity"),
        "perplexity/llama-3-sonar-small-32k-online": ("perplexity/llama-3-sonar-small-32k-online", "Perplexity"),
    }

    @classmethod
    def get_research_model(cls, trading_model: str) -> str:
        """
        Get the appropriate research model for a given trading model.

        Args:
            trading_model: The model identifier used for trading decisions

        Returns:
            The model identifier to use for research tasks

        Examples:
            >>> ResearchModelMapper.get_research_model("openai/gpt-4-turbo")
            'openai/gpt-3.5-turbo'

            >>> ResearchModelMapper.get_research_model("deepseek/deepseek-chat")
            'deepseek/deepseek-chat'
        """
        if trading_model in cls.MODEL_MAPPINGS:
            research_model, _ = cls.MODEL_MAPPINGS[trading_model]
            return research_model

        # If unknown model, use the same model (safe fallback)
        return trading_model

    @classmethod
    def get_model_company(cls, model: str) -> str:
        """
        Get the company/provider for a model.

        Args:
            model: The model identifier

        Returns:
            The company name (OpenAI, Anthropic, Google, etc.)
        """
        if model in cls.MODEL_MAPPINGS:
            _, company = cls.MODEL_MAPPINGS[model]
            return company

        # Try to infer from model prefix
        if model.startswith("openai/"):
            return "OpenAI"
        elif model.startswith("anthropic/"):
            return "Anthropic"
        elif model.startswith("google/"):
            return "Google"
        elif model.startswith("meta-llama/"):
            return "Meta"
        elif model.startswith("mistralai/"):
            return "Mistral"
        elif model.startswith("deepseek/"):
            return "DeepSeek"
        elif model.startswith("cohere/"):
            return "Cohere"
        elif model.startswith("perplexity/"):
            return "Perplexity"

        return "Unknown"

    @classmethod
    def is_cheap_model(cls, model: str) -> bool:
        """
        Check if a model is already cheap (uses same model for research).

        Args:
            model: The model identifier

        Returns:
            True if the model uses itself for research, False otherwise
        """
        research_model = cls.get_research_model(model)
        return research_model == model

    @classmethod
    def get_cost_estimate(cls, trading_model: str) -> Dict[str, str]:
        """
        Get cost tier estimates for trading and research models.

        Args:
            trading_model: The trading model identifier

        Returns:
            Dictionary with 'trading' and 'research' cost tiers
        """
        research_model = cls.get_research_model(trading_model)

        # Rough cost tiers (actual costs vary)
        COST_TIERS = {
            # Premium models
            "openai/gpt-4": "premium",
            "openai/gpt-4-turbo": "premium",
            "openai/gpt-4o": "premium",
            "anthropic/claude-3-opus": "premium",
            "anthropic/claude-3-opus-20240229": "premium",
            "anthropic/claude-3-5-sonnet-20240620": "premium",
            "google/gemini-1.5-pro": "premium",
            "meta-llama/llama-3.1-405b-instruct": "premium",

            # Mid-tier models
            "openai/gpt-3.5-turbo": "mid",
            "anthropic/claude-3-sonnet": "mid",
            "anthropic/claude-3-sonnet-20240229": "mid",
            "meta-llama/llama-3-70b-instruct": "mid",
            "meta-llama/llama-3.1-70b-instruct": "mid",

            # Cheap models
            "openai/gpt-4o-mini": "cheap",
            "anthropic/claude-3-haiku": "cheap",
            "anthropic/claude-3-haiku-20240307": "cheap",
            "google/gemini-pro": "cheap",
            "google/gemini-flash": "cheap",
            "meta-llama/llama-3-8b-instruct": "cheap",
            "meta-llama/llama-3.1-8b-instruct": "cheap",
            "deepseek/deepseek-chat": "cheap",
            "deepseek/deepseek-coder": "cheap",
        }

        trading_tier = COST_TIERS.get(trading_model, "unknown")
        research_tier = COST_TIERS.get(research_model, "unknown")

        return {
            "trading_model": trading_model,
            "research_model": research_model,
            "trading_cost_tier": trading_tier,
            "research_cost_tier": research_tier,
            "is_same_model": trading_model == research_model
        }

    @classmethod
    def list_supported_models(cls) -> Dict[str, list]:
        """
        List all supported models grouped by company.

        Returns:
            Dictionary with companies as keys and lists of models as values
        """
        companies: Dict[str, list] = {}

        for model, (research_model, company) in cls.MODEL_MAPPINGS.items():
            if company not in companies:
                companies[company] = []

            companies[company].append({
                "trading_model": model,
                "research_model": research_model,
                "uses_same": model == research_model
            })

        return companies
