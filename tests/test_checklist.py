# tests/test_checklist.py
import pytest
from app.models import Requirement, ProjectExtraction, Checklist, TeamRecommendation
from app.services.checklist import (
    generate_checklist,
    is_critical_missing_info,
    _normalize_task_text,
    _is_duplicate_task,
)


def make_req(desc: str, priority="high"):
    return Requirement(description=desc, priority=priority)


# ============================================================================
# 1. Team-Specific Checklists
# ============================================================================


def test_ai_ml_team_specific_checklist():
    """AI / ML project generates model, data, and evaluation specific tasks"""
    reqs = [
        make_req("Train transformer model for document classification"),
        make_req("Expose inference endpoint with latency under 100ms"),
    ]
    checklist = generate_checklist(requirements=reqs, team="AI / ML")

    assert isinstance(checklist, Checklist)
    tasks_text = [item.task.lower() for item in checklist.items]

    # Verify AI/ML specific lifecycle tasks
    assert any("model architecture" in t or "retrieval strategy" in t for t in tasks_text)
    assert any("model exploration" in t or "vector store" in t for t in tasks_text)
    assert any("model accuracy" in t or "benchmark" in t for t in tasks_text)
    assert any("inference service" in t or "containerize" in t for t in tasks_text)


def test_web_development_team_specific_checklist():
    """Web project generates frontend, REST API, cross-browser, and build tasks"""
    reqs = [
        make_req("React customer portal with responsive navigation"),
        make_req("FastAPI user authentication and profile backend"),
    ]
    checklist = generate_checklist(requirements=reqs, team="Web Development")

    assert isinstance(checklist, Checklist)
    tasks_text = [item.task.lower() for item in checklist.items]

    assert any("frontend component hierarchy" in t or "rest api" in t for t in tasks_text)
    assert any("cross-browser" in t for t in tasks_text)
    assert any("production build" in t for t in tasks_text)


def test_devops_team_specific_checklist():
    """DevOps project generates infrastructure, K8s, CI/CD, and monitoring tasks"""
    reqs = [
        make_req("Provision Kubernetes cluster on AWS EKS"),
        make_req("Set up automated GitHub Actions CI/CD deployment"),
    ]
    checklist = generate_checklist(requirements=reqs, team="DevOps / Infrastructure")

    assert isinstance(checklist, Checklist)
    tasks_text = [item.task.lower() for item in checklist.items]

    assert any("infrastructure topology" in t or "ci/cd" in t for t in tasks_text)
    assert any("cloud infrastructure" in t or "kubernetes" in t for t in tasks_text)
    assert any("monitoring dashboards" in t or "alerts" in t for t in tasks_text)


# ============================================================================
# 2. Multi-Team Projects (Primary + Supporting Tasks)
# ============================================================================


def test_multi_team_checklist_includes_supporting_tasks():
    """Multi-team project includes primary tasks plus supporting team integration tasks"""
    reqs = [
        make_req("Deploy machine learning RAG model for customer Q&A"),
        make_req("Implement web chat widget interface"),
    ]
    checklist = generate_checklist(
        requirements=reqs,
        team="AI / ML",
        supporting_teams=["Web Development"],
    )

    tasks_text = [item.task.lower() for item in checklist.items]

    # Primary team (AI/ML)
    assert any("model architecture" in t for t in tasks_text)

    # Supporting team (Web Development integration)
    assert any("client integration" in t or "ui consuming" in t or "web development" in t for t in tasks_text)


# ============================================================================
# 3. Missing Information Filtering (Critical vs. Minor)
# ============================================================================


def test_missing_critical_info_creates_clarification_task():
    """Critical missing info (e.g. database, user scale, hosting) creates initial clarification tasks"""
    reqs = [make_req("Build customer billing portal")]
    missing = [
        "Target deployment cloud provider (AWS vs Azure)",
        "Expected monthly active user scale",
    ]

    checklist = generate_checklist(
        requirements=reqs,
        team="Web Development",
        missing_information=missing,
    )

    # Clarification task appears as the very first task(s)
    first_task = checklist.items[0]
    assert first_task.id == 1
    assert "clarify with client" in first_task.task.lower()
    assert first_task.depends_on is None


def test_minor_missing_info_does_not_create_clarification_tasks():
    """Minor cosmetic details (color, logo, button copy) are filtered out and do not create tasks"""
    reqs = [make_req("Build customer billing portal")]
    minor_missing = [
        "Primary brand button color scheme",
        "Company logo font preference",
        "Dark mode theme styling",
    ]

    checklist = generate_checklist(
        requirements=reqs,
        team="Web Development",
        missing_information=minor_missing,
    )

    tasks_text = [item.task.lower() for item in checklist.items]
    assert not any("color scheme" in t for t in tasks_text)
    assert not any("logo font" in t for t in tasks_text)
    assert not any("dark mode" in t for t in tasks_text)


