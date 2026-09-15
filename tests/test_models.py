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
    ReviewedBrief,
    UserFeedback,
    ApprovedIntake,
    ErrorResponse,
)


# ============================================================================
# Helpers
# ============================================================================


def make_valid_requirement(desc="Valid requirement description", priority="medium"):
    return Requirement(description=desc, priority=priority)


def make_valid_extraction(confidence=0.9):
    return ProjectExtraction(
        project_name="Portal Project",
        summary="A valid summary of sufficient length for testing.",
        requirements=[make_valid_requirement()],
        confidence=confidence,
    )


def make_valid_recommendation(confidence=0.9):
    return TeamRecommendation(team="Web Development", confidence=confidence)


def make_valid_checklist():
    return Checklist(items=[ChecklistItem(id=1, task="Initial setup")], total_tasks=1)


# ============================================================================
# 1. State Transitions (Request & PendingIntake/ReviewedBrief)
# ============================================================================


def test_request_valid_workflow_transitions():
    req = Request(raw_text="Initial brief text here", source="web_form")
    assert req.status == "processing"

    # processing -> pending_review
    req.transition_to("pending_review")
    assert req.status == "pending_review"

    # pending_review -> approved
    req.transition_to("approved")
    assert req.status == "approved"


def test_request_invalid_transition_rejected_to_processing():
    req = Request(raw_text="Initial brief text here", source="web_form", status="rejected")
    with pytest.raises(ValueError) as exc_info:
        req.transition_to("processing")
    assert "cannot transition Request from 'rejected' to 'processing'" in str(exc_info.value)


def test_request_invalid_transition_approved_to_pending_review():
    req = Request(raw_text="Initial brief text here", source="web_form", status="approved")
    with pytest.raises(ValueError) as exc_info:
        req.transition_to("pending_review")
    assert "cannot transition Request from 'approved' to 'pending_review'" in str(exc_info.value)


def test_request_invalid_transition_processing_to_approved_directly():
    req = Request(raw_text="Initial brief text here", source="web_form", status="processing")
    with pytest.raises(ValueError) as exc_info:
        req.transition_to("approved")
    assert "cannot transition Request from 'processing' to 'approved'" in str(exc_info.value)


def test_pending_intake_transitions():
    intake = PendingIntake(
        request_id="REQ-123",
        extracted=make_valid_extraction(),
        team_recommendation=make_valid_recommendation(),
        checklist=make_valid_checklist(),
        status="draft",
    )
    # draft -> pending_review is allowed
    intake.transition_to("pending_review")
    assert intake.status == "pending_review"

    # pending_review -> draft is NOT allowed
    with pytest.raises(ValueError) as exc_info:
        intake.transition_to("draft")
    assert "cannot transition PendingIntake from 'pending_review' to 'draft'" in str(exc_info.value)


# ============================================================================
# 2. Nested Validation Cascading
# ============================================================================


def test_nested_validation_invalid_requirement_in_project_extraction():
    # Attempting to stuff an invalid requirement (description too short) inside ProjectExtraction
    with pytest.raises(ValidationError) as exc_info:
        ProjectExtraction(
            project_name="Portal",
            summary="A valid summary of sufficient length.",
            requirements=[{"description": "Hi"}],  # description < 5 chars
            confidence=0.9,
        )
    errors = exc_info.value.errors()
    assert any("requirements" in str(err["loc"]) for err in errors)


def test_nested_validation_invalid_confidence_in_pending_intake():
    # What happens if you try to stuff a ProjectExtraction with confidence=1.5 inside PendingIntake?
    with pytest.raises(ValidationError) as exc_info:
        PendingIntake(
            request_id="REQ-123",
            extracted={
                "project_name": "Portal",
                "summary": "A valid summary of sufficient length.",
                "requirements": [{"description": "Valid requirement description"}],
                "confidence": 1.5,  # Out of bounds (> 1.0)
            },
            team_recommendation=make_valid_recommendation(),
            checklist=make_valid_checklist(),
        )
    errors = exc_info.value.errors()
    assert any(err["loc"] == ("extracted", "confidence") for err in errors)


def test_nested_validation_invalid_checklist_priority_in_pending_intake():
    with pytest.raises(ValidationError) as exc_info:
        ReviewedBrief(
            request_id="REQ-123",
            extracted=make_valid_extraction(),
            team_recommendation=make_valid_recommendation(),
            checklist={
                "items": [{"task": "Do something", "priority": "urgent"}],  # invalid priority
                "total_tasks": 1,
            },
        )
    errors = exc_info.value.errors()
    assert any("checklist" in str(err["loc"]) for err in errors)


# ============================================================================
# 3. TeamRecommendation Field & ReviewedBrief Testing
# ============================================================================


