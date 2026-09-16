# tests/test_extraction_gating.py
import pytest
from unittest.mock import MagicMock

from app.models import (
    RawBrief,
    ProjectExtraction,
    Requirement,
    TeamRecommendation,
    Checklist,
    ChecklistItem,
    PendingIntake,
    ExtractionResult,
    extraction_is_usable,
)
from app.providers.ollama import OllamaProvider
from app.orchestrator import IntakeOrchestrator
from app.services.checklist import generate_checklist, generate_clarification_checklist
from app.storage.db import init_db


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


@pytest.fixture
def sample_ai_brief():
    return "Build an AI system for our operations. It should make things faster and save money. We have some data."


@pytest.fixture
def valid_mock_extraction():
    return ProjectExtraction(
        project_name="Employee Dashboard",
        summary="Internal dashboard for tracking employee projects, time logs, and metrics.",
        requirements=[
            Requirement(
                description="React web dashboard frontend",
                priority="high",
                confirmed=True,
                source_quote="React frontend",
            ),
            Requirement(
                description="Python FastAPI backend API",
                priority="high",
                confirmed=True,
                source_quote="Python backend",
            ),
        ],
        missing_information=["Expected concurrent users"],
        scope_constraints=["6 weeks timeline", "$50,000 budget"],
        confidence=0.92,
        extraction_status="validated",
    )


# ============================================================================
# Test 1: Failed extraction cannot produce implementation checklist
# ============================================================================

def test_failed_extraction_generates_only_clarification_checklist(sample_ai_brief):
    """
    Assert that when extraction fails:
    - checklist exists
    - checklist is marked as clarification ('clarification')
    - checklist contains clarification tasks
    - checklist does NOT contain implementation-specific tasks
    """
    provider = MagicMock(spec=OllamaProvider)
    provider.extract_requirements.return_value = ExtractionResult(
        valid=False,
        error="LLM returned invalid JSON after retries",
        requires_manual_review=True,
        review_notes="LLM output could not be parsed as valid JSON.",
    )

    orchestrator = IntakeOrchestrator(provider=provider)
    pending = orchestrator.process_brief(RawBrief(brief_text=sample_ai_brief))

    # 1. Checklist exists
    assert pending.checklist is not None
    assert pending.checklist.total_tasks > 0

    # 2. Marked as clarification
    assert pending.checklist.checklist_type == "clarification"
    assert pending.checklist.type == "clarification"

    # 3. Contains clarification tasks
    tasks = [item.task for item in pending.checklist.items]
    assert any("clarify" in t.lower() or "identify" in t.lower() or "define" in t.lower() for t in tasks)

    # 4. Strictly does NOT contain implementation-specific tasks or inventions
    forbidden_terms = [
        "vector database",
        "rag",
        "fastapi",
        "docker",
        "kubernetes",
        "embedding model",
        "document ingestion pipeline",
        "technical architecture and design specifications",
        "development workspace, repository, and dependencies",
        "quality assurance and integration testing",
        "release build and configure deployment",
    ]
    for task_text in tasks:
        for forbidden in forbidden_terms:
            assert forbidden not in task_text.lower(), f"Forbidden implementation task found: '{task_text}' contains '{forbidden}'"


# ============================================================================
# Test 2: Confidence 0 blocks implementation
# ============================================================================

