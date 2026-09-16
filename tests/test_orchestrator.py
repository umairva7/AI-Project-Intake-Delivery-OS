# tests/test_orchestrator.py
import json
from unittest.mock import patch, MagicMock
import pytest

from app.models import (
    RawBrief,
    ProjectExtraction,
    Requirement,
    PendingIntake,
    ApprovedIntake,
    UserFeedback,
)
from app.providers.ollama import OllamaProvider, ExtractionResult
from app.orchestrator import IntakeOrchestrator
from app.storage.db import init_db, get_db_connection


@pytest.fixture(autouse=True)
def setup_db():
    """Ensure clean database schema before tests"""
    init_db()


@pytest.fixture
def mock_extraction_dict():
    return {
        "project_name": "Employee Dashboard",
        "summary": "Internal dashboard for tracking employee projects, time logs, and company metrics.",
        "requirements": [
            {
                "description": "React web dashboard frontend",
                "priority": "high",
                "confirmed": True,
                "source_quote": "React frontend",
            },
            {
                "description": "Python FastAPI backend API",
                "priority": "high",
                "confirmed": True,
                "source_quote": "Python backend",
            },
            {
                "description": "User authentication and role-based access",
                "priority": "medium",
                "confirmed": True,
                "source_quote": "secure login",
            },
        ],
        "missing_information": [
            "Expected number of concurrent users",
            "Hosting preferences (AWS vs On-prem)",
        ],
        "scope_constraints": ["6 weeks MVP", "$50,000 budget"],
        "confidence": 0.92,
    }


@pytest.fixture
def mock_provider(mock_extraction_dict):
    """Mock OllamaProvider that returns successful ExtractionResult"""
    provider = MagicMock(spec=OllamaProvider)
    extraction = ProjectExtraction.model_validate(mock_extraction_dict)
    provider.extract_requirements.return_value = ExtractionResult(
        valid=True,
        extraction=extraction,
        requires_manual_review=False,
        review_notes=None,
    )
    return provider


# ============================================================================
# 1. Core Workflow: process_brief returns PendingIntake
# ============================================================================


def test_process_brief_returns_pending_intake(mock_provider):
    """
    Test: orchestrator.process_brief(RawBrief(brief_text="...")) should return PendingIntake
    """
    orchestrator = IntakeOrchestrator(provider=mock_provider)

    raw_brief = RawBrief(
        brief_text=(
            "We need a React frontend with Python backend for an employee dashboard. "
            "Timeline is 6 weeks with secure login and project tracking."
        ),
        source="web_form",
    )

    pending = orchestrator.process_brief(raw_brief)

    # Assert model types and basic contracts
    assert isinstance(pending, PendingIntake)
    assert pending.id.startswith("INT-")
    assert pending.request_id.startswith("REQ-")
    assert pending.status == "pending_review"

    # Extracted data validation
    assert pending.extracted.project_name == "Employee Dashboard"
    assert len(pending.extracted.requirements) == 3
    assert pending.extracted.confidence == 0.92

    # Team recommendation validation
    assert pending.team_recommendation.team == "Web Development"
    assert pending.team_recommendation.confidence >= 0.70

    # Checklist validation
    assert pending.checklist.total_tasks > 0
    assert len(pending.checklist.items) == pending.checklist.total_tasks
    assert any("Clarify with client" in item.task for item in pending.checklist.items)

    # Database persistence verification
    stored_request = orchestrator.get_request(pending.request_id)
    assert stored_request is not None
    assert stored_request.id == pending.request_id
    assert stored_request.status == "pending_review"
    assert stored_request.raw_text == raw_brief.brief_text

    stored_intake = orchestrator.get_intake(pending.id)
    assert stored_intake is not None
    assert stored_intake.id == pending.id
    assert stored_intake.request_id == pending.request_id
    assert stored_intake.extracted.project_name == "Employee Dashboard"

    # Verify query by request_id
    intake_by_req = orchestrator.get_intake_by_request_id(pending.request_id)
    assert intake_by_req is not None
    assert intake_by_req.id == pending.id


