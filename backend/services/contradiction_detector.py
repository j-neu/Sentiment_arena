"""
Contradiction Detection Service

Identifies conflicting information from different sources in research briefings.
Flags uncertainties, data gaps, and requires higher confidence when conflicts exist.
"""

from typing import Dict, Any, List, Tuple
import json
from backend.logger import get_logger
from backend.services.openrouter_client import OpenRouterClient
from backend.services.research_model_mapper import ResearchModelMapper

logger = get_logger(__name__)


class ContradictionDetector:
    """
    Detects contradictions and conflicts in research data.

    Uses LLM to analyze multiple sources and identify:
    - Direct contradictions (X says up, Y says down)
    - Inconsistent data points
    - Conflicting sentiment
    - Uncertainty indicators
    """

    def __init__(self, openrouter_client: OpenRouterClient, trading_model: str):
        """
        Initialize contradiction detector.

        Args:
            openrouter_client: OpenRouter API client
            trading_model: Trading model identifier
        """
        self.client = openrouter_client
        self.trading_model = trading_model
        self.research_model = ResearchModelMapper.get_research_model(trading_model)

        logger.info(f"ContradictionDetector initialized: research_model={self.research_model}")

    def detect_contradictions(
        self,
        briefing: Dict[str, Any],
        source_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Detect contradictions in research briefing.

        Args:
            briefing: Synthesized research briefing
            source_data: Original source data

        Returns:
            Dictionary with contradiction analysis
        """
        logger.info("Detecting contradictions in briefing")

        # Build contradiction detection prompt
        prompt = self._build_detection_prompt(briefing, source_data)

        try:
            # Call research LLM for detection
            response = self.client.get_completion_text(
                model=self.research_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a fact-checker analyzing financial research for contradictions and conflicts."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,  # Very low temperature for consistent detection
                max_tokens=1500
            )

            # Parse contradiction results
            analysis = self._parse_contradictions(response)

            logger.info(
                f"Found {len(analysis.get('contradictions', []))} contradictions, "
                f"severity: {analysis.get('severity', 'UNKNOWN')}"
            )

            return analysis

        except Exception as e:
            logger.error(f"Error detecting contradictions: {e}")
            return self._fallback_analysis()

    def _build_detection_prompt(
        self,
        briefing: Dict[str, Any],
        source_data: List[Dict[str, Any]]
    ) -> str:
        """Build prompt for contradiction detection."""
        # Format briefing
        briefing_text = json.dumps(briefing, indent=2)

        # Format sources
        sources_text = ""
        for i, source in enumerate(source_data, 1):
            sources_text += f"[SOURCE {i}]\n"
            sources_text += f"Title: {source.get('title', 'N/A')}\n"
            sources_text += f"Content: {source.get('snippet', 'N/A')}\n"
            sources_text += f"URL: {source.get('url', 'N/A')}\n\n"

        prompt = f"""Analyze the following research briefing and source data for contradictions,
conflicts, and inconsistencies.

=== SOURCE DATA ===
{sources_text}

=== SYNTHESIZED BRIEFING ===
{briefing_text}

=== YOUR TASK ===
Identify any contradictions or conflicts in:

1. **Factual Contradictions**
   - Different sources stating opposite facts
   - Inconsistent numbers, dates, or events
   - Conflicting assessments (bullish vs bearish)

2. **Sentiment Conflicts**
   - Sources with wildly different sentiment
   - Positive outlook vs negative outlook
   - Mixed signals from different analysts

3. **Data Inconsistencies**
   - Numbers that don't match
   - Timeline discrepancies
   - Conflicting technical indicators

4. **Uncertainty Indicators**
   - Speculative language ("might", "could", "may")
   - Lack of consensus
   - Missing critical information

For each contradiction found:
- Describe the conflict
- Identify which sources conflict
- Rate severity (LOW/MEDIUM/HIGH)
- Suggest how to resolve it

Return your analysis as JSON:
{{
    "contradictions": [
        {{
            "type": "factual|sentiment|data|uncertainty",
            "description": "description of contradiction",
            "sources_involved": ["source 1", "source 2"],
            "severity": "LOW|MEDIUM|HIGH",
            "resolution_suggestion": "how to resolve",
            "confidence_impact": "how this affects confidence"
        }}
    ],
    "data_gaps": [
        "missing information 1",
        "missing information 2"
    ],
    "uncertainty_level": "LOW|MEDIUM|HIGH",
    "severity": "LOW|MEDIUM|HIGH",
    "trading_recommendation": "PROCEED|CAUTION|HOLD",
    "confidence_adjustment": "percentage to reduce confidence (-10% to -50%)",
    "summary": "brief summary of findings"
}}"""

        return prompt

    def _parse_contradictions(self, response: str) -> Dict[str, Any]:
        """Parse contradiction detection response."""
        try:
            # Remove markdown code blocks
            response = response.strip()
            if response.startswith("```"):
                lines = response.split("\n")
                json_lines = []
                in_code_block = False
                for line in lines:
                    if line.strip().startswith("```"):
                        in_code_block = not in_code_block
                        continue
                    if in_code_block:
                        json_lines.append(line)
                response = "\n".join(json_lines)

            # Parse JSON
            analysis = json.loads(response)

            # Validate and set defaults
            analysis.setdefault("contradictions", [])
            analysis.setdefault("data_gaps", [])
            analysis.setdefault("uncertainty_level", "MEDIUM")
            analysis.setdefault("severity", "MEDIUM")
            analysis.setdefault("trading_recommendation", "CAUTION")
            analysis.setdefault("confidence_adjustment", "-20%")
            analysis.setdefault("summary", "No contradictions detected")

            return analysis

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse contradiction detection: {e}")
            return self._fallback_analysis()

    def _fallback_analysis(self) -> Dict[str, Any]:
        """Fallback analysis if detection fails."""
        return {
            "contradictions": [],
            "data_gaps": ["Contradiction detection failed - manual review recommended"],
            "uncertainty_level": "HIGH",
            "severity": "MEDIUM",
            "trading_recommendation": "CAUTION",
            "confidence_adjustment": "-30%",
            "summary": "Contradiction detection failed"
        }

    def calculate_confidence_penalty(
        self,
        analysis: Dict[str, Any],
        base_confidence: float = 1.0
    ) -> Tuple[float, str]:
        """
        Calculate confidence penalty based on contradictions.

        Args:
            analysis: Contradiction analysis results
            base_confidence: Base confidence level (0.0-1.0)

        Returns:
            Tuple of (adjusted_confidence, reason)
        """
        contradictions = analysis.get("contradictions", [])
        severity = analysis.get("severity", "LOW")

        # Calculate penalty based on severity
        if severity == "HIGH":
            penalty = 0.40  # -40%
            reason = "High-severity contradictions detected"
        elif severity == "MEDIUM":
            penalty = 0.25  # -25%
            reason = "Medium-severity contradictions detected"
        elif severity == "LOW":
            penalty = 0.10  # -10%
            reason = "Low-severity contradictions detected"
        else:
            penalty = 0.0
            reason = "No contradictions detected"

        # Additional penalty for multiple contradictions
        if len(contradictions) > 3:
            penalty += 0.10
            reason += f" ({len(contradictions)} contradictions found)"

        # Cap penalty at 50%
        penalty = min(penalty, 0.50)

        # Calculate adjusted confidence
        adjusted_confidence = max(base_confidence - penalty, 0.0)

        return adjusted_confidence, reason

    def format_contradiction_report(
        self,
        analysis: Dict[str, Any]
    ) -> str:
        """
        Format contradiction analysis as readable report.

        Args:
            analysis: Contradiction analysis results

        Returns:
            Formatted report string
        """
        contradictions = analysis.get("contradictions", [])
        severity = analysis.get("severity", "UNKNOWN")
        recommendation = analysis.get("trading_recommendation", "UNKNOWN")

        report = f"""
╔══════════════════════════════════════════════════════════╗
║              CONTRADICTION ANALYSIS REPORT              ║
╚══════════════════════════════════════════════════════════╝

Overall Severity: {severity}
Trading Recommendation: {recommendation}
Confidence Adjustment: {analysis.get('confidence_adjustment', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

        # Summary
        summary = analysis.get("summary", "No summary available")
        report += f"\nSUMMARY:\n{summary}\n"

        # Contradictions
        if contradictions:
            report += f"\n⚠️  CONTRADICTIONS FOUND ({len(contradictions)}):\n"
            for i, contradiction in enumerate(contradictions, 1):
                report += f"\n{i}. {contradiction.get('type', 'unknown').upper()} - {contradiction.get('severity', 'UNKNOWN')}\n"
                report += f"   Description: {contradiction.get('description', 'N/A')}\n"
                report += f"   Sources: {', '.join(contradiction.get('sources_involved', []))}\n"
                report += f"   Resolution: {contradiction.get('resolution_suggestion', 'N/A')}\n"
                report += f"   Impact: {contradiction.get('confidence_impact', 'N/A')}\n"
        else:
            report += "\n✅ No contradictions detected\n"

        # Data gaps
        data_gaps = analysis.get("data_gaps", [])
        if data_gaps:
            report += f"\n📋 DATA GAPS ({len(data_gaps)}):\n"
            for gap in data_gaps:
                report += f"  • {gap}\n"

        # Uncertainty level
        uncertainty = analysis.get("uncertainty_level", "UNKNOWN")
        report += f"\n🎲 UNCERTAINTY LEVEL: {uncertainty}\n"

        report += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

        return report

    def should_require_manual_review(self, analysis: Dict[str, Any]) -> bool:
        """
        Determine if manual review is required due to contradictions.

        Args:
            analysis: Contradiction analysis results

        Returns:
            True if manual review recommended
        """
        severity = analysis.get("severity", "LOW")
        contradictions = analysis.get("contradictions", [])
        recommendation = analysis.get("trading_recommendation", "PROCEED")

        # Require review if:
        # - High severity
        # - More than 3 contradictions
        # - Recommendation is HOLD
        return (
            severity == "HIGH" or
            len(contradictions) > 3 or
            recommendation == "HOLD"
        )
