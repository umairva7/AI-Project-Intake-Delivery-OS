from datetime import timezone
import pytest
from pydantic import ValidationError
from app.models import (
    RawBrief,
    Request,
    Requirement,
    ProjectExtraction,
    ChecklistItem,
    Checklist,
    TeamRecommendation,
    PendingIntake,
    UserFeedback,
    ApprovedIntake,
    ErrorResponse,
)


def test_raw_brief_valid():
    brief = RawBrief(brief_text="This is a valid project brief with enough length.")
    assert brief.brief_text == "This is a valid project brief with enough length."
    assert brief.source == "web_form"


def test_raw_brief_too_short():
    with pytest.raises(ValidationError):
        RawBrief(brief_text="Short")


def test_raw_brief_too_long():
    with pytest.raises(ValidationError):
        RawBrief(brief_text="a" * 5001)


def test_raw_brief_max_length_boundary():
    brief = RawBrief(brief_text="a" * 5000)
    assert len(brief.brief_text) == 5000


def test_request_timezone_utc():
    req = Request(raw_text="Test brief text here", source="web_form")
    assert req.created_at.tzinfo == timezone.utc


def test_requirement_validation():
    req = Requirement(description="Build auth API", priority="high")
    assert req.priority == "high"
    assert req.confirmed is True


def test_project_extraction_empty_requirements_fails():
    with pytest.raises(ValidationError):
        ProjectExtraction(
            project_name="Auth Portal",
            summary="A secure authentication portal for internal employees.",
            requirements=[],  # min_length=1 should reject empty list
            confidence=0.95,
        )


def test_project_extraction_mutable_defaults_isolated():
    req = Requirement(description="Build auth API", priority="high")
    e1 = ProjectExtraction(
        project_name="Project One",
        summary="A secure portal description long enough.",
        requirements=[req],
        confidence=0.9,
    )
    e2 = ProjectExtraction(
        project_name="Project Two",
        summary="Another secure portal description long enough.",
        requirements=[req],
        confidence=0.9,
    )
    e1.missing_information.append("Item 1")
    assert "Item 1" not in e2.missing_information


def test_checklist_item_with_id_and_dependencies():
    task1 = ChecklistItem(id=1, task="Design DB Schema", priority="high")
    task2 = ChecklistItem(id=2, task="Implement Migrations", priority="high", depends_on=[1])
    assert task1.id == 1
    assert task2.depends_on == [1]


def test_team_recommendation():
    rec = TeamRecommendation(
        team="Web Development",
        confidence=0.88,
        reasoning=["React frontend", "FastAPI backend"],
    )
    assert rec.team == "Web Development"
    assert rec.confidence == 0.88


def test_pending_intake():
    req = Requirement(description="Build auth API", priority="high")
    extraction = ProjectExtraction(
        project_name="Auth Portal",
        summary="A secure authentication portal for internal employees.",
        requirements=[req],
        confidence=0.95,
    )
    rec = TeamRecommendation(team="Web Development", confidence=0.88)
    chk = Checklist(items=[ChecklistItem(id=1, task="Setup DB", priority="high")], total_tasks=1)
    pending = PendingIntake(
        request_id="REQ-12345",
        extracted=extraction,
        team_recommendation=rec,
        checklist=chk,
    )
    assert pending.status == "pending_review"
    assert pending.created_at.tzinfo == timezone.utc
