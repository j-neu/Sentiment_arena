"""
Quality Verification Service

LLM-powered quality assurance for research briefings:
- Self-review of generated briefings
- Accuracy verification against source data
- Completeness checking
- Bias detection
- Quality scoring (0-100)
"""

from typing import Dict, Any, List
import json
from datetime import datetime

from backend.logger import get_logger
from backend.services.openrouter_client import OpenRouterClient
from backend.services.research_model_mapper import ResearchModelMapper

logger = get_logger(__name__)


class QualityVerifier:
    """
    Verifies quality of research briefings using LLM self-review.

    Uses the same cheaper model to verify its own synthesis work.
    """

    def __init__(self, openrouter_client: OpenRouterClient, trading_model: str):
        """
        Initialize quality verifier.

        Args:
            openrouter_client: OpenRouter API client
            trading_model: Trading model identifier
        """
        self.client = openrouter_client
        self.trading_model = trading_model
        self.research_model = ResearchModelMapper.get_research_model(trading_model)

        logger.info(
            f"QualityVerifier initialized: research_model={self.research_model}"
        )

    def verify_briefing(
        self,
        briefing: Dict[str, Any],
        source_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Verify quality of a research briefing.

        Args:
            briefing: The synthesized briefing to verify
            source_data: Original source data used for synthesis

        Returns:
            Dictionary with quality assessment and score
        """
        logger.info("Verifying briefing quality")

        # Build verification prompt
        prompt = self._build_verification_prompt(briefing, source_data)

        try:
            # Call research LLM for verification
            response = self.client.get_completion_text(
                model=self.research_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a quality assurance analyst reviewing financial research briefings."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,  # Low temperature for consistent verification
                max_tokens=1000
            )

            # Parse verification results
            verification = self._parse_verification(response)

            logger.info(f"Quality score: {verification.get('quality_score', 0)}/100")
            return verification

        except Exception as e:
            logger.error(f"Error verifying briefing quality: {e}")
            return self._fallback_verification()

    def _build_verification_prompt(
        self,
        briefing: Dict[str, Any],
        source_data: List[Dict[str, Any]]
    ) -> str:
        """Build prompt for quality verification."""
        # Format briefing
        briefing_text = json.dumps(briefing, indent=2)

        # Format source data
        sources_text = ""
        for i, source in enumerate(source_data, 1):
            sources_text += f"[{i}] {source.get('title', 'N/A')}\n"
            sources_text += f"    {source.get('snippet', 'N/A')}\n"
            sources_text += f"    Source: {source.get('url', 'N/A')}\n\n"

        prompt = f"""Review the following research briefing for quality, accuracy, and completeness.

=== ORIGINAL SOURCE DATA ===
{sources_text}

=== SYNTHESIZED BRIEFING ===
{briefing_text}

=== VERIFICATION CRITERIA ===

1. **Accuracy** (0-25 points)
   - Does the briefing accurately represent the source data?
   - Are there any factual errors or misrepresentations?
   - Are numbers and dates correct?

2. **Completeness** (0-25 points)
   - Are all required sections present and filled?
   - Is important information from sources included?
   - Are there significant omissions?

3. **Objectivity** (0-25 points)
   - Is the language objective and professional?
   - Is there bias or promotional language?
   - Are both positive and negative aspects covered?

4. **Usefulness** (0-25 points)
   - Will this briefing help make informed trading decisions?
   - Are the key takeaways actionable?
   - Is the information relevant and current?

=== YOUR TASK ===
Evaluate the briefing on each criterion and provide:

1. Score for each criterion (0-25)
2. Total quality score (0-100)
3. List of specific issues found (if any)
4. List of strengths
5. Recommendations for improvement
6. Overall assessment (PASS/FAIL) - PASS if score >= 60

Return your evaluation as a JSON object:
{{
    "accuracy_score": 0-25,
    "completeness_score": 0-25,
    "objectivity_score": 0-25,
    "usefulness_score": 0-25,
    "quality_score": 0-100,
    "issues_found": ["issue 1", "issue 2", ...],
    "strengths": ["strength 1", "strength 2", ...],
    "recommendations": ["recommendation 1", ...],
    "overall_assessment": "PASS|FAIL",
    "confidence_in_verification": "HIGH|MEDIUM|LOW"
}}"""

        return prompt

    def _parse_verification(self, response: str) -> Dict[str, Any]:
        """Parse verification response from LLM."""
        try:
            # Remove markdown code blocks if present
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
            verification = json.loads(response)

            # Validate and set defaults
            verification.setdefault("accuracy_score", 0)
            verification.setdefault("completeness_score", 0)
            verification.setdefault("objectivity_score", 0)
            verification.setdefault("usefulness_score", 0)
            verification.setdefault("quality_score", 0)
            verification.setdefault("issues_found", [])
            verification.setdefault("strengths", [])
            verification.setdefault("recommendations", [])
            verification.setdefault("overall_assessment", "FAIL")
            verification.setdefault("confidence_in_verification", "MEDIUM")

            # Calculate total if not provided
            if verification["quality_score"] == 0:
                verification["quality_score"] = (
                    verification["accuracy_score"] +
                    verification["completeness_score"] +
                    verification["objectivity_score"] +
                    verification["usefulness_score"]
                )

            # Add timestamp
            verification["verified_at"] = datetime.now().isoformat()
            verification["verified_by"] = self.research_model

            return verification

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse verification as JSON: {e}")
            return self._fallback_verification()

    def _fallback_verification(self) -> Dict[str, Any]:
        """Return fallback verification if parsing fails."""
        return {
            "accuracy_score": 15,
            "completeness_score": 15,
            "objectivity_score": 15,
            "usefulness_score": 15,
            "quality_score": 60,
            "issues_found": ["Verification process failed - manual review recommended"],
            "strengths": [],
            "recommendations": ["Manual verification recommended"],
            "overall_assessment": "PASS",
            "confidence_in_verification": "LOW",
            "verified_at": datetime.now().isoformat(),
            "verified_by": self.research_model
        }

    def create_quality_report(
        self,
        briefing: Dict[str, Any],
        verification: Dict[str, Any]
    ) -> str:
        """
        Create a formatted quality report.

        Args:
            briefing: The briefing that was verified
            verification: The verification results

        Returns:
            Formatted quality report string
        """
        symbol = briefing.get("metadata", {}).get("symbol", "Unknown")
        quality_score = verification.get("quality_score", 0)
        assessment = verification.get("overall_assessment", "UNKNOWN")

        # Quality tier
        if quality_score >= 80:
            tier = "EXCELLENT"
        elif quality_score >= 70:
            tier = "GOOD"
        elif quality_score >= 60:
            tier = "ACCEPTABLE"
        else:
            tier = "POOR"

        report = f"""
╔══════════════════════════════════════════════════════════╗
║           RESEARCH QUALITY REPORT - {symbol}           ║
╚══════════════════════════════════════════════════════════╝

Overall Score: {quality_score}/100 ({tier})
Assessment: {assessment}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DETAILED SCORES:
  • Accuracy:     {verification.get('accuracy_score', 0)}/25
  • Completeness: {verification.get('completeness_score', 0)}/25
  • Objectivity:  {verification.get('objectivity_score', 0)}/25
  • Usefulness:   {verification.get('usefulness_score', 0)}/25

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

        # Strengths
        strengths = verification.get("strengths", [])
        if strengths:
            report += "\n✅ STRENGTHS:\n"
            for strength in strengths:
                report += f"  • {strength}\n"

        # Issues
        issues = verification.get("issues_found", [])
        if issues:
            report += "\n⚠️  ISSUES FOUND:\n"
            for issue in issues:
                report += f"  • {issue}\n"

        # Recommendations
        recommendations = verification.get("recommendations", [])
        if recommendations:
            report += "\n💡 RECOMMENDATIONS:\n"
            for rec in recommendations:
                report += f"  • {rec}\n"

        report += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        report += f"Verified by: {verification.get('verified_by', 'Unknown')}\n"
        report += f"Confidence: {verification.get('confidence_in_verification', 'UNKNOWN')}\n"
        report += f"Timestamp: {verification.get('verified_at', 'Unknown')}\n"

        return report

    def should_use_briefing(self, verification: Dict[str, Any]) -> bool:
        """
        Determine if briefing is good enough to use for trading.

        Args:
            verification: Verification results

        Returns:
            True if briefing should be used, False otherwise
        """
        quality_score = verification.get("quality_score", 0)
        assessment = verification.get("overall_assessment", "FAIL")

        # Require at least 60/100 score and PASS assessment
        return quality_score >= 60 and assessment == "PASS"

    def get_quality_tier(self, quality_score: int) -> str:
        """Get quality tier label for a score."""
        if quality_score >= 80:
            return "EXCELLENT"
        elif quality_score >= 70:
            return "GOOD"
        elif quality_score >= 60:
            return "ACCEPTABLE"
        elif quality_score >= 40:
            return "POOR"
        else:
            return "VERY_POOR"

    def get_model_info(self) -> Dict[str, str]:
        """Get information about models being used."""
        return {
            "trading_model": self.trading_model,
            "research_model": self.research_model,
            "company": ResearchModelMapper.get_model_company(self.trading_model)
        }
