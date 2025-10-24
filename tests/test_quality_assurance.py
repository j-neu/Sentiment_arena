"""
Test Quality Assurance Components (Phase 3.5.4)

Tests:
- Contradiction Detector
- Briefing Templates
- Quality Assurance Orchestrator
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from backend.services.contradiction_detector import ContradictionDetector
from backend.services.briefing_templates import (
    BriefingTemplateManager,
    BriefingTemplateFactory,
    TradingStrategy,
    TemplateSection
)
from backend.services.quality_assurance_orchestrator import QualityAssuranceOrchestrator


class TestContradictionDetector:
    """Test contradiction detection service."""

    @pytest.fixture
    def mock_client(self):
        """Mock OpenRouter client."""
        return Mock()

    @pytest.fixture
    def detector(self, mock_client):
        """Create contradiction detector."""
        return ContradictionDetector(mock_client, "openai/gpt-3.5-turbo")

    def test_initialization(self, detector):
        """Test detector initialization."""
        assert detector is not None
        assert detector.trading_model == "openai/gpt-3.5-turbo"
        assert detector.research_model is not None

    def test_detect_contradictions_success(self, detector, mock_client):
        """Test successful contradiction detection."""
        # Mock LLM response
        mock_response = '''{
            "contradictions": [
                {
                    "type": "sentiment",
                    "description": "Source 1 says bullish, Source 2 says bearish",
                    "sources_involved": ["Reuters", "Bloomberg"],
                    "severity": "MEDIUM",
                    "resolution_suggestion": "Consider latest source",
                    "confidence_impact": "Reduces confidence by 20%"
                }
            ],
            "data_gaps": ["Missing earnings data"],
            "uncertainty_level": "MEDIUM",
            "severity": "MEDIUM",
            "trading_recommendation": "CAUTION",
            "confidence_adjustment": "-20%",
            "summary": "One sentiment contradiction detected"
        }'''

        mock_client.get_completion_text.return_value = mock_response

        briefing = {"metadata": {"symbol": "SAP.DE"}, "content": "test"}
        sources = [{"title": "Test", "snippet": "content"}]

        result = detector.detect_contradictions(briefing, sources)

        assert result["severity"] == "MEDIUM"
        assert len(result["contradictions"]) == 1
        assert result["contradictions"][0]["type"] == "sentiment"
        assert result["trading_recommendation"] == "CAUTION"

    def test_calculate_confidence_penalty(self, detector):
        """Test confidence penalty calculation."""
        # High severity
        analysis = {
            "contradictions": [{"severity": "HIGH"}],
            "severity": "HIGH"
        }
        confidence, reason = detector.calculate_confidence_penalty(analysis, 1.0)
        assert confidence < 0.7  # At least 30% penalty
        assert "High-severity" in reason

        # Medium severity
        analysis["severity"] = "MEDIUM"
        confidence, reason = detector.calculate_confidence_penalty(analysis, 1.0)
        assert confidence < 0.8  # At least 20% penalty

        # No contradictions
        analysis = {"contradictions": [], "severity": "LOW"}
        confidence, reason = detector.calculate_confidence_penalty(analysis, 1.0)
        assert confidence >= 0.9

    def test_should_require_manual_review(self, detector):
        """Test manual review requirement detection."""
        # High severity requires review
        analysis = {"severity": "HIGH", "contradictions": [], "trading_recommendation": "PROCEED"}
        assert detector.should_require_manual_review(analysis) is True

        # Many contradictions require review
        analysis = {
            "severity": "LOW",
            "contradictions": [{}] * 5,
            "trading_recommendation": "PROCEED"
        }
        assert detector.should_require_manual_review(analysis) is True

        # HOLD recommendation requires review
        analysis = {"severity": "LOW", "contradictions": [], "trading_recommendation": "HOLD"}
        assert detector.should_require_manual_review(analysis) is True

        # Low severity, few contradictions, no review needed
        analysis = {"severity": "LOW", "contradictions": [{}], "trading_recommendation": "PROCEED"}
        assert detector.should_require_manual_review(analysis) is False

    def test_format_contradiction_report(self, detector):
        """Test contradiction report formatting."""
        analysis = {
            "contradictions": [
                {
                    "type": "factual",
                    "description": "Test contradiction",
                    "sources_involved": ["Source 1"],
                    "severity": "HIGH",
                    "resolution_suggestion": "Use latest",
                    "confidence_impact": "High"
                }
            ],
            "data_gaps": ["Missing data"],
            "severity": "HIGH",
            "trading_recommendation": "HOLD",
            "confidence_adjustment": "-40%",
            "summary": "Test summary"
        }

        report = detector.format_contradiction_report(analysis)

        assert "CONTRADICTION ANALYSIS REPORT" in report
        assert "HIGH" in report
        assert "HOLD" in report
        assert "Test contradiction" in report
        assert "Missing data" in report


class TestBriefingTemplates:
    """Test briefing template system."""

    @pytest.fixture
    def template_manager(self):
        """Create template manager."""
        return BriefingTemplateManager()

    def test_template_manager_initialization(self, template_manager):
        """Test template manager initialization."""
        assert template_manager is not None
        templates = template_manager.list_templates()
        assert "swing" in templates
        assert "day" in templates
        assert "value" in templates

    def test_swing_trading_template(self):
        """Test swing trading template."""
        template = BriefingTemplateFactory.create_swing_trading_template()

        assert template.strategy == TradingStrategy.SWING
        required = template.get_required_sections()
        assert "recent_events" in required
        assert "sentiment_analysis" in required
        assert "technical_analysis" in required
        assert "trading_signals" in required

    def test_day_trading_template(self):
        """Test day trading template."""
        template = BriefingTemplateFactory.create_day_trading_template()

        assert template.strategy == TradingStrategy.DAY
        required = template.get_required_sections()
        assert "pre_market_analysis" in required
        assert "technical_analysis" in required
        assert "volatility_metrics" in required

    def test_value_investing_template(self):
        """Test value investing template."""
        template = BriefingTemplateFactory.create_value_investing_template()

        assert template.strategy == TradingStrategy.VALUE
        required = template.get_required_sections()
        assert "fundamental_metrics" in required
        assert "intrinsic_value_analysis" in required
        assert "competitive_moat" in required

    def test_template_validation_pass(self, template_manager):
        """Test template validation with valid briefing."""
        briefing = {
            "recent_events": "Q3 earnings beat expectations",
            "sentiment_analysis": "Positive: 85% bullish",
            "risk_factors": "European slowdown",
            "technical_analysis": "RSI: 62.5",
            "source_quality": "High credibility sources",
            "key_takeaways": "Strong earnings, bullish setup",
            "trading_signals": "Bullish: 5 signals"
        }

        validation = template_manager.validate_briefing(briefing, "swing")

        assert validation["valid"] is True
        assert validation["completeness_score"] >= 85  # Most sections present

    def test_template_validation_fail(self, template_manager):
        """Test template validation with missing sections."""
        briefing = {
            "recent_events": "Some event"
        }

        validation = template_manager.validate_briefing(briefing, "swing")

        assert validation["valid"] is False
        assert len(validation["missing_sections"]) > 0
        assert validation["completeness_score"] < 50

    def test_template_formatting_structured(self, template_manager):
        """Test structured briefing formatting."""
        data = {
            "recent_events": "Test event",
            "sentiment_analysis": "Positive",
            "technical_analysis": "Bullish"
        }

        formatted = template_manager.format_briefing(data, "swing")

        assert "RECENT EVENTS" in formatted
        assert "SENTIMENT ANALYSIS" in formatted
        assert "Test event" in formatted


class TestQualityAssuranceOrchestrator:
    """Test quality assurance orchestrator."""

    @pytest.fixture
    def mock_client(self):
        """Mock OpenRouter client."""
        return Mock()

    @pytest.fixture
    def orchestrator(self, mock_client):
        """Create QA orchestrator."""
        with patch('backend.services.quality_assurance_orchestrator.QualityVerifier'):
            with patch('backend.services.quality_assurance_orchestrator.ContradictionDetector'):
                with patch('backend.services.quality_assurance_orchestrator.BriefingTemplateManager'):
                    orch = QualityAssuranceOrchestrator(
                        openrouter_client=mock_client,
                        trading_model="openai/gpt-3.5-turbo"
                    )
                    return orch

    def test_initialization(self, orchestrator):
        """Test orchestrator initialization."""
        assert orchestrator is not None
        assert orchestrator.trading_model == "openai/gpt-3.5-turbo"
        assert orchestrator.default_strategy == "swing"

    def test_comprehensive_qa_all_pass(self, orchestrator):
        """Test comprehensive QA with all checks passing."""
        # Mock template validation
        orchestrator.template_manager.validate_briefing = Mock(return_value={
            "valid": True,
            "completeness_score": 95,
            "missing_sections": [],
            "issues": []
        })

        # Mock quality verification
        orchestrator.quality_verifier.verify_briefing = Mock(return_value={
            "quality_score": 85,
            "overall_assessment": "PASS",
            "accuracy_score": 22,
            "completeness_score": 21,
            "objectivity_score": 22,
            "usefulness_score": 20
        })

        # Mock contradiction detection
        orchestrator.contradiction_detector.detect_contradictions = Mock(return_value={
            "contradictions": [],
            "severity": "LOW",
            "data_gaps": [],
            "trading_recommendation": "PROCEED",
            "confidence_adjustment": "0%"
        })
        orchestrator.contradiction_detector.should_require_manual_review = Mock(return_value=False)
        orchestrator.contradiction_detector.calculate_confidence_penalty = Mock(return_value=(0.95, "No issues"))

        briefing = {"metadata": {"symbol": "SAP.DE"}}
        sources = [{"title": "Test"}]

        result = orchestrator.run_comprehensive_qa(briefing, sources)

        assert result["should_use_briefing"] is True
        assert result["overall_score"] >= 80
        assert result["final_recommendation"]["action"] == "USE"

    def test_comprehensive_qa_quality_fail(self, orchestrator):
        """Test comprehensive QA with quality failure."""
        # Mock template validation (pass)
        orchestrator.template_manager.validate_briefing = Mock(return_value={
            "valid": True,
            "completeness_score": 90,
            "missing_sections": [],
            "issues": []
        })

        # Mock quality verification (fail)
        orchestrator.quality_verifier.verify_briefing = Mock(return_value={
            "quality_score": 45,  # Below threshold
            "overall_assessment": "FAIL",
            "accuracy_score": 10,
            "completeness_score": 12,
            "objectivity_score": 13,
            "usefulness_score": 10
        })

        # Mock contradiction detection (pass)
        orchestrator.contradiction_detector.detect_contradictions = Mock(return_value={
            "contradictions": [],
            "severity": "LOW",
            "data_gaps": [],
            "trading_recommendation": "PROCEED"
        })
        orchestrator.contradiction_detector.should_require_manual_review = Mock(return_value=False)

        briefing = {"metadata": {"symbol": "SAP.DE"}}
        sources = [{"title": "Test"}]

        result = orchestrator.run_comprehensive_qa(briefing, sources)

        assert result["should_use_briefing"] is False
        assert result["final_recommendation"]["action"] == "REJECT"
        assert len(result["final_recommendation"]["issues"]) > 0

    def test_comprehensive_qa_skip_contradictions(self, orchestrator):
        """Test comprehensive QA with contradiction detection skipped."""
        # Mock template and quality (both pass)
        orchestrator.template_manager.validate_briefing = Mock(return_value={
            "valid": True,
            "completeness_score": 90,
            "missing_sections": []
        })

        orchestrator.quality_verifier.verify_briefing = Mock(return_value={
            "quality_score": 75,
            "overall_assessment": "PASS"
        })

        briefing = {"metadata": {"symbol": "SAP.DE"}}
        sources = [{"title": "Test"}]

        result = orchestrator.run_comprehensive_qa(
            briefing,
            sources,
            skip_contradiction_detection=True
        )

        assert result["qa_stages"]["contradiction_detection"]["status"] == "skipped"
        assert "contradiction_detection" not in result["timing"] or result["timing"]["contradiction_detection"] == 0

    def test_calculate_overall_score(self, orchestrator):
        """Test overall score calculation."""
        results = {
            "qa_stages": {
                "template_validation": {
                    "valid": True,
                    "completeness_score": 90
                },
                "quality_verification": {
                    "quality_score": 80
                },
                "contradiction_detection": {
                    "status": "skipped"
                }
            }
        }

        score = orchestrator._calculate_overall_score(results)

        assert score > 0
        assert score <= 100

    def test_format_qa_report(self, orchestrator):
        """Test QA report formatting."""
        results = {
            "briefing_symbol": "SAP.DE",
            "overall_score": 85,
            "strategy": "swing",
            "final_recommendation": {
                "action": "USE",
                "confidence": "HIGH",
                "reason": "All checks passed",
                "issues": [],
                "warnings": []
            },
            "qa_stages": {
                "template_validation": {
                    "valid": True,
                    "completeness_score": 95
                },
                "quality_verification": {
                    "quality_score": 85,
                    "overall_assessment": "PASS",
                    "accuracy_score": 22,
                    "completeness_score": 21,
                    "objectivity_score": 22,
                    "usefulness_score": 20
                }
            },
            "timing": {
                "total": 2.5,
                "template_validation": 0.1,
                "quality_verification": 1.2
            }
        }

        report = orchestrator.format_qa_report(results)

        assert "QUALITY ASSURANCE REPORT" in report
        assert "SAP.DE" in report
        assert "85/100" in report
        assert "USE" in report


class TestIntegration:
    """Integration tests for quality assurance system."""

    def test_end_to_end_qa_workflow(self):
        """Test complete QA workflow."""
        # This would test the full integration in a real scenario
        # For now, we verify the components work together
        template_manager = BriefingTemplateManager()

        # Create a valid briefing
        briefing = {
            "recent_events": "Q3 earnings exceeded expectations",
            "sentiment_analysis": "Bullish: 75%",
            "risk_factors": "Market volatility",
            "technical_analysis": "RSI: 65, MACD bullish",
            "source_quality": "High credibility",
            "key_takeaways": "Strong fundamentals",
            "trading_signals": "Bullish setup"
        }

        # Validate
        validation = template_manager.validate_briefing(briefing, "swing")
        assert validation["valid"] is True

        # Format
        formatted = template_manager.format_briefing(briefing, "swing")
        assert len(formatted) > 0
        assert "RECENT EVENTS" in formatted
