# tests/test_regression_eval.py
import json
import re
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from app.models import ProjectExtraction, Requirement
from app.orchestrator import IntakeOrchestrator
from app.providers.ollama import ExtractionResult
from app.services.recommendation import recommend_team
from app.storage.db import get_db_connection, init_db


@pytest.fixture(autouse=True)
def setup_test_db():
    init_db()


def load_eval_case(case_id: str):
    root = Path(__file__).resolve().parent.parent
    candidates = [
        root / "evaluation" / "dataset.json",
        root / "test_cases" / "evaluation_data.json",
        root / "evaluation_data.json",
    ]
    for path in candidates:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            cases = data.get("evaluation_set", {}).get("cases", data.get("cases", []))
            for c in cases:
                if c["case_id"] == case_id:
                    return c
    raise ValueError(f"Case {case_id} not found in evaluation dataset")


def test_regression_tc004_web_development():
    """TC-004 e-commerce platform should route to Web Development"""
    case = load_eval_case("TC-004")
    ext = ProjectExtraction(
        project_name="E-Commerce Platform",
        summary=case["input"],
        requirements=[Requirement(description=r) for r in case["expected_requirements"]],
        confidence=0.95,
    )
    rec = recommend_team(ext)
    assert rec.team == "Web Development"


def test_regression_tc006_ai_ml():
    """TC-006 recommendation engine should route to AI / ML"""
    case = load_eval_case("TC-006")
    ext = ProjectExtraction(
        project_name="E-Commerce Recommendation Engine",
        summary=case["input"],
        requirements=[Requirement(description=r) for r in case["expected_requirements"]],
        confidence=0.90,
    )
    rec = recommend_team(ext)
    assert rec.team == "AI / ML"


def test_regression_tc007_automation_data():
    """TC-007 daily CSV collection & cleaning should route to Automation / Data"""
    case = load_eval_case("TC-007")
    ext = ProjectExtraction(
        project_name="Sales Data Pipeline",
        summary=case["input"],
        requirements=[Requirement(description=r) for r in case["expected_requirements"]],
        confidence=0.90,
    )
    rec = recommend_team(ext)
    assert rec.team == "Automation / Data"


def test_regression_tc008_automation_data():
    """TC-008 invoice PDF OCR & accounting integration should route to Automation / Data"""
    case = load_eval_case("TC-008")
    ext = ProjectExtraction(
        project_name="Invoice Processing Automation",
        summary=case["input"],
        requirements=[Requirement(description=r) for r in case["expected_requirements"]],
        confidence=0.90,
    )
    rec = recommend_team(ext)
    assert rec.team == "Automation / Data"


def test_regression_tc012_cross_functional_supporting_ai_ml():
    """TC-012 multi-team request should retain AI / ML in supporting teams"""
    case = load_eval_case("TC-012")
    ext = ProjectExtraction(
        project_name="Mobile AI App",
        summary=case["input"],
        requirements=[Requirement(description=r) for r in case["expected_requirements"]],
        confidence=0.85,
    )
    rec = recommend_team(ext)
    assert "AI / ML" in rec.supporting_teams


def test_regression_spark_kafka_data_engineering():
    """Enterprise Spark/Kafka streaming pipeline routes to Data Engineering"""
    brief = "Build an Apache Spark and Kafka streaming data pipeline to ingest telemetry events into warehouse."
    rec = recommend_team(brief)
    assert rec.team == "Data Engineering"


def test_regression_tie_break_csv_snowflake():
    """
    Tie-break test: 'Automate CSV exports into Snowflake'.
    Precedence rule: Enterprise warehouse (Snowflake) gives Data Engineering primary lead;
    Automation / Data is retained as supporting team.
    """
    brief = "Automate CSV exports into Snowflake"
    rec = recommend_team(brief)
    assert rec.team == "Data Engineering"
    assert "Automation / Data" in rec.supporting_teams


def test_regression_tc017_secret_free_sqlite():
    """
    TC-017 Policy (b) Sanitized-Only regression test:
    Asserts in-memory sanitization scrubs secret credentials before SQLite persistence.
    No secret-shaped strings or credentials exist anywhere in SQLite requests or intakes tables.
    """
    case = load_eval_case("TC-017")
    brief_input = case["input"]

    mock_provider = MagicMock()
    mock_provider.extract_requirements.return_value = ExtractionResult(
        valid=True,
        extraction=ProjectExtraction(
            project_name="Sanitized Request Project",
            summary="A project request that contained sensitive credentials and SQL injection attempts.",
            requirements=[Requirement(description="Build a website", priority="high")],
            confidence=0.85,
        ),
        requires_manual_review=False,
        review_notes=None,
    )

    orchestrator = IntakeOrchestrator(provider=mock_provider)
    pending = orchestrator.process_brief(brief_input)

    # Invariants on PendingIntake
    assert pending.sensitive_data_detected is True
    assert pending.injection_attempt_detected is True
    assert pending.requires_manual_review is True
    assert "Sensitive credentials or secrets were detected" in (pending.review_notes or "")

    # Invariant: No secret-shaped strings in SQLite
    conn = get_db_connection()
    req_row = conn.execute("SELECT * FROM requests WHERE id = ?", (pending.request_id,)).fetchone()
    intake_row = conn.execute("SELECT * FROM intakes WHERE id = ?", (pending.id,)).fetchone()
    conn.close()

    assert req_row is not None
    assert intake_row is not None

    req_text = " ".join(str(val) for val in dict(req_row).values())
    intake_text = " ".join(str(val) for val in dict(intake_row).values())
    all_db_text = f"{req_text} {intake_text}"

    # Secret pattern assertions
    secret_key_pattern = re.compile(r"\bsk-[a-zA-Z0-9]{10,}\b")
    assert secret_key_pattern.search(all_db_text) is None

    # Dynamically extract the password and key from the raw input without hardcoding raw secrets here
    found_secrets = re.findall(r"\bsk-[a-zA-Z0-9]{10,}\b", brief_input)
    for s in found_secrets:
        assert s not in all_db_text

    password_matches = re.findall(r"(?:password\s*(?:is|:|=)\s*)([^\s,;]+)", brief_input, re.IGNORECASE)
    for p in password_matches:
        assert p not in all_db_text
