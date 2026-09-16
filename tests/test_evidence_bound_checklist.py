# tests/test_evidence_bound_checklist.py
import re
import pytest
from unittest.mock import MagicMock

from app.models import (
    RawBrief,
    ProjectExtraction,
    Requirement,
    ExtractionResult,
    Checklist,
    ChecklistItem,
    TaskEvidence,
    TeamRecommendation,
)
from app.orchestrator import IntakeOrchestrator
from app.providers.groq import GroqProvider
from app.services.checklist import (
    generate_checklist,
    generate_clarification_checklist,
    is_technology_supported_by_evidence,
    validate_checklist_evidence,
)
from app.storage.db import init_db


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def _word_in_text(word: str, text: str) -> bool:
    """Helper to check whole-word presence in text."""
    return bool(re.search(r"\b" + re.escape(word) + r"\b", text.lower()))


# ============================================================================
# Test 1: Employee Dashboard Brief (No Hallucinated Vector Store, Redis, Docker, K8s, Cloud)
# ============================================================================

def test_employee_dashboard_does_not_hallucinate_unsupported_tech():
    """
    Given the brief:
    'We need a React frontend with a Python API for an internal employee dashboard.
    The dashboard should display employee information, project assignments, and work hours.
    We have an existing PostgreSQL database we can connect to.
    Timeline: 6 weeks.
    Budget: $50,000.'

    Assert checklist does NOT contain:
    - 'vector store' / 'vector database'
    - 'rag'
    - 'redis'
    - 'docker'
    - 'kubernetes' / 'k8s'
    - specific deployment platforms (e.g. 'aws', 'gcp', 'azure', 'vercel')
    """
    brief_text = (
        "We need a React frontend with a Python API for an internal employee dashboard.\n"
        "The dashboard should display employee information, project assignments, and work hours.\n"
        "We have an existing PostgreSQL database we can connect to.\n"
        "Timeline: 6 weeks.\n"
        "Budget: $50,000."
    )

    extraction = ProjectExtraction(
        project_name="Internal Employee Dashboard",
        summary="Internal employee dashboard displaying employee info, assignments, and work hours.",
        requirements=[
            Requirement(description="React frontend for internal employee dashboard", priority="high", confirmed=True),
            Requirement(description="Python API backend services", priority="high", confirmed=True),
            Requirement(description="Display employee information, project assignments, and work hours", priority="high", confirmed=True),
            Requirement(description="Connect to existing PostgreSQL database", priority="high", confirmed=True),
        ],
        missing_information=[],
        scope_constraints=["6 weeks timeline", "$50,000 budget"],
        confidence=0.95,
        extraction_status="validated",
    )

    # 1. Direct service call
    checklist = generate_checklist(
        requirements=extraction,
        team="Web Development",
        brief_text=brief_text,
    )

    # 2. Pipeline call via orchestrator
    mock_provider = MagicMock(spec=GroqProvider)
    mock_provider.extract_requirements.return_value = ExtractionResult(
        valid=True,
        extraction=extraction,
    )
    orchestrator = IntakeOrchestrator(provider=mock_provider)
    pending = orchestrator.process_brief(RawBrief(brief_text=brief_text))
    pipeline_checklist = pending.checklist

    forbidden_terms = [
        "vector store",
        "vector database",
        "rag",
        "redis",
        "docker",
        "kubernetes",
        "k8s",
        "aws",
        "gcp",
        "azure",
        "vercel",
        "heroku",
        "netlify",
    ]

    for cl in (checklist, pipeline_checklist):
        assert isinstance(cl, Checklist)
        assert cl.checklist_type == "implementation"
        assert len(cl.items) >= 5

        for item in cl.items:
            task_lower = item.task.lower()
            for forbidden in forbidden_terms:
                assert not _word_in_text(forbidden, task_lower), (
                    f"Hallucinated unsupported tech '{forbidden}' found in task: '{item.task}'"
                )


# ============================================================================
# Test 2: Sales Automation Brief (No React, REST API, FastAPI, Docker, K8s, Cloud)
# ============================================================================

def test_sales_automation_brief_does_not_hallucinate_web_or_container_stack():
    """
    Given a brief with only:
    - CSV exports
    - Daily collection
    - Anomaly detection

    Assert checklist does NOT contain:
    - 'react'
    - 'rest api'
    - 'fastapi'
    - 'docker'
    - 'kubernetes'
    - cloud platform ('aws', 'gcp', 'azure', 'cloud platform')
    """
    brief_text = (
        "We need daily collection of sales data from internal CSV exports. "
        "The system should detect anomalies in daily sales numbers and email a summary report."
    )

    extraction = ProjectExtraction(
        project_name="Sales Data Anomaly Detection",
        summary="Automated pipeline collecting sales CSV data, detecting anomalies, and emailing reports.",
        requirements=[
            Requirement(description="Daily collection of sales data from CSV exports", priority="high", confirmed=True),
            Requirement(description="Detect anomalies in daily sales numbers", priority="high", confirmed=True),
            Requirement(description="Email summary report of detected anomalies", priority="high", confirmed=True),
        ],
        missing_information=[],
        confidence=0.90,
        extraction_status="validated",
    )

    # Generate checklist even if team is "AI / ML" or "Data Science"
    checklist = generate_checklist(
        requirements=extraction,
        team="AI / ML",
        brief_text=brief_text,
    )

    forbidden_terms = [
        "react",
        "rest api",
        "fastapi",
        "docker",
        "kubernetes",
        "k8s",
        "cloud platform",
        "aws",
        "gcp",
        "azure",
    ]

    assert isinstance(checklist, Checklist)
    for item in checklist.items:
        task_lower = item.task.lower()
        for forbidden in forbidden_terms:
            assert not _word_in_text(forbidden, task_lower), (
                f"Hallucinated term '{forbidden}' found in sales automation task: '{item.task}'"
            )