def test_pending_intake_with_valid_team_recommendation():
    rec = TeamRecommendation(
        team="Mobile Development",
        confidence=0.92,
        reasoning=["Native iOS required", "Swift expertise needed"],
        alternative_team="Web Development",
        requires_human_review=False,
    )
    brief = ReviewedBrief(
        request_id="REQ-999",
        extracted=make_valid_extraction(),
        team_recommendation=rec,
        checklist=make_valid_checklist(),
    )
    assert brief.team_recommendation.team == "Mobile Development"
    assert brief.team_recommendation.confidence == 0.92
    assert len(brief.team_recommendation.reasoning) == 2


def test_pending_intake_fails_when_team_recommendation_missing():
    with pytest.raises(ValidationError) as exc_info:
        ReviewedBrief(
            request_id="REQ-999",
            extracted=make_valid_extraction(),
            # team_recommendation intentionally omitted
            checklist=make_valid_checklist(),
        )
    errors = exc_info.value.errors()
    assert any("team_recommendation" in str(err["loc"]) for err in errors)


def test_pending_intake_fails_when_team_recommendation_is_none():
    with pytest.raises(ValidationError) as exc_info:
        ReviewedBrief(
            request_id="REQ-999",
            extracted=make_valid_extraction(),
            team_recommendation=None,  # Not nullable
            checklist=make_valid_checklist(),
        )
    errors = exc_info.value.errors()
    assert any("team_recommendation" in str(err["loc"]) for err in errors)


def test_pending_intake_fails_when_team_recommendation_has_invalid_confidence():
    with pytest.raises(ValidationError) as exc_info:
        ReviewedBrief(
            request_id="REQ-999",
            extracted=make_valid_extraction(),
            team_recommendation={
                "team": "Web Development",
                "confidence": 1.5,  # Out of bounds
            },
            checklist=make_valid_checklist(),
        )
    errors = exc_info.value.errors()
    assert any(err["loc"] == ("team_recommendation", "confidence") for err in errors)


# ============================================================================
# 4. Relationship Constraints (requires_manual_review & UserFeedback)
# ============================================================================


def test_pending_intake_manual_review_requires_review_notes():
    # If requires_manual_review=True, review_notes must be provided
    with pytest.raises(ValidationError) as exc_info:
        PendingIntake(
            request_id="REQ-123",
            extracted=make_valid_extraction(),
            team_recommendation=make_valid_recommendation(),
            checklist=make_valid_checklist(),
            requires_manual_review=True,
            review_notes=None,  # Missing notes!
        )
    assert "review_notes are required when requires_manual_review is True" in str(exc_info.value)


def test_pending_intake_manual_review_empty_whitespace_rejected():
    with pytest.raises(ValidationError) as exc_info:
        PendingIntake(
            request_id="REQ-123",
            extracted=make_valid_extraction(),
            team_recommendation=make_valid_recommendation(),
            checklist=make_valid_checklist(),
            requires_manual_review=True,
            review_notes="    ",  # Only whitespace
        )
    assert "review_notes are required when requires_manual_review is True" in str(exc_info.value)


def test_pending_intake_manual_review_with_notes_succeeds():
    intake = PendingIntake(
        request_id="REQ-123",
        extracted=make_valid_extraction(),
        team_recommendation=make_valid_recommendation(),
        checklist=make_valid_checklist(),
        requires_manual_review=True,
        review_notes="Low confidence score (0.55) detected by LLM.",
    )
    assert intake.requires_manual_review is True
    assert "Low confidence" in intake.review_notes


def test_pending_intake_no_manual_review_notes_optional():
    intake = PendingIntake(
        request_id="REQ-123",
        extracted=make_valid_extraction(),
        team_recommendation=make_valid_recommendation(),
        checklist=make_valid_checklist(),
        requires_manual_review=False,
        review_notes=None,
    )
    assert intake.requires_manual_review is False
    assert intake.review_notes is None


def test_user_feedback_mark_issues_requires_issues_detected():
    with pytest.raises(ValidationError) as exc_info:
        UserFeedback(
            intake_id="INT-123",
            decision="mark_issues",
            issues_detected=None,  # Mandatory when mark_issues!
        )
    assert "issues_detected list cannot be empty or None" in str(exc_info.value)


def test_user_feedback_mark_issues_empty_list_rejected():
    with pytest.raises(ValidationError) as exc_info:
        UserFeedback(
            intake_id="INT-123",
            decision="mark_issues",
            issues_detected=[],  # Empty list rejected
        )
    assert "issues_detected list cannot be empty or None" in str(exc_info.value)


def test_user_feedback_mark_issues_valid():
    fb = UserFeedback(
        intake_id="INT-123",
        decision="mark_issues",
        issues_detected=["Database type was not specified"],
    )
    assert fb.decision == "mark_issues"
    assert len(fb.issues_detected) == 1