def test_zero_extraction_confidence_blocks_implementation_checklist(sample_ai_brief):
    """
    Assert that an extraction with confidence 0.0 is blocked by the extraction gate
    from generating an implementation checklist and produces a clarification checklist instead.
    """
    provider = MagicMock(spec=OllamaProvider)
    # Return valid=True but with confidence=0.0
    zero_conf_extraction = ProjectExtraction(
        project_name="AI System",
        summary="AI operations system with unclear requirements.",
        requirements=[
            Requirement(description="Build unspecified AI system", priority="high", confirmed=False)
        ],
        confidence=0.0,
        extraction_status="validated",
    )
    provider.extract_requirements.return_value = ExtractionResult(
        valid=True,
        extraction=zero_conf_extraction,
        requires_manual_review=True,
    )

    orchestrator = IntakeOrchestrator(provider=provider)
    pending = orchestrator.process_brief(RawBrief(brief_text=sample_ai_brief))

    # Gate blocks implementation: checklist must be clarification
    assert pending.checklist.checklist_type == "clarification"
    assert pending.checklist.type == "clarification"

    # Does not contain implementation tasks like repository setup or release build
    tasks_lower = [item.task.lower() for item in pending.checklist.items]
    assert not any("development workspace" in t for t in tasks_lower)
    assert not any("release build" in t for t in tasks_lower)
    assert any("clarify" in t or "identify" in t or "define" in t for t in tasks_lower)


# ============================================================================
# Test 3: Error message cannot contaminate checklist
# ============================================================================

def test_error_message_cannot_contaminate_checklist(sample_ai_brief):
    """
    Provide an extraction error such as 'Ollama connection refused'
    and assert that terms from the error do not appear as checklist tasks.
    """
    provider = MagicMock(spec=OllamaProvider)
    provider.extract_requirements.return_value = ExtractionResult(
        valid=False,
        error="Ollama connection refused to http://localhost:11434",
        user_message="AI system unavailable. Please ensure Ollama is running on http://localhost:11434",
        requires_manual_review=True,
        review_notes="Ollama service unavailable at http://localhost:11434.",
    )

    orchestrator = IntakeOrchestrator(provider=provider)
    pending = orchestrator.process_brief(RawBrief(brief_text=sample_ai_brief))

    # Verify checklist exists and is clarification
    assert pending.checklist.checklist_type == "clarification"

    # Assert error terms do not appear as checklist tasks
    contamination_terms = [
        "ollama",
        "connection",
        "refused",
        "11434",
        "offline",
        "traceback",
        "http",
        "status code",
        "internal server error",
        "failed",
    ]
    tasks = [item.task.lower() for item in pending.checklist.items]
    for task_text in tasks:
        for term in contamination_terms:
            assert term not in task_text, f"Checklist contaminated with error term '{term}': '{task_text}'"


# ============================================================================
# Test 4: Original brief is preserved
# ============================================================================

def test_original_brief_is_preserved_when_extraction_fails(sample_ai_brief):
    """
    Assert that original brief is preserved exactly and not overwritten by error strings.
    """
    provider = MagicMock(spec=OllamaProvider)
    provider.extract_requirements.return_value = ExtractionResult(
        valid=False,
        error="Ollama connection refused",
        user_message="AI system unavailable. Please ensure Ollama is running on http://localhost:11434",
        requires_manual_review=True,
    )

    orchestrator = IntakeOrchestrator(provider=provider)
    pending = orchestrator.process_brief(RawBrief(brief_text=sample_ai_brief, source="web_form"))

    # Original brief preserved on PendingIntake model
    assert pending.original_brief == sample_ai_brief
    assert pending.raw_brief == sample_ai_brief

    # Original brief preserved in SQLite requests table
    stored_req = orchestrator.get_request(pending.request_id)
    assert stored_req is not None
    assert stored_req.raw_text == sample_ai_brief
    assert "AI system unavailable" not in stored_req.raw_text
    assert "We couldn't confidently extract" not in stored_req.raw_text


# ============================================================================
# Test 5: Valid extraction still generates implementation checklist
# ============================================================================