# ============================================================================
# Test 3: Explicit Technical Requirements Are Honored
# ============================================================================

def test_explicit_technical_requirements_generate_matching_tasks():
    """
    Given a brief that explicitly asks for:
    - React
    - FastAPI
    - Docker

    Assert checklist DOES contain implementation tasks for:
    - React
    - FastAPI
    - Docker
    """
    brief_text = (
        "We require a React frontend and a FastAPI backend for our customer portal. "
        "The application must be packaged and containerized with Docker."
    )

    extraction = ProjectExtraction(
        project_name="Customer Portal",
        summary="Customer portal built with React and FastAPI, packaged with Docker.",
        requirements=[
            Requirement(description="Build React frontend customer portal", priority="high", confirmed=True),
            Requirement(description="Develop FastAPI backend API services", priority="high", confirmed=True),
            Requirement(description="Package application with Docker containerization", priority="high", confirmed=True),
        ],
        missing_information=[],
        confidence=0.95,
        extraction_status="validated",
    )

    checklist = generate_checklist(
        requirements=extraction,
        team="Web Development",
        brief_text=brief_text,
    )

    impl_tasks = [item.task.lower() for item in checklist.items if item.task_type == "implementation"]

    # Assert explicit technologies are preserved in the implementation checklist
    assert any("react" in t for t in impl_tasks), "Expected implementation task for React"
    assert any("fastapi" in t for t in impl_tasks), "Expected implementation task for FastAPI"
    assert any("docker" in t for t in impl_tasks), "Expected implementation task for Docker"


# ============================================================================
# Test 4: Missing Information Clarification Without Invented Algorithms
# ============================================================================

def test_missing_information_generates_clarification_task_without_invented_techniques():
    """
    Given a brief where anomaly detection thresholds are missing:
    - missing_information=['anomaly thresholds']

    Assert:
    - Generated checklist includes a clarification task for anomaly thresholds
    - Does NOT invent specific techniques like Z-score, Isolation Forest, etc.
    """
    brief_text = (
        "Collect daily sales numbers from CSV exports and detect anomalies. "
        "Email daily summaries."
    )

    extraction = ProjectExtraction(
        project_name="Sales Anomaly Tracker",
        summary="Collect CSV sales data, identify anomalies, and email daily report.",
        requirements=[
            Requirement(description="Collect daily sales numbers from CSV exports", priority="high", confirmed=True),
            Requirement(description="Detect anomalies in sales numbers", priority="high", confirmed=True),
            Requirement(description="Email daily summary report", priority="high", confirmed=True),
        ],
        missing_information=["anomaly thresholds"],
        confidence=0.88,
        extraction_status="validated",
    )

    checklist = generate_checklist(
        requirements=extraction,
        team="Data Science",
        brief_text=brief_text,
        missing_information=extraction.missing_information,
    )

    # 1. Assert clarification task exists for anomaly thresholds
    clarification_tasks = [
        item for item in checklist.items
        if item.task_type == "clarification"
    ]
    assert len(clarification_tasks) >= 1
    assert any("anomaly thresholds" in item.task.lower() for item in clarification_tasks), (
        "Expected clarification task for 'anomaly thresholds'"
    )

    # 2. Assert no invented statistical or ML algorithms
    invented_algorithms = ["z-score", "isolation forest", "autoencoder", "dbscan", "arima"]
    for item in checklist.items:
        task_lower = item.task.lower()
        for algo in invented_algorithms:
            assert algo not in task_lower, (
                f"Invented algorithm '{algo}' found in checklist task: '{item.task}'"
            )


# ============================================================================
# Test 5: Traceable Evidence Field on All Tasks
# ============================================================================

def test_traceable_evidence_on_all_tasks():
    """
    Assert:
    - Every implementation task has task.evidence
    - task.has_evidence is True
    - task.evidence.type in ('requirement', 'implied')
    - Clarification tasks have task.evidence.type == 'missing_information'
    """
    brief_text = (
        "We need a React web frontend with a Python backend for internal staff. "
        "PostgreSQL will be used for data persistence."
    )

    extraction = ProjectExtraction(
        project_name="Staff Management Portal",
        summary="Internal staff management portal with React, Python, and PostgreSQL.",
        requirements=[
            Requirement(description="React web frontend for internal staff", priority="high", confirmed=True),
            Requirement(description="Python backend service", priority="high", confirmed=True),
            Requirement(description="PostgreSQL data persistence layer", priority="high", confirmed=True),
        ],
        missing_information=["Authentication provider (OAuth vs SAML)"],
        confidence=0.92,
        extraction_status="validated",
    )

    checklist = generate_checklist(
        requirements=extraction,
        team="Web Development",
        brief_text=brief_text,
    )

    assert len(checklist.items) >= 5

    for task in checklist.items:
        # Every task must have an evidence record
        assert task.evidence is not None, f"Task '{task.task}' missing evidence"
        assert task.has_evidence is True, f"Task '{task.task}' has_evidence is False"

        if task.task_type == "implementation":
            assert task.evidence.type in ("requirement", "implied"), (
                f"Implementation task '{task.task}' has invalid evidence type: {task.evidence.type}"
            )
            assert task.evidence.confirmed is True, (
                f"Implementation task '{task.task}' evidence must be confirmed"
            )
        elif task.task_type == "clarification":
            assert task.evidence.type == "missing_information", (
                f"Clarification task '{task.task}' has invalid evidence type: {task.evidence.type}"
            )
            assert task.evidence.confirmed is False, (
                f"Clarification task '{task.task}' evidence should have confirmed=False"
            )
