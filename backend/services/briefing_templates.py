"""
Briefing Templates System

Provides standardized templates for research briefings to ensure consistency.
Supports different templates for different trading strategies.
"""

from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass
from backend.logger import get_logger

logger = get_logger(__name__)


class TradingStrategy(Enum):
    """Trading strategy types."""
    SWING = "swing"
    DAY = "day"
    VALUE = "value"
    GROWTH = "growth"
    MOMENTUM = "momentum"
    CONTRARIAN = "contrarian"


class BriefingSection(Enum):
    """Required briefing sections."""
    RECENT_EVENTS = "recent_events"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    RISK_FACTORS = "risk_factors"
    TECHNICAL_ANALYSIS = "technical_analysis"
    FUNDAMENTAL_METRICS = "fundamental_metrics"
    SOURCE_QUALITY = "source_quality"
    KEY_TAKEAWAYS = "key_takeaways"
    TRADING_SIGNALS = "trading_signals"


@dataclass
class TemplateSection:
    """Template section definition."""
    name: str
    required: bool
    description: str
    example_content: str
    weight: float = 1.0  # Importance weight for this section


class BriefingTemplate:
    """Base briefing template."""

    def __init__(
        self,
        strategy: TradingStrategy,
        sections: List[TemplateSection],
        format_style: str = "structured"
    ):
        """
        Initialize briefing template.

        Args:
            strategy: Trading strategy this template is for
            sections: List of template sections
            format_style: Format style ("structured", "narrative", "concise")
        """
        self.strategy = strategy
        self.sections = sections
        self.format_style = format_style

        logger.info(f"BriefingTemplate initialized for {strategy.value} strategy")

    def get_required_sections(self) -> List[str]:
        """Get list of required section names."""
        return [s.name for s in self.sections if s.required]

    def get_all_sections(self) -> List[str]:
        """Get list of all section names."""
        return [s.name for s in self.sections]

    def validate_briefing(self, briefing: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate briefing against template.

        Args:
            briefing: Briefing to validate

        Returns:
            Validation results
        """
        missing_sections = []
        present_sections = []
        issues = []

        # Check required sections
        for section in self.sections:
            section_name = section.name
            if section_name in briefing:
                present_sections.append(section_name)

                # Check if section has content
                content = briefing[section_name]
                if not content or (isinstance(content, str) and len(content.strip()) < 10):
                    issues.append(f"Section '{section_name}' is empty or too short")
            elif section.required:
                missing_sections.append(section_name)
                issues.append(f"Required section '{section_name}' is missing")

        # Calculate completeness score
        total_required = sum(1 for s in self.sections if s.required)
        present_required = sum(
            1 for s in self.sections
            if s.required and s.name in present_sections
        )
        completeness = (present_required / total_required * 100) if total_required > 0 else 0

        return {
            "valid": len(missing_sections) == 0,
            "completeness_score": completeness,
            "missing_sections": missing_sections,
            "present_sections": present_sections,
            "issues": issues,
            "template_strategy": self.strategy.value
        }

    def format_briefing(self, data: Dict[str, Any]) -> str:
        """
        Format data into briefing according to template.

        Args:
            data: Data to format

        Returns:
            Formatted briefing string
        """
        if self.format_style == "structured":
            return self._format_structured(data)
        elif self.format_style == "narrative":
            return self._format_narrative(data)
        elif self.format_style == "concise":
            return self._format_concise(data)
        else:
            return self._format_structured(data)

    def _format_structured(self, data: Dict[str, Any]) -> str:
        """Format as structured sections with headers."""
        output = []

        for section in self.sections:
            section_name = section.name
            if section_name in data:
                output.append(f"## {section_name.replace('_', ' ').upper()}")
                output.append(str(data[section_name]))
                output.append("")  # Blank line

        return "\n".join(output)

    def _format_narrative(self, data: Dict[str, Any]) -> str:
        """Format as flowing narrative."""
        # TODO: Implement narrative formatting
        return self._format_structured(data)

    def _format_concise(self, data: Dict[str, Any]) -> str:
        """Format as concise bullet points."""
        output = []

        for section in self.sections:
            section_name = section.name
            if section_name in data and data[section_name]:
                output.append(f"• {section_name.replace('_', ' ').title()}: {data[section_name]}")

        return "\n".join(output)


class BriefingTemplateFactory:
    """Factory for creating briefing templates."""

    @staticmethod
    def create_swing_trading_template() -> BriefingTemplate:
        """Create template for swing trading strategy."""
        sections = [
            TemplateSection(
                name="recent_events",
                required=True,
                description="Recent events (last 7 days): earnings, announcements, price movements",
                example_content="Q3 earnings beat expectations by 3.7%, stock rallied 4%",
                weight=1.5
            ),
            TemplateSection(
                name="sentiment_analysis",
                required=True,
                description="Overall sentiment, news sentiment, analyst consensus",
                example_content="Overall: POSITIVE (85% bullish), 28 analysts: BUY consensus",
                weight=1.0
            ),
            TemplateSection(
                name="risk_factors",
                required=True,
                description="Company-specific, sector, and macro risks",
                example_content="European economic slowdown (moderate risk), currency headwinds",
                weight=1.2
            ),
            TemplateSection(
                name="technical_analysis",
                required=True,
                description="Indicators, signals, chart patterns",
                example_content="RSI: 62.5 (neutral), MACD bullish crossover, price above 50-day SMA",
                weight=1.5
            ),
            TemplateSection(
                name="fundamental_metrics",
                required=False,
                description="Valuation, growth, profitability",
                example_content="P/E: 18.5, undervalued vs sector (22.0), ROE: 18.75%",
                weight=0.8
            ),
            TemplateSection(
                name="source_quality",
                required=True,
                description="Credibility ratings, contradictions flagged",
                example_content="High: 7 sources (Reuters, Bloomberg), Medium: 3, Low: 2 excluded",
                weight=0.5
            ),
            TemplateSection(
                name="key_takeaways",
                required=True,
                description="Main actionable insights",
                example_content="1. Strong earnings, 2. Technical setup bullish, 3. Valuation attractive",
                weight=1.0
            ),
            TemplateSection(
                name="trading_signals",
                required=True,
                description="Entry/exit signals, price targets",
                example_content="Bullish signals: 5, Support: €120, Resistance: €130, Target: €135",
                weight=1.3
            )
        ]

        return BriefingTemplate(
            strategy=TradingStrategy.SWING,
            sections=sections,
            format_style="structured"
        )

    @staticmethod
    def create_day_trading_template() -> BriefingTemplate:
        """Create template for day trading strategy."""
        sections = [
            TemplateSection(
                name="pre_market_analysis",
                required=True,
                description="Pre-market price action, news, volume",
                example_content="Pre-market: +2.3%, volume 150% above average",
                weight=1.5
            ),
            TemplateSection(
                name="technical_analysis",
                required=True,
                description="Intraday indicators and levels",
                example_content="VWAP: €125.50, pivot: €124.80, resistance: €127.20",
                weight=2.0
            ),
            TemplateSection(
                name="volatility_metrics",
                required=True,
                description="ATR, IV, expected range",
                example_content="ATR: 2.5 (high), expected range: €123-€128",
                weight=1.5
            ),
            TemplateSection(
                name="catalyst_tracking",
                required=True,
                description="Intraday catalysts, scheduled events",
                example_content="10:00 AM: Earnings call, 2:00 PM: Fed announcement",
                weight=1.3
            ),
            TemplateSection(
                name="risk_management",
                required=True,
                description="Stop loss levels, position sizing",
                example_content="Stop: €123.50 (-1.2%), size: 25% of capital",
                weight=1.0
            )
        ]

        return BriefingTemplate(
            strategy=TradingStrategy.DAY,
            sections=sections,
            format_style="concise"
        )

    @staticmethod
    def create_value_investing_template() -> BriefingTemplate:
        """Create template for value investing strategy."""
        sections = [
            TemplateSection(
                name="fundamental_metrics",
                required=True,
                description="Valuation, financial health, growth",
                example_content="P/E: 12.5 (undervalued), P/B: 1.8, debt/equity: 0.4",
                weight=2.0
            ),
            TemplateSection(
                name="intrinsic_value_analysis",
                required=True,
                description="DCF, comparables, margin of safety",
                example_content="Fair value: €150, current: €125, margin: 20%",
                weight=1.8
            ),
            TemplateSection(
                name="competitive_moat",
                required=True,
                description="Competitive advantages, market position",
                example_content="Strong brand, high switching costs, market leader",
                weight=1.5
            ),
            TemplateSection(
                name="management_quality",
                required=True,
                description="Management track record, capital allocation",
                example_content="CEO 10+ years, consistent FCF growth, shareholder-friendly",
                weight=1.3
            ),
            TemplateSection(
                name="catalyst_identification",
                required=False,
                description="Potential value realization catalysts",
                example_content="Upcoming restructuring, new product launch Q2",
                weight=1.0
            )
        ]

        return BriefingTemplate(
            strategy=TradingStrategy.VALUE,
            sections=sections,
            format_style="structured"
        )

    @staticmethod
    def get_template(strategy: TradingStrategy) -> BriefingTemplate:
        """
        Get template for specific strategy.

        Args:
            strategy: Trading strategy

        Returns:
            Briefing template
        """
        if strategy == TradingStrategy.SWING:
            return BriefingTemplateFactory.create_swing_trading_template()
        elif strategy == TradingStrategy.DAY:
            return BriefingTemplateFactory.create_day_trading_template()
        elif strategy == TradingStrategy.VALUE:
            return BriefingTemplateFactory.create_value_investing_template()
        else:
            # Default to swing trading
            logger.warning(f"No template for {strategy.value}, using swing template")
            return BriefingTemplateFactory.create_swing_trading_template()

    @staticmethod
    def list_available_strategies() -> List[str]:
        """List all available strategy templates."""
        return [strategy.value for strategy in TradingStrategy]


class BriefingTemplateManager:
    """Manages briefing templates and validation."""

    def __init__(self):
        """Initialize template manager."""
        self.templates: Dict[str, BriefingTemplate] = {}
        self._load_default_templates()

    def _load_default_templates(self):
        """Load default templates."""
        self.templates["swing"] = BriefingTemplateFactory.create_swing_trading_template()
        self.templates["day"] = BriefingTemplateFactory.create_day_trading_template()
        self.templates["value"] = BriefingTemplateFactory.create_value_investing_template()

        logger.info(f"Loaded {len(self.templates)} default templates")

    def get_template(self, strategy_name: str) -> Optional[BriefingTemplate]:
        """Get template by strategy name."""
        return self.templates.get(strategy_name.lower())

    def validate_briefing(
        self,
        briefing: Dict[str, Any],
        strategy_name: str = "swing"
    ) -> Dict[str, Any]:
        """
        Validate briefing against template.

        Args:
            briefing: Briefing to validate
            strategy_name: Strategy template to use

        Returns:
            Validation results
        """
        template = self.get_template(strategy_name)
        if not template:
            return {
                "valid": False,
                "error": f"Template '{strategy_name}' not found"
            }

        return template.validate_briefing(briefing)

    def format_briefing(
        self,
        data: Dict[str, Any],
        strategy_name: str = "swing"
    ) -> str:
        """
        Format data into briefing using template.

        Args:
            data: Data to format
            strategy_name: Strategy template to use

        Returns:
            Formatted briefing
        """
        template = self.get_template(strategy_name)
        if not template:
            logger.warning(f"Template '{strategy_name}' not found, using swing")
            template = self.templates["swing"]

        return template.format_briefing(data)

    def add_custom_template(self, name: str, template: BriefingTemplate):
        """Add custom template."""
        self.templates[name.lower()] = template
        logger.info(f"Added custom template: {name}")

    def list_templates(self) -> List[str]:
        """List all available template names."""
        return list(self.templates.keys())
