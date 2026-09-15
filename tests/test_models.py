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


# ============================================================================
# RawBrief Edge Cases
# ============================================================================


def test_raw_brief_empty_string():
    with pytest.raises(ValidationError) as exc_info:
        RawBrief(brief_text="")
    assert "string_too_short" in str(exc_info.value)


def test_raw_brief_below_min_length():
    # Exactly 9 characters (1 below minimum of 10)
    with pytest.raises(ValidationError) as exc_info:
        RawBrief(brief_text="123456789")
    assert "string_too_short" in str(exc_info.value)


def test_raw_brief_exact_min_length():
    # Exactly 10 characters (boundary condition)
    brief = RawBrief(brief_text="1234567890")
    assert len(brief.brief_text) == 10
    assert brief.source == "web_form"


def test_raw_brief_exact_max_length():
    # Exactly 5000 characters (boundary condition)
    exact_5000 = "x" * 5000
    brief = RawBrief(brief_text=exact_5000)
    assert len(brief.brief_text) == 5000


def test_raw_brief_over_max_length():
    # Exactly 5001 characters (1 above maximum of 5000)
    over_limit = "x" * 5001
    with pytest.raises(ValidationError) as exc_info:
        RawBrief(brief_text=over_limit)
    assert "string_too_long" in str(exc_info.value)


def test_raw_brief_custom_source():
    brief = RawBrief(brief_text="A valid length client brief.", source="slack")
    assert brief.source == "slack"


# ============================================================================
# Requirement Edge Cases
# ============================================================================


def test_requirement_empty_description():
    with pytest.raises(ValidationError):
        Requirement(description="")


def test_requirement_below_min_length():
    # Exactly 4 characters (1 below minimum of 5)
    with pytest.raises(ValidationError):
        Requirement(description="1234")


def test_requirement_exact_min_length():
    # Exactly 5 characters (boundary condition)
    req = Requirement(description="12345")
    assert req.description == "12345"
    assert req.priority == "medium"
    assert req.confirmed is True
    assert req.source_quote is None


@pytest.mark.parametrize("priority", ["high", "medium", "low"])
def test_requirement_valid_priorities(priority):
    req = Requirement(description="Valid task description", priority=priority)
    assert req.priority == priority


def test_requirement_invalid_priority():
    with pytest.raises(ValidationError):
        Requirement(description="Valid task description", priority="urgent")


# ============================================================================
# ProjectExtraction Edge Cases
# ============================================================================


def test_project_extraction_empty_project_name():
    req = Requirement(description="Valid requirement")
    with pytest.raises(ValidationError):
        ProjectExtraction(
            project_name="",
            summary="A valid summary of sufficient length.",
            requirements=[req],
            confidence=0.9,
        )


def test_project_extraction_project_name_below_min_length():
    # Exactly 2 characters (below min of 3)
    req = Requirement(description="Valid requirement")
    with pytest.raises(ValidationError):
        ProjectExtraction(
            project_name="AB",
            summary="A valid summary of sufficient length.",
            requirements=[req],
            confidence=0.9,
        )


def test_project_extraction_project_name_exact_min_length():
    # Exactly 3 characters (boundary)
    req = Requirement(description="Valid requirement")
    extraction = ProjectExtraction(
        project_name="ABC",
        summary="A valid summary of sufficient length.",
        requirements=[req],
        confidence=0.9,
    )
    assert extraction.project_name == "ABC"


def test_project_extraction_empty_summary():
    req = Requirement(description="Valid requirement")
    with pytest.raises(ValidationError):
        ProjectExtraction(
            project_name="Project",
            summary="",
            requirements=[req],
            confidence=0.9,
        )


def test_project_extraction_summary_below_min_length():
    # Exactly 19 characters (below min of 20)
    req = Requirement(description="Valid requirement")
    with pytest.raises(ValidationError):
        ProjectExtraction(
            project_name="Project",
            summary="1234567890123456789",  # 19 chars
            requirements=[req],
            confidence=0.9,
        )


def test_project_extraction_summary_exact_min_length():
    # Exactly 20 characters (boundary)
    req = Requirement(description="Valid requirement")
    extraction = ProjectExtraction(
        project_name="Project",
        summary="12345678901234567890",  # 20 chars
        requirements=[req],
        confidence=0.9,
    )
    assert len(extraction.summary) == 20


def test_project_extraction_empty_requirements_list():
    with pytest.raises(ValidationError):
        ProjectExtraction(
            project_name="Project",
            summary="A valid summary of sufficient length.",
            requirements=[],  # Empty list violates min_length=1
            confidence=0.9,
        )


@pytest.mark.parametrize("confidence", [0.0, 0.5, 1.0])
def test_project_extraction_confidence_valid_boundaries(confidence):
    req = Requirement(description="Valid requirement")
    extraction = ProjectExtraction(
        project_name="Project",
        summary="A valid summary of sufficient length.",
        requirements=[req],
        confidence=confidence,
    )
    assert extraction.confidence == confidence


@pytest.mark.parametrize("confidence", [-0.01, -1.0, 1.01, 2.0])
def test_project_extraction_confidence_invalid_boundaries(confidence):
    req = Requirement(description="Valid requirement")
    with pytest.raises(ValidationError):
        ProjectExtraction(
            project_name="Project",
            summary="A valid summary of sufficient length.",
            requirements=[req],
            confidence=confidence,
        )