def test_user_feedback_approve_without_issues():
    fb = UserFeedback(
        intake_id="INT-123",
        decision="approve",
        issues_detected=None,
    )
    assert fb.decision == "approve"


# ============================================================================
# 5. Empty vs. None Semantics
# ============================================================================


def test_project_extraction_missing_info_empty_list_vs_none():
    req = make_valid_requirement()

    # missing_information=[]: SEMANTIC: Valid. We checked, and 0 information items are missing.
    e_empty = ProjectExtraction(
        project_name="Portal",
        summary="A valid summary of sufficient length.",
        requirements=[req],
        missing_information=[],
        confidence=0.9,
    )
    assert e_empty.missing_information == []

    # missing_information=None: SEMANTIC: Invalid. List[str] is non-nullable.
    with pytest.raises(ValidationError) as exc_info:
        ProjectExtraction(
            project_name="Portal",
            summary="A valid summary of sufficient length.",
            requirements=[req],
            missing_information=None,
            confidence=0.9,
        )
    assert any(err["loc"] == ("missing_information",) for err in exc_info.value.errors())


def test_project_extraction_scope_constraints_empty_list_vs_none():
    req = make_valid_requirement()

    # scope_constraints=[]: Valid empty list
    e_empty = ProjectExtraction(
        project_name="Portal",
        summary="A valid summary of sufficient length.",
        requirements=[req],
        scope_constraints=[],
        confidence=0.9,
    )
    assert e_empty.scope_constraints == []

    # scope_constraints=None: Rejected
    with pytest.raises(ValidationError):
        ProjectExtraction(
            project_name="Portal",
            summary="A valid summary of sufficient length.",
            requirements=[req],
            scope_constraints=None,
            confidence=0.9,
        )


def test_project_extraction_requirements_empty_vs_none():
    # requirements=[]: Rejected (violates min_length=1)
    with pytest.raises(ValidationError) as exc1:
        ProjectExtraction(
            project_name="Portal",
            summary="A valid summary of sufficient length.",
            requirements=[],
            confidence=0.9,
        )
    assert any("requirements" in str(err["loc"]) for err in exc1.value.errors())

    # requirements=None: Rejected (not a list)
    with pytest.raises(ValidationError) as exc2:
        ProjectExtraction(
            project_name="Portal",
            summary="A valid summary of sufficient length.",
            requirements=None,
            confidence=0.9,
        )
    assert any("requirements" in str(err["loc"]) for err in exc2.value.errors())


def test_checklist_item_depends_on_empty_vs_none():
    # depends_on=None: SEMANTIC: Default, no dependencies tracked
    item_none = ChecklistItem(task="Setup repository", depends_on=None)
    assert item_none.depends_on is None

    # depends_on=[]: SEMANTIC: Explicitly evaluated to 0 dependencies
    item_empty = ChecklistItem(task="Setup repository", depends_on=[])
    assert item_empty.depends_on == []

    # depends_on=[1, 2]: Dependencies present
    item_deps = ChecklistItem(task="Deploy container", depends_on=[1, 2])
    assert item_deps.depends_on == [1, 2]


def test_user_feedback_corrections_empty_vs_none():
    # corrections=None: No corrections provided
    fb_none = UserFeedback(intake_id="INT-1", decision="approve", corrections=None)
    assert fb_none.corrections is None

    # corrections={}: Empty corrections dictionary
    fb_empty = UserFeedback(intake_id="INT-1", decision="approve", corrections={})
    assert fb_empty.corrections == {}

    # corrections={"summary": "Updated"}: Dict with corrections
    fb_dict = UserFeedback(
        intake_id="INT-1",
        decision="approve",
        corrections={"summary": "Updated"},
    )
    assert fb_dict.corrections == {"summary": "Updated"}


# ============================================================================
# 6. RawBrief, Requirement, Boundary & Auto-ID Regression Tests
# ============================================================================


def test_raw_brief_empty_string():
    with pytest.raises(ValidationError) as exc_info:
        RawBrief(brief_text="")
    assert "string_too_short" in str(exc_info.value)


def test_raw_brief_below_min_length():
    with pytest.raises(ValidationError) as exc_info:
        RawBrief(brief_text="123456789")
    assert "string_too_short" in str(exc_info.value)


def test_raw_brief_exact_min_length():
    brief = RawBrief(brief_text="1234567890")
    assert len(brief.brief_text) == 10
    assert brief.source == "web_form"


def test_raw_brief_exact_max_length():
    exact_5000 = "x" * 5000
    brief = RawBrief(brief_text=exact_5000)
    assert len(brief.brief_text) == 5000