def test_is_critical_missing_info_helper():
    assert is_critical_missing_info("Expected database type (Postgres vs MySQL)") is True
    assert is_critical_missing_info("Peak concurrent user traffic volume") is True
    assert is_critical_missing_info("OAuth authentication provider") is True
    assert is_critical_missing_info("MVP launch deadline and timeline") is True

    # Minor / cosmetic
    assert is_critical_missing_info("Navbar background color") is False
    assert is_critical_missing_info("Footer favicon icon") is False


# ============================================================================
# 4. Task Count Constraints (Min 5, Max 12)
# ============================================================================


def test_very_simple_project_meets_minimum_5_tasks():
    """A minimal 1-requirement project expands delivery stages to guarantee at least 5 meaningful tasks"""
    reqs = [make_req("Single small landing page")]
    checklist = generate_checklist(requirements=reqs, team="Web Development")

    assert len(checklist.items) >= 5
    assert checklist.total_tasks >= 5


def test_complex_project_capped_at_maximum_12_tasks():
    """A project with 15 requirements caps at 12 tasks without blowing up plan size"""
    reqs = [make_req(f"Feature requirement number {i} with specific deliverables") for i in range(15)]
    missing = [f"Missing specification detail {j} regarding architecture" for j in range(5)]

    checklist = generate_checklist(
        requirements=reqs,
        team="Web Development",
        missing_information=missing,
        supporting_teams=["DevOps / Infrastructure"],
    )

    assert len(checklist.items) <= 12
    assert checklist.total_tasks <= 12


# ============================================================================
# 5. Duplicate Task Removal & Normalization
# ============================================================================


def test_duplicate_task_removal():
    """Duplicate / nearly identical tasks are deduplicated"""
    assert _is_duplicate_task("Implement React user dashboard", ["Implement React user dashboard"]) is True
    assert _is_duplicate_task("Conduct cross-browser testing", ["Perform cross-browser testing"]) is True
    assert _is_duplicate_task("Deploy to cloud server", ["Implement database migration"]) is False


# ============================================================================
# 6. Delivery Lifecycle Ordering & Dependencies
# ============================================================================


def test_checklist_ordering_and_dependencies():
    """
    Verifies that checklist follows:
    Clarification -> Architecture -> Setup -> Implementation -> Testing -> Deployment
    and dependencies point strictly to prior valid task IDs.
    """
    reqs = [
        make_req("Implement React user dashboard"),
        make_req("Implement FastAPI REST API"),
    ]
    missing = ["Confirm target database technology"]

    checklist = generate_checklist(
        requirements=reqs,
        team="Web Development",
        missing_information=missing,
    )

    # 1. Clarification task is at index 0 and has no dependencies
    assert checklist.items[0].id == 1
    assert "confirm with client" in checklist.items[0].task.lower()
    assert checklist.items[0].depends_on is None

    # 2. Architecture task depends on clarification task (id: 1)
    arch_task = checklist.items[1]
    assert arch_task.depends_on == [1]

    # 3. All subsequent dependencies point to earlier task IDs (no forward or circular deps)
    for idx, item in enumerate(checklist.items):
        if item.depends_on:
            for dep in item.depends_on:
                assert dep < item.id


# ============================================================================
# 7. Safe Failure & Empty Requirements Handling
# ============================================================================


def test_empty_requirements_raises_safe_error():
    """Empty requirements list raises ValueError allowing orchestrator fault isolation to handle it"""
    with pytest.raises(ValueError, match="Cannot generate delivery checklist without project requirements"):
        generate_checklist(requirements=[])

    with pytest.raises(ValueError, match="Cannot generate delivery checklist without project requirements"):
        generate_checklist(requirements=None)


# ============================================================================
# 8. ProjectExtraction & TeamRecommendation Object Compatibility
# ============================================================================


def test_generate_checklist_with_pydantic_models():
    """Accepts ProjectExtraction and TeamRecommendation model objects directly"""
    extraction = ProjectExtraction(
        project_name="AI Image Classifier",
        summary="A computer vision application for identifying objects in images.",
        requirements=[
            make_req("Train computer vision neural network model"),
            make_req("Build mobile client app for taking photos"),
        ],
        missing_information=["Confirm expected inference device hardware"],
        confidence=0.92,
    )
    team_rec = TeamRecommendation(
        team="AI / ML",
        supporting_teams=["Mobile Development"],
        confidence=0.85,
    )

    checklist = generate_checklist(requirements=extraction, team=team_rec)
    assert isinstance(checklist, Checklist)
    assert 5 <= checklist.total_tasks <= 12
    assert any("clarify with client" in item.task.lower() for item in checklist.items)