def test_process_brief_with_raw_string_input(mock_provider):
    """Verifies that passing a plain string to process_brief works identically"""
    orchestrator = IntakeOrchestrator(provider=mock_provider)

    brief_str = (
        "We need a React web application with Python REST API for managing warehouse items."
    )

    pending = orchestrator.process_brief(brief_str)
    assert isinstance(pending, PendingIntake)
    assert pending.id.startswith("INT-")
    assert pending.extracted.project_name == "Employee Dashboard"


# ============================================================================
# 2. Low Confidence & Review Flagging
# ============================================================================


def test_process_brief_low_confidence_flags_manual_review(mock_extraction_dict):
    """Low confidence (< 0.7) sets requires_manual_review=True and populates review_notes"""
    mock_extraction_dict["confidence"] = 0.55
    extraction = ProjectExtraction.model_validate(mock_extraction_dict)

    provider = MagicMock(spec=OllamaProvider)
    provider.extract_requirements.return_value = ExtractionResult(
        valid=True,
        extraction=extraction,
        requires_manual_review=True,
        review_notes="Confidence score (0.55) is below threshold (0.70).",
    )

    orchestrator = IntakeOrchestrator(provider=provider)
    brief = RawBrief(brief_text="Need some dashboard app quickly.")

    pending = orchestrator.process_brief(brief)
    assert pending.requires_manual_review is True
    assert pending.review_notes is not None
    assert "below threshold" in pending.review_notes

    # Verify persisted flag in database
    db_intake = orchestrator.get_intake(pending.id)
    assert db_intake.requires_manual_review is True
    assert "below threshold" in db_intake.review_notes


# ============================================================================
# 3. Handling Complete LLM Failure
# ============================================================================


def test_process_brief_llm_failure_returns_fallback_pending_intake():
    """When LLM completely fails (timeout / offline), fallback PendingIntake is returned"""
    provider = MagicMock(spec=OllamaProvider)
    provider.extract_requirements.return_value = ExtractionResult(
        valid=False,
        error="Ollama connection refused",
        requires_manual_review=True,
        review_notes="Ollama service unavailable at http://localhost:11434.",
    )

    orchestrator = IntakeOrchestrator(provider=provider)
    brief = RawBrief(brief_text="Build an inventory tracking system with barcodes.")

    pending = orchestrator.process_brief(brief)
    assert isinstance(pending, PendingIntake)
    assert pending.requires_manual_review is True
    assert "Manual review required" in pending.review_notes
    assert pending.extracted.confidence == 0.0
    assert pending.checklist.total_tasks > 0

    # Stored properly in DB
    db_intake = orchestrator.get_intake(pending.id)
    assert db_intake is not None
    assert db_intake.requires_manual_review is True


# ============================================================================
# 4. Partial Failures During Assembly (Fault Isolation & Fallbacks)
# ============================================================================


def test_process_brief_checklist_failure_executes_fallback(mock_provider):
    """
    Simulates partial failure: extraction and team recommendation succeed,
    but checklist generation raises an exception halfway.
    Verifies that:
    1. Orchestrator catches the error without rolling back or crashing.
    2. Fallback triage checklist is created.
    3. requires_manual_review is set to True with explanatory notes.
    4. Successful extraction and team recommendation are preserved and stored.
    """
    orchestrator = IntakeOrchestrator(provider=mock_provider)
    brief = RawBrief(
        brief_text="We need a React frontend with Python backend for an employee dashboard."
    )

    with patch(
        "app.orchestrator.generate_checklist",
        side_effect=RuntimeError("Checklist service timeout or syntax error"),
    ):
        pending = orchestrator.process_brief(brief)

        # 1. Pipeline did NOT crash and returned a valid PendingIntake
        assert isinstance(pending, PendingIntake)
        assert pending.id.startswith("INT-")
        assert pending.status == "pending_review"

        # 2. Upstream successes are PRESERVED (not rolled back or discarded)
        assert pending.extracted.project_name == "Employee Dashboard"
        assert pending.team_recommendation.team == "Web Development"

        # 3. Fallback checklist was generated
        assert pending.checklist.total_tasks == 1
        assert (
            pending.checklist.items[0].task
            == "Manually review requirements and compile delivery checklist"
        )

        # 4. Flagged for manual review with specific error notes
        assert pending.requires_manual_review is True
        assert "Checklist generation failed" in pending.review_notes
        assert "Manual task entry required" in pending.review_notes

        # 5. Successfully persisted in database
        db_intake = orchestrator.get_intake(pending.id)
        assert db_intake is not None
        assert db_intake.requires_manual_review is True
        assert db_intake.extracted.project_name == "Employee Dashboard"