def test_validated_extraction_generates_implementation_checklist(valid_mock_extraction):
    """
    Ensure the extraction gate allows valid extractions through the normal path
    to generate an implementation-specific delivery checklist.
    """
    provider = MagicMock(spec=OllamaProvider)
    provider.extract_requirements.return_value = ExtractionResult(
        valid=True,
        extraction=valid_mock_extraction,
        requires_manual_review=False,
    )

    orchestrator = IntakeOrchestrator(provider=provider)
    brief = RawBrief(brief_text="We need a React web frontend with Python backend for an employee dashboard.")
    pending = orchestrator.process_brief(brief)

    # Checklist must be an implementation checklist
    assert pending.checklist.checklist_type == "implementation"
    assert pending.checklist.type == "implementation"
    assert pending.checklist.total_tasks >= 5

    tasks_lower = [item.task.lower() for item in pending.checklist.items]
    # Implementation tasks are present
    assert any("architecture" in t for t in tasks_lower)
    assert any("workspace" in t or "repository" in t for t in tasks_lower)
    assert any("react" in t or "frontend" in t for t in tasks_lower)
    assert any("testing" in t or "quality assurance" in t for t in tasks_lower)


# ============================================================================
# Test 6: Failed extraction triggers human review
# ============================================================================

def test_failed_extraction_triggers_human_review(sample_ai_brief):
    """
    Assert that requires_manual_review is True for both the pending intake and team recommendation.
    """
    provider = MagicMock(spec=OllamaProvider)
    provider.extract_requirements.return_value = ExtractionResult(
        valid=False,
        error="LLM syntax error",
        user_message="AI system was unable to parse requirements.",
        requires_manual_review=True,
        review_notes="Syntax parsing error during extraction.",
    )

    orchestrator = IntakeOrchestrator(provider=provider)
    pending = orchestrator.process_brief(RawBrief(brief_text=sample_ai_brief))

    assert pending.requires_manual_review is True
    assert pending.team_recommendation.requires_human_review is True
    assert pending.review_notes is not None
    assert len(pending.review_notes.strip()) > 0


# ============================================================================
# Additional Invariant Tests for extraction_is_usable and Boundary Conditions
# ============================================================================

def test_extraction_is_usable_boundary_conditions(valid_mock_extraction):
    """Test all boundary conditions for the authoritative extraction gate."""
    # None is not usable
    assert extraction_is_usable(None) is False

    # Valid extraction with positive confidence is usable
    assert extraction_is_usable(valid_mock_extraction) is True

    # Status failed is not usable
    failed_extraction = valid_mock_extraction.model_copy(update={"extraction_status": "failed"})
    assert extraction_is_usable(failed_extraction) is False

    # Confidence 0 is not usable
    zero_conf = valid_mock_extraction.model_copy(update={"confidence": 0.0})
    assert extraction_is_usable(zero_conf) is False

    # Negative confidence is not usable
    neg_conf = valid_mock_extraction.model_copy(update={"confidence": -0.1})
    assert extraction_is_usable(neg_conf) is False

    # ExtractionResult checking
    res_valid = ExtractionResult(valid=True, extraction=valid_mock_extraction)
    assert extraction_is_usable(res_valid) is True

    res_invalid = ExtractionResult(valid=False, extraction=valid_mock_extraction)
    assert extraction_is_usable(res_invalid) is False

    res_zero = ExtractionResult(valid=True, extraction=zero_conf)
    assert extraction_is_usable(res_zero) is False


def test_recommendation_does_not_invent_certainty_on_failed_extraction():
    """
    When extraction fails, recommendation uncertainty must increase, not decrease.
    """
    provider = MagicMock(spec=OllamaProvider)
    provider.extract_requirements.return_value = ExtractionResult(
        valid=False,
        error="Provider timeout",
        requires_manual_review=True,
    )

    orchestrator = IntakeOrchestrator(provider=provider)
    # Brief without clear team signals
    ambiguous_brief = RawBrief(brief_text="Do something helpful for our organization.")
    pending = orchestrator.process_brief(ambiguous_brief)

    assert pending.team_recommendation.confidence <= 0.35
    assert pending.team_recommendation.requires_human_review is True
    if pending.team_recommendation.team is None:
        assert pending.team_recommendation.confidence == 0.0
