"""
Quality Assurance Orchestrator

Combines all quality assurance components from Phase 3.5.4:
- Quality Verifier (self-review, scoring, completeness)
- Contradiction Detector (conflict identification, data gaps)
- Briefing Templates (standardized formats, validation)

Provides comprehensive quality control for research briefings.
"""

from typing import Dict, Any, List, Optional
import time
from backend.logger import get_logger
from backend.services.quality_verifier import QualityVerifier
from backend.services.contradiction_detector import ContradictionDetector
from backend.services.briefing_templates import (
    BriefingTemplateManager,
    TradingStrategy
)
from backend.services.openrouter_client import OpenRouterClient

logger = get_logger(__name__)


class QualityAssuranceOrchestrator:
    """
    Orchestrates all quality assurance checks for research briefings.

    Runs:
    1. Template validation (structure, required sections)
    2. Quality verification (accuracy, completeness, bias)
    3. Contradiction detection (conflicts, uncertainties)
    4. Final recommendation (use/reject briefing)
    """

    def __init__(
        self,
        openrouter_client: OpenRouterClient,
        trading_model: str,
        default_strategy: str = "swing"
    ):
        """
        Initialize quality assurance orchestrator.

        Args:
            openrouter_client: OpenRouter API client
            trading_model: Trading model identifier
            default_strategy: Default trading strategy for templates
        """
        self.client = openrouter_client
        self.trading_model = trading_model
        self.default_strategy = default_strategy

        # Initialize components
        self.quality_verifier = QualityVerifier(openrouter_client, trading_model)
        self.contradiction_detector = ContradictionDetector(openrouter_client, trading_model)
        self.template_manager = BriefingTemplateManager()

        logger.info(f"QualityAssuranceOrchestrator initialized for {trading_model}")

    def run_comprehensive_qa(
        self,
        briefing: Dict[str, Any],
        source_data: List[Dict[str, Any]],
        strategy: Optional[str] = None,
        skip_contradiction_detection: bool = False
    ) -> Dict[str, Any]:
        """
        Run comprehensive quality assurance on briefing.

        Args:
            briefing: Research briefing to verify
            source_data: Original source data
            strategy: Trading strategy (default: self.default_strategy)
            skip_contradiction_detection: Skip contradiction detection (faster)

        Returns:
            Complete QA results with recommendation
        """
        logger.info("Running comprehensive QA on briefing")
        start_time = time.time()

        strategy = strategy or self.default_strategy

        results = {
            "briefing_symbol": briefing.get("metadata", {}).get("symbol", "Unknown"),
            "strategy": strategy,
            "qa_stages": {},
            "timing": {},
            "final_recommendation": None,
            "overall_score": 0,
            "should_use_briefing": False
        }

        # Stage 1: Template Validation
        stage1_start = time.time()
        try:
            logger.info("[QA Stage 1/3] Validating briefing structure...")
            template_validation = self.template_manager.validate_briefing(briefing, strategy)
            results["qa_stages"]["template_validation"] = template_validation
            results["timing"]["template_validation"] = time.time() - stage1_start

            logger.info(
                f"Template validation: {template_validation['completeness_score']:.1f}% complete"
            )
        except Exception as e:
            logger.error(f"Template validation failed: {e}")
            results["qa_stages"]["template_validation"] = {
                "valid": False,
                "error": str(e)
            }
            results["timing"]["template_validation"] = time.time() - stage1_start

        # Stage 2: Quality Verification
        stage2_start = time.time()
        try:
            logger.info("[QA Stage 2/3] Running quality verification...")
            quality_verification = self.quality_verifier.verify_briefing(briefing, source_data)
            results["qa_stages"]["quality_verification"] = quality_verification
            results["timing"]["quality_verification"] = time.time() - stage2_start

            logger.info(
                f"Quality score: {quality_verification['quality_score']}/100 "
                f"({quality_verification['overall_assessment']})"
            )
        except Exception as e:
            logger.error(f"Quality verification failed: {e}")
            results["qa_stages"]["quality_verification"] = {
                "quality_score": 50,
                "overall_assessment": "FAIL",
                "error": str(e)
            }
            results["timing"]["quality_verification"] = time.time() - stage2_start

        # Stage 3: Contradiction Detection (optional, slower)
        if not skip_contradiction_detection:
            stage3_start = time.time()
            try:
                logger.info("[QA Stage 3/3] Detecting contradictions...")
                contradiction_analysis = self.contradiction_detector.detect_contradictions(
                    briefing, source_data
                )
                results["qa_stages"]["contradiction_detection"] = contradiction_analysis
                results["timing"]["contradiction_detection"] = time.time() - stage3_start

                logger.info(
                    f"Contradictions: {len(contradiction_analysis.get('contradictions', []))}, "
                    f"severity: {contradiction_analysis.get('severity', 'UNKNOWN')}"
                )
            except Exception as e:
                logger.error(f"Contradiction detection failed: {e}")
                results["qa_stages"]["contradiction_detection"] = {
                    "contradictions": [],
                    "severity": "UNKNOWN",
                    "error": str(e)
                }
                results["timing"]["contradiction_detection"] = time.time() - stage3_start
        else:
            results["qa_stages"]["contradiction_detection"] = {
                "status": "skipped"
            }
            logger.info("[QA Stage 3/3] Contradiction detection skipped")

        # Calculate overall score and recommendation
        results["final_recommendation"] = self._generate_recommendation(results)
        results["overall_score"] = self._calculate_overall_score(results)
        results["should_use_briefing"] = results["final_recommendation"]["use_briefing"]

        # Total time
        total_time = time.time() - start_time
        results["timing"]["total"] = total_time

        logger.info(
            f"QA complete: Score {results['overall_score']}/100, "
            f"Recommendation: {'USE' if results['should_use_briefing'] else 'REJECT'}, "
            f"Time: {total_time:.2f}s"
        )

        return results

    def _calculate_overall_score(self, results: Dict[str, Any]) -> float:
        """Calculate overall QA score (0-100)."""
        weights = {
            "template_validation": 0.20,
            "quality_verification": 0.50,
            "contradiction_detection": 0.30
        }

        total_score = 0.0

        # Template validation score
        template = results["qa_stages"].get("template_validation", {})
        if template.get("valid"):
            template_score = template.get("completeness_score", 0)
            total_score += template_score * weights["template_validation"]

        # Quality verification score
        quality = results["qa_stages"].get("quality_verification", {})
        quality_score = quality.get("quality_score", 0)
        total_score += quality_score * weights["quality_verification"]

        # Contradiction detection (penalty system)
        contradictions = results["qa_stages"].get("contradiction_detection", {})
        if contradictions.get("status") != "skipped":
            severity = contradictions.get("severity", "LOW")
            num_contradictions = len(contradictions.get("contradictions", []))

            # Base contradiction score
            if severity == "LOW" and num_contradictions <= 1:
                contradiction_score = 90
            elif severity == "LOW":
                contradiction_score = 75
            elif severity == "MEDIUM":
                contradiction_score = 60
            else:  # HIGH
                contradiction_score = 40

            total_score += contradiction_score * weights["contradiction_detection"]
        else:
            # If skipped, assume no contradictions (full score)
            total_score += 100 * weights["contradiction_detection"]

        return round(total_score, 1)

    def _generate_recommendation(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate final recommendation based on QA results."""
        issues = []
        warnings = []

        # Check template validation
        template = results["qa_stages"].get("template_validation", {})
        if not template.get("valid", False):
            issues.append("Briefing structure is invalid")
        if template.get("completeness_score", 0) < 70:
            warnings.append(f"Briefing only {template.get('completeness_score', 0):.0f}% complete")

        # Check quality verification
        quality = results["qa_stages"].get("quality_verification", {})
        quality_score = quality.get("quality_score", 0)
        assessment = quality.get("overall_assessment", "FAIL")

        if quality_score < 60:
            issues.append(f"Quality score too low ({quality_score}/100)")
        elif quality_score < 70:
            warnings.append(f"Quality score is marginal ({quality_score}/100)")

        if assessment == "FAIL":
            issues.append("Quality assessment: FAIL")

        # Check contradictions
        contradictions = results["qa_stages"].get("contradiction_detection", {})
        if contradictions.get("status") != "skipped":
            severity = contradictions.get("severity", "LOW")
            num_contradictions = len(contradictions.get("contradictions", []))

            if severity == "HIGH":
                issues.append(f"High-severity contradictions detected ({num_contradictions})")
            elif severity == "MEDIUM" and num_contradictions > 2:
                warnings.append(f"Medium contradictions detected ({num_contradictions})")
            elif num_contradictions > 5:
                warnings.append(f"Many contradictions detected ({num_contradictions})")

            # Check if manual review recommended
            if self.contradiction_detector.should_require_manual_review(contradictions):
                warnings.append("Manual review recommended due to contradictions")

        # Determine recommendation
        use_briefing = len(issues) == 0 and quality_score >= 60

        recommendation = {
            "use_briefing": use_briefing,
            "confidence": "HIGH" if use_briefing and len(warnings) == 0 else "MEDIUM" if use_briefing else "LOW",
            "issues": issues,
            "warnings": warnings,
            "action": "USE" if use_briefing else "REJECT",
            "reason": self._generate_reason(use_briefing, issues, warnings)
        }

        # Adjust confidence based on contradictions
        if contradictions.get("status") != "skipped" and use_briefing:
            base_confidence = 1.0 if recommendation["confidence"] == "HIGH" else 0.7
            adjusted_confidence, reason = self.contradiction_detector.calculate_confidence_penalty(
                contradictions, base_confidence
            )
            if adjusted_confidence < 0.6:
                recommendation["confidence"] = "MEDIUM"
                recommendation["warnings"].append(reason)
            elif adjusted_confidence < 0.4:
                recommendation["confidence"] = "LOW"
                recommendation["use_briefing"] = False
                recommendation["action"] = "REJECT"
                recommendation["issues"].append(reason)

        return recommendation

    def _generate_reason(
        self,
        use_briefing: bool,
        issues: List[str],
        warnings: List[str]
    ) -> str:
        """Generate human-readable reason for recommendation."""
        if use_briefing:
            if len(warnings) == 0:
                return "Briefing passes all quality checks"
            else:
                return f"Briefing is acceptable but has {len(warnings)} warning(s)"
        else:
            return f"Briefing fails quality checks: {len(issues)} critical issue(s)"

    def format_qa_report(self, results: Dict[str, Any]) -> str:
        """
        Format QA results as comprehensive report.

        Args:
            results: QA results from run_comprehensive_qa()

        Returns:
            Formatted report string
        """
        symbol = results.get("briefing_symbol", "Unknown")
        score = results.get("overall_score", 0)
        recommendation = results.get("final_recommendation", {})
        action = recommendation.get("action", "UNKNOWN")

        report = f"""
╔══════════════════════════════════════════════════════════════════╗
║         QUALITY ASSURANCE REPORT - {symbol:^10}                  ║
╚══════════════════════════════════════════════════════════════════╝

Overall QA Score: {score}/100
Recommendation: {action}
Confidence: {recommendation.get('confidence', 'UNKNOWN')}

{recommendation.get('reason', 'No reason provided')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

        # Stage results
        stages = results.get("qa_stages", {})
        timing = results.get("timing", {})

        # Template validation
        if "template_validation" in stages:
            template = stages["template_validation"]
            report += f"\n📋 TEMPLATE VALIDATION ({timing.get('template_validation', 0):.2f}s)\n"
            report += f"   Status: {'✅ VALID' if template.get('valid') else '❌ INVALID'}\n"
            report += f"   Completeness: {template.get('completeness_score', 0):.1f}%\n"

            missing = template.get("missing_sections", [])
            if missing:
                report += f"   Missing: {', '.join(missing)}\n"

        # Quality verification
        if "quality_verification" in stages:
            quality = stages["quality_verification"]
            report += f"\n⭐ QUALITY VERIFICATION ({timing.get('quality_verification', 0):.2f}s)\n"
            report += f"   Score: {quality.get('quality_score', 0)}/100\n"
            report += f"   Assessment: {quality.get('overall_assessment', 'UNKNOWN')}\n"
            report += f"   • Accuracy: {quality.get('accuracy_score', 0)}/25\n"
            report += f"   • Completeness: {quality.get('completeness_score', 0)}/25\n"
            report += f"   • Objectivity: {quality.get('objectivity_score', 0)}/25\n"
            report += f"   • Usefulness: {quality.get('usefulness_score', 0)}/25\n"

        # Contradiction detection
        if "contradiction_detection" in stages:
            contradictions = stages["contradiction_detection"]
            if contradictions.get("status") != "skipped":
                report += f"\n⚠️  CONTRADICTION DETECTION ({timing.get('contradiction_detection', 0):.2f}s)\n"
                num_contradictions = len(contradictions.get("contradictions", []))
                report += f"   Found: {num_contradictions} contradiction(s)\n"
                report += f"   Severity: {contradictions.get('severity', 'UNKNOWN')}\n"
                report += f"   Recommendation: {contradictions.get('trading_recommendation', 'UNKNOWN')}\n"

        # Issues and warnings
        issues = recommendation.get("issues", [])
        warnings = recommendation.get("warnings", [])

        if issues:
            report += f"\n❌ CRITICAL ISSUES ({len(issues)}):\n"
            for issue in issues:
                report += f"   • {issue}\n"

        if warnings:
            report += f"\n⚠️  WARNINGS ({len(warnings)}):\n"
            for warning in warnings:
                report += f"   • {warning}\n"

        # Timing summary
        report += f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        report += f"Total QA Time: {timing.get('total', 0):.2f}s\n"
        report += f"Strategy: {results.get('strategy', 'unknown')}\n"

        return report

    def get_component_info(self) -> Dict[str, Any]:
        """Get information about QA components."""
        return {
            "quality_verifier": self.quality_verifier.get_model_info(),
            "contradiction_detector": {
                "trading_model": self.trading_model,
                "enabled": True
            },
            "template_manager": {
                "available_templates": self.template_manager.list_templates(),
                "default_strategy": self.default_strategy
            }
        }