def test_project_extraction_mutable_defaults_isolated():
    req = Requirement(description="Valid requirement")
    e1 = ProjectExtraction(
        project_name="Project One",
        summary="A valid summary of sufficient length.",
        requirements=[req],
        confidence=0.9,
    )
    e2 = ProjectExtraction(
        project_name="Project Two",
        summary="A valid summary of sufficient length.",
        requirements=[req],
        confidence=0.9,
    )
    e1.missing_information.append("Missing DB credentials")
    e1.scope_constraints.append("Max 4 weeks")

    assert "Missing DB credentials" not in e2.missing_information
    assert "Max 4 weeks" not in e2.scope_constraints


# ============================================================================
# TeamRecommendation Edge Cases
# ============================================================================


@pytest.mark.parametrize("confidence", [0.0, 1.0])
def test_team_recommendation_confidence_boundaries(confidence):
    rec = TeamRecommendation(team="Web Development", confidence=confidence)
    assert rec.confidence == confidence
    assert rec.reasoning == []
    assert rec.alternative_team is None
    assert rec.requires_human_review is False


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_team_recommendation_confidence_out_of_bounds(confidence):
    with pytest.raises(ValidationError):
        TeamRecommendation(team="Web Development", confidence=confidence)


# ============================================================================
# ChecklistItem & Checklist Edge Cases
# ============================================================================


def test_checklist_item_defaults_and_explicit_fields():
    item_default = ChecklistItem(task="Write test cases")
    assert item_default.id is None
    assert item_default.priority == "medium"
    assert item_default.estimated_effort is None
    assert item_default.depends_on is None

    item_explicit = ChecklistItem(
        id=10,
        task="Deploy API",
        priority="high",
        estimated_effort="4 hours",
        depends_on=[1, 2],
    )
    assert item_explicit.id == 10
    assert item_explicit.priority == "high"
    assert item_explicit.depends_on == [1, 2]


def test_checklist_item_invalid_priority():
    with pytest.raises(ValidationError):
        ChecklistItem(task="Do something", priority="critical")


def test_checklist_generated_at_timezone():
    chk = Checklist(items=[], total_tasks=0)
    assert chk.generated_at.tzinfo == timezone.utc


# ============================================================================
# Request Edge Cases
# ============================================================================


def test_request_id_autogenerated_and_unique():
    r1 = Request(raw_text="Request one text here", source="web_form")
    r2 = Request(raw_text="Request two text here", source="web_form")
    assert r1.id.startswith("REQ-")
    assert r2.id.startswith("REQ-")
    assert r1.id != r2.id
    assert r1.created_at.tzinfo == timezone.utc


@pytest.mark.parametrize("status", ["processing", "pending_review", "approved", "rejected"])
def test_request_valid_statuses(status):
    req = Request(raw_text="Valid text here", source="email", status=status)
    assert req.status == status


def test_request_invalid_status():
    with pytest.raises(ValidationError):
        Request(raw_text="Valid text here", source="email", status="completed")


# ============================================================================
# PendingIntake Edge Cases
# ============================================================================


def test_pending_intake_valid_and_invalid_statuses():
    req = Requirement(description="Valid requirement")
    ext = ProjectExtraction(
        project_name="Portal",
        summary="A valid summary of sufficient length.",
        requirements=[req],
        confidence=0.85,
    )
    rec = TeamRecommendation(team="Web Development", confidence=0.85)
    chk = Checklist(items=[], total_tasks=0)

    # Valid status: draft
    p_draft = PendingIntake(
        request_id="REQ-001",
        extracted=ext,
        team_recommendation=rec,
        checklist=chk,
        status="draft",
    )
    assert p_draft.status == "draft"

    # Valid status: pending_review (default)
    p_default = PendingIntake(
        request_id="REQ-002",
        extracted=ext,
        team_recommendation=rec,
        checklist=chk,
    )
    assert p_default.status == "pending_review"
    assert p_default.id.startswith("INT-")
    assert p_default.created_at.tzinfo == timezone.utc

    # Invalid status: approved is not allowed in PendingIntake
    with pytest.raises(ValidationError):
        PendingIntake(
            request_id="REQ-003",
            extracted=ext,
            team_recommendation=rec,
            checklist=chk,
            status="approved",
        )


# ============================================================================
# UserFeedback Edge Cases
# ============================================================================


@pytest.mark.parametrize("decision", ["approve", "mark_issues", "reject"])
def test_user_feedback_valid_decisions(decision):
    fb = UserFeedback(intake_id="INT-1234", decision=decision)
    assert fb.decision == decision


def test_user_feedback_invalid_decision():
    with pytest.raises(ValidationError):
        UserFeedback(intake_id="INT-1234", decision="maybe")


# ============================================================================
# ApprovedIntake Edge Cases
# ============================================================================


@pytest.mark.parametrize("status", ["approved", "in_progress", "completed"])
def test_approved_intake_valid_statuses(status):
    approved = ApprovedIntake(
        request_id="REQ-1",
        intake_id="INT-1",
        project_name="Project Alpha",
        summary="A valid summary of sufficient length.",
        requirements=[],
        team_assignment="Web Development",
        checklist=[],
        status=status,
    )
    assert approved.status == status
    assert approved.id.startswith("APPROVED-")
    assert approved.approved_at.tzinfo == timezone.utc


def test_approved_intake_invalid_status():
    with pytest.raises(ValidationError):
        ApprovedIntake(
            request_id="REQ-1",
            intake_id="INT-1",
            project_name="Project Alpha",
            summary="A valid summary of sufficient length.",
            requirements=[],
            team_assignment="Web Development",
            checklist=[],
            status="pending_review",
        )