def test_raw_brief_over_max_length():
    over_limit = "x" * 5001
    with pytest.raises(ValidationError) as exc_info:
        RawBrief(brief_text=over_limit)
    assert "string_too_long" in str(exc_info.value)


def test_raw_brief_custom_source():
    brief = RawBrief(brief_text="A valid length client brief.", source="slack")
    assert brief.source == "slack"


def test_requirement_empty_description():
    with pytest.raises(ValidationError):
        Requirement(description="")


def test_requirement_below_min_length():
    with pytest.raises(ValidationError):
        Requirement(description="1234")


def test_requirement_exact_min_length():
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


def test_project_extraction_empty_project_name():
    req = make_valid_requirement()
    with pytest.raises(ValidationError):
        ProjectExtraction(
            project_name="",
            summary="A valid summary of sufficient length.",
            requirements=[req],
            confidence=0.9,
        )


def test_project_extraction_project_name_below_min_length():
    req = make_valid_requirement()
    with pytest.raises(ValidationError):
        ProjectExtraction(
            project_name="AB",
            summary="A valid summary of sufficient length.",
            requirements=[req],
            confidence=0.9,
        )


def test_project_extraction_project_name_exact_min_length():
    req = make_valid_requirement()
    extraction = ProjectExtraction(
        project_name="ABC",
        summary="A valid summary of sufficient length.",
        requirements=[req],
        confidence=0.9,
    )
    assert extraction.project_name == "ABC"


def test_project_extraction_empty_summary():
    req = make_valid_requirement()
    with pytest.raises(ValidationError):
        ProjectExtraction(
            project_name="Project",
            summary="",
            requirements=[req],
            confidence=0.9,
        )


def test_project_extraction_summary_below_min_length():
    req = make_valid_requirement()
    with pytest.raises(ValidationError):
        ProjectExtraction(
            project_name="Project",
            summary="1234567890123456789",
            requirements=[req],
            confidence=0.9,
        )


def test_project_extraction_summary_exact_min_length():
    req = make_valid_requirement()
    extraction = ProjectExtraction(
        project_name="Project",
        summary="12345678901234567890",
        requirements=[req],
        confidence=0.9,
    )
    assert len(extraction.summary) == 20


@pytest.mark.parametrize("confidence", [0.0, 0.5, 1.0])
def test_project_extraction_confidence_valid_boundaries(confidence):
    req = make_valid_requirement()
    extraction = ProjectExtraction(
        project_name="Project",
        summary="A valid summary of sufficient length.",
        requirements=[req],
        confidence=confidence,
    )
    assert extraction.confidence == confidence


@pytest.mark.parametrize("confidence", [-0.01, -1.0, 1.01, 2.0])
def test_project_extraction_confidence_invalid_boundaries(confidence):
    req = make_valid_requirement()
    with pytest.raises(ValidationError):
        ProjectExtraction(
            project_name="Project",
            summary="A valid summary of sufficient length.",
            requirements=[req],
            confidence=confidence,
        )


def test_project_extraction_mutable_defaults_isolated():
    req = make_valid_requirement()
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


def test_checklist_item_invalid_priority():
    with pytest.raises(ValidationError):
        ChecklistItem(task="Do something", priority="critical")


def test_checklist_generated_at_timezone():
    chk = Checklist(items=[], total_tasks=0)
    assert chk.generated_at.tzinfo == timezone.utc


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


def test_pending_intake_valid_and_invalid_statuses():
    ext = make_valid_extraction()
    rec = make_valid_recommendation()
    chk = make_valid_checklist()

    # Valid: draft
    p_draft = PendingIntake(
        request_id="REQ-001",
        extracted=ext,
        team_recommendation=rec,
        checklist=chk,
        status="draft",
    )
    assert p_draft.status == "draft"

    # Valid: pending_review (default)
    p_default = PendingIntake(
        request_id="REQ-002",
        extracted=ext,
        team_recommendation=rec,
        checklist=chk,
    )
    assert p_default.status == "pending_review"
    assert p_default.id.startswith("INT-")
    assert p_default.created_at.tzinfo == timezone.utc

    # Invalid: approved is rejected on PendingIntake
    with pytest.raises(ValidationError):
        PendingIntake(
            request_id="REQ-003",
            extracted=ext,
            team_recommendation=rec,
            checklist=chk,
            status="approved",
        )


@pytest.mark.parametrize("decision", ["approve", "mark_issues", "reject"])
def test_user_feedback_valid_decisions(decision):
    issues = ["Something"] if decision == "mark_issues" else None
    fb = UserFeedback(intake_id="INT-1234", decision=decision, issues_detected=issues)
    assert fb.decision == decision


def test_user_feedback_invalid_decision():
    with pytest.raises(ValidationError):
        UserFeedback(intake_id="INT-1234", decision="maybe")


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
