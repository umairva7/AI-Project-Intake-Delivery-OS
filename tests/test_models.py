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


def test_requirement_validation():
    req = Requirement(description="Build auth API", priority="high")
    assert req.priority == "high"
    assert req.confirmed is True


def test_project_extraction():
    req = Requirement(description="Build auth API", priority="high")
    extraction = ProjectExtraction(
        project_name="Auth Portal",
        summary="A secure authentication portal for internal employees.",
        requirements=[req],
        confidence=0.95,
    )
    assert extraction.confidence == 0.95


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
    chk = Checklist(items=[ChecklistItem(task="Setup DB", priority="high")], total_tasks=1)
    pending = PendingIntake(
        request_id="REQ-12345",
        extracted=extraction,
        team_recommendation=rec,
        checklist=chk,
    )
    assert pending.status == "pending_review"