def test_process_brief_team_recommendation_failure_executes_fallback(mock_provider):
    """
    Simulates partial failure where team recommendation service raises an exception.
    Verifies that fallback team recommendation ('Pending Triage') is assigned and flagged for review.
    """
    orchestrator = IntakeOrchestrator(provider=mock_provider)
    brief = RawBrief(
        brief_text="We need a React frontend with Python backend for an employee dashboard."
    )

    with patch(
        "app.orchestrator.recommend_team",
        side_effect=ValueError("Team taxonomy classification failure"),
    ):
        pending = orchestrator.process_brief(brief)

        assert isinstance(pending, PendingIntake)
        assert pending.team_recommendation.team == "Pending Triage"
        assert pending.requires_manual_review is True
        assert "Team recommendation failed" in pending.review_notes
        assert pending.checklist.total_tasks > 0


# ============================================================================
# 5. Approval Workflow: approve_intake
# ============================================================================


def test_approve_intake_workflow(mock_provider):
    """Tests human approval transitions and persists ApprovedIntake"""
    orchestrator = IntakeOrchestrator(provider=mock_provider)
    brief = RawBrief(
        brief_text="We need a React frontend with Python backend for an employee dashboard."
    )
    pending = orchestrator.process_brief(brief)

    # User approves
    feedback = UserFeedback(
        intake_id=pending.id,
        decision="approve",
        notes="Looks complete and ready for sprint planning.",
    )
    approved = orchestrator.approve_intake(feedback)

    assert isinstance(approved, ApprovedIntake)
    assert approved.id.startswith("APPROVED-")
    assert approved.intake_id == pending.id
    assert approved.request_id == pending.request_id
    assert approved.status == "approved"
    assert approved.project_name == pending.extracted.project_name
    assert approved.team_assignment == "Web Development"

    # Database checks: request & intake updated to approved
    stored_req = orchestrator.get_request(pending.request_id)
    assert stored_req.status == "approved"

    stored_approved = orchestrator.get_approved_intake(approved.id)
    assert stored_approved is not None
    assert stored_approved.id == approved.id


def test_mark_issues_workflow(mock_provider):
    """Tests user marking issues on pending intake"""
    orchestrator = IntakeOrchestrator(provider=mock_provider)
    brief = RawBrief(
        brief_text="We need a React frontend with Python backend for an employee dashboard."
    )
    pending = orchestrator.process_brief(brief)

    feedback = UserFeedback(
        intake_id=pending.id,
        decision="mark_issues",
        issues_detected=["Database type is missing", "Scope timeline too tight"],
        notes="Please clarify with client team first",
    )
    updated_intake = orchestrator.approve_intake(feedback)

    assert updated_intake.id == pending.id

    # Check issues in DB
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM intakes WHERE id = ?", (pending.id,)).fetchone()
    conn.close()

    assert row["issues_marked"] is not None
    issues_list = json.loads(row["issues_marked"])
    assert "Database type is missing" in issues_list


def test_logging_emitted_for_every_major_step(mock_provider, caplog):
    """Verifies that clear, structured log messages are emitted for every major pipeline step."""
    import logging
    orchestrator = IntakeOrchestrator(provider=mock_provider)
    brief = RawBrief(
        brief_text="We need a React frontend with Python backend for an employee dashboard."
    )

    with caplog.at_level(logging.INFO):
        orchestrator.process_brief(brief)

    log_output = caplog.text
    assert "Step 1: Request Ingestion" in log_output
    assert "Step 2: LLM Extraction" in log_output
    assert "Step 3: Team Recommendation" in log_output
    assert "Step 4: Checklist Generation" in log_output
    assert "Step 5: Intake Assembly" in log_output
    assert "Step 6: Intake Persistence" in log_output
    assert "Step 7: Human Review Ready" in log_output
