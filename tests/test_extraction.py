# tests/test_extraction.py
import json
from unittest.mock import MagicMock
import pytest

from app.models import (
    ProjectExtraction,
    RawBrief,
    Requirement,
    ExtractionResult,
)
from app.providers.ollama import OllamaProvider
from app.services.extraction import (
    ExtractionError,
    ExtractionService,
    ExtractionValidationError,
    audit_and_prevent_hallucinations,
    calculate_extraction_confidence,
    extract_requirements,
    filter_and_audit_missing_info,
)


def make_mock_provider(extraction_dict: dict) -> OllamaProvider:
    """Create a mock OllamaProvider that returns an ExtractionResult from a dictionary."""
    provider = MagicMock(spec=OllamaProvider)
    extraction = ProjectExtraction.model_validate(extraction_dict)
    provider.extract_requirements.return_value = ExtractionResult(
        valid=True,
        extraction=extraction,
        requires_manual_review=False,
    )
    return provider


# ============================================================================
# 1. Detailed Project Brief (Complete Structured Extraction)
# ============================================================================


def test_detailed_project_brief_extraction():
    """
    Detailed project brief produces complete structured extraction with
    high confidence and accurate constraints.
    """
    brief = (
        "We need a React web dashboard that displays real-time sales metrics from our existing "
        "PostgreSQL database. The backend must be built using Python FastAPI. User authentication "
        "is required, and the MVP must launch in 6 weeks with a budget of $40,000."
    )
    raw_dict = {
        "project_name": "Sales Analytics Dashboard",
        "summary": "Real-time sales analytics dashboard with React frontend and FastAPI backend.",
        "requirements": [
            {"description": "React web dashboard frontend", "priority": "high", "confirmed": True, "source_quote": "React web dashboard"},
            {"description": "FastAPI backend connected to PostgreSQL database", "priority": "high", "confirmed": True, "source_quote": "Python FastAPI"},
            {"description": "User authentication system", "priority": "high", "confirmed": True, "source_quote": "User authentication is required"},
        ],
        "missing_information": ["Expected concurrent user load", "Hosting environment preferences"],
        "scope_constraints": ["6 weeks MVP deadline", "$40,000 budget"],
        "confidence": 0.90,
    }
    provider = make_mock_provider(raw_dict)
    service = ExtractionService(provider=provider)
    extraction = service.extract_requirements(brief)

    assert isinstance(extraction, ProjectExtraction)
    assert extraction.project_name == "Sales Analytics Dashboard"
    assert len(extraction.requirements) == 3
    assert all(r.confirmed for r in extraction.requirements)
    assert extraction.confidence >= 0.70
    assert len(extraction.scope_constraints) == 2


# ============================================================================
# 2. Short Project Brief (Partial Extraction + Missing Information)
# ============================================================================


def test_short_project_brief_extraction():
    """
    Short brief extracts requested capability and identifies important missing
    architectural dimensions.
    """
    brief = "We need an AI customer support chatbot for our e-commerce website."
    raw_dict = {
        "project_name": "E-Commerce Support Chatbot",
        "summary": "Customer support chatbot for assisting online store shoppers.",
        "requirements": [
            {"description": "AI customer support chatbot", "priority": "high", "confirmed": True, "source_quote": "AI customer support chatbot"},
            {"description": "Integration with e-commerce website", "priority": "medium", "confirmed": True, "source_quote": "e-commerce website"},
        ],
        "missing_information": [],
        "scope_constraints": [],
        "confidence": 0.75,
    }
    provider = make_mock_provider(raw_dict)
    extraction = extract_requirements(brief, provider=provider)

    assert extraction.project_name == "E-Commerce Support Chatbot"
    assert len(extraction.requirements) == 2
    # Missing information should actively identify critical architectural dimensions
    missing_text = " ".join(extraction.missing_information).lower()
    assert "user" in missing_text or "traffic" in missing_text or "hosting" in missing_text or "deployment" in missing_text


# ============================================================================
# 3. Extremely Vague Request (Low Confidence + Missing Information)
# ============================================================================


def test_extremely_vague_request_low_confidence():
    """
    Extremely vague input ('Build me an app.') produces low confidence (<= 0.35)
    and populates critical missing information.
    """
    brief = "Build me an app."
    raw_dict = {
        "project_name": "Custom Application",
        "summary": "Unspecified custom application requested by client.",
        "requirements": [
            {"description": "Application development", "priority": "high", "confirmed": False, "source_quote": None},
        ],
        "missing_information": ["Target platform (Web, iOS, Android)", "Core functionality"],
        "scope_constraints": [],
        "confidence": 0.90,  # Model mistakenly self-reports high confidence
    }
    provider = make_mock_provider(raw_dict)
    service = ExtractionService(provider=provider)
    extraction = service.extract_requirements(brief)

    # Confidence must be penalized for extreme vagueness
    assert extraction.confidence <= 0.35
    assert len(extraction.missing_information) >= 2


# ============================================================================
# 4. Explicit Technical Requirements Preserved
# ============================================================================


def test_explicit_technical_requirements_preserved():
    """
    Explicitly requested technical stacks (FastAPI, Redis, PostgreSQL) are preserved.
    """
    brief = "Build a Python FastAPI service with PostgreSQL database and Redis caching."
    raw_dict = {
        "project_name": "FastAPI Data Service",
        "summary": "High performance data API built with FastAPI, PostgreSQL, and Redis.",
        "requirements": [
            {"description": "Python FastAPI service", "priority": "high", "confirmed": True, "source_quote": "Python FastAPI service"},
            {"description": "PostgreSQL database storage", "priority": "high", "confirmed": True, "source_quote": "PostgreSQL database"},
            {"description": "Redis caching layer", "priority": "medium", "confirmed": True, "source_quote": "Redis caching"},
        ],
        "missing_information": [],
        "scope_constraints": [],
        "confidence": 0.88,
    }
    provider = make_mock_provider(raw_dict)
    extraction = extract_requirements(brief, provider=provider)

    descs = [r.description for r in extraction.requirements]
    assert any("FastAPI" in d or "fastapi" in d.lower() for d in descs)
    assert any("PostgreSQL" in d or "postgresql" in d.lower() for d in descs)
    assert any("Redis" in d or "redis" in d.lower() for d in descs)


# ============================================================================
# 5. Explicit Business Requirements Preserved
# ============================================================================


def test_explicit_business_requirements_preserved():
    """
    Functional and business objectives (customer questions, human escalation) are preserved.
    """
    brief = (
        "The chatbot should answer customer questions using our product information "
        "and escalate complex issues to human agents."
    )
    raw_dict = {
        "project_name": "Support Ticket Escalation Bot",
        "summary": "Customer service bot answering product FAQs with agent handoff.",
        "requirements": [
            {"description": "Answer customer questions using product information", "priority": "high", "confirmed": True, "source_quote": "answer customer questions"},
            {"description": "Escalate complex issues to human agents", "priority": "high", "confirmed": True, "source_quote": "escalate complex issues to human agents"},
        ],
        "missing_information": [],
        "scope_constraints": [],
        "confidence": 0.82,
    }
    provider = make_mock_provider(raw_dict)
    extraction = extract_requirements(brief, provider=provider)

    descs = [r.description.lower() for r in extraction.requirements]
    assert any("customer questions" in d for d in descs)
    assert any("escalate" in d or "human agent" in d for d in descs)


# ============================================================================
# 6. Existing Technologies Mentioned (Preserved Without Replacement)
# ============================================================================


def test_existing_technologies_preserved_without_replacement():
    """
    Client's existing stack (Firebase) is preserved and not replaced with alternatives.
    """
    brief = "We already use Firebase for authentication and database. We need a web portal."
    raw_dict = {
        "project_name": "Firebase Client Portal",
        "summary": "Web portal integrating with existing Firebase authentication and database.",
        "requirements": [
            {"description": "Web portal interface", "priority": "high", "confirmed": True, "source_quote": "web portal"},
            {"description": "Integration with existing Firebase auth and database", "priority": "high", "confirmed": True, "source_quote": "Firebase for authentication and database"},
        ],
        "missing_information": [],
        "scope_constraints": ["Existing Firebase infrastructure"],
        "confidence": 0.85,
    }
    provider = make_mock_provider(raw_dict)
    extraction = extract_requirements(brief, provider=provider)

    all_text = " ".join(r.description for r in extraction.requirements) + " " + " ".join(extraction.scope_constraints)
    assert "Firebase" in all_text or "firebase" in all_text.lower()
    # Confirm that unmentioned databases were not hallucinated
    assert "PostgreSQL" not in all_text
    assert "MongoDB" not in all_text


# ============================================================================
# 7. Missing Information (Critical vs Cosmetic Filtering)
# ============================================================================


def test_missing_information_filters_cosmetic_details():
    """
    Cosmetic details (colors, button copy, logos) are filtered out, and
    material delivery gaps (scale, hosting, timeline) are preserved.
    """
    brief = "We need an internal portal for employee time tracking."
    raw_missing = [
        "Primary brand button color scheme",
        "Company logo font preference",
        "Expected monthly active user scale",
        "Preferred cloud hosting provider",
    ]
    reqs = [Requirement(description="Employee time tracking portal", priority="high", confirmed=True)]

    filtered = filter_and_audit_missing_info(raw_missing, brief, reqs)

    # Cosmetic items removed
    assert not any("color" in item.lower() for item in filtered)
    assert not any("font" in item.lower() for item in filtered)

    # Material items preserved
    assert any("user" in item.lower() or "scale" in item.lower() for item in filtered)
    assert any("host" in item.lower() or "cloud" in item.lower() for item in filtered)


# ============================================================================
# 8. No Hallucination (Unspecified Technologies Not Treated As Facts)
# ============================================================================


def test_hallucination_audit_flags_unstated_technologies():
    """
    When the client requests a generic solution ('We need a chatbot'), but the LLM
    hallucinates specific technologies (React, PostgreSQL, AWS), they are marked
    unconfirmed (confirmed=False) and added to missing_information.
    """
    brief = "We need a simple customer chatbot."
    hallucinated = ProjectExtraction(
        project_name="AI Chatbot",
        summary="A customer support chatbot application.",
        requirements=[
            Requirement(
                description="React frontend for customer chat widget",
                priority="high",
                confirmed=True,  # Hallucinated as confirmed
                source_quote="simple customer chatbot",
            ),
            Requirement(
                description="PostgreSQL database to store conversation history",
                priority="medium",
                confirmed=True,  # Hallucinated as confirmed
                source_quote=None,
            ),
        ],
        missing_information=[],
        scope_constraints=[],
        confidence=0.85,
    )

    audited = audit_and_prevent_hallucinations(hallucinated, brief)

    # React and PostgreSQL were not mentioned in brief; confirmed must be set to False
    assert audited.requirements[0].confirmed is False
    assert audited.requirements[1].confirmed is False

    # Unstated tech preferences should be surfaced in missing_information
    missing_str = " ".join(audited.missing_information).lower()
    assert "react" in missing_str or "technology" in missing_str


# ============================================================================
# 9. Invalid LLM Output (Validation & Failure Path Works)
# ============================================================================


def test_invalid_llm_json_raises_extraction_error():
    """
    When the LLM provider returns unparseable or invalid output,
    a controlled ExtractionError is raised.
    """
    provider = MagicMock(spec=OllamaProvider)
    provider.extract_requirements.return_value = ExtractionResult(
        valid=False,
        error="LLM returned invalid JSON after retries",
        requires_manual_review=True,
    )

    service = ExtractionService(provider=provider)
    with pytest.raises(ExtractionError, match="invalid JSON"):
        service.extract_requirements("We need a dashboard.")


def test_schema_validation_error_raises_extraction_validation_error():
    """
    When LLM output is missing required fields (e.g. project_name missing),
    ExtractionValidationError is raised.
    """
    provider = MagicMock(spec=OllamaProvider)
    provider.extract_requirements.return_value = ExtractionResult(
        valid=False,
        error="Missing or invalid fields: project_name: Field required",
        requires_manual_review=True,
    )

    service = ExtractionService(provider=provider)
    with pytest.raises(ExtractionValidationError, match="project_name"):
        service.extract_requirements("We need a dashboard.")


# ============================================================================
# 10. Empty Input (Controlled Validation Error)
# ============================================================================


def test_empty_input_raises_controlled_value_error():
    """Empty or whitespace project briefs raise a controlled ValueError."""
    service = ExtractionService()

    with pytest.raises(ValueError, match="Project brief cannot be empty"):
        service.extract_requirements("")

    with pytest.raises(ValueError, match="Project brief cannot be empty"):
        service.extract_requirements("     ")

    with pytest.raises(ValueError, match="Project brief cannot be empty"):
        service.extract_requirements(None)


# ============================================================================
# 11. Confidence Value Always Between 0.0 and 1.0
# ============================================================================


@pytest.mark.parametrize(
    "brief,initial_conf",
    [
        ("Build an app.", 0.95),
        ("Build an app.", 0.10),
        ("Quick fix.", 0.0),
        ("We need an internal React dashboard with Python FastAPI and PostgreSQL for tracking hours.", 0.92),
        ("Complex multi-tenant healthcare EHR integration platform with HIPAA compliance and AWS cloud deployment.", 0.85),
    ],
)
def test_confidence_always_clamped_between_zero_and_one(brief, initial_conf):
    """
    Ensures that under all brief lengths and initial scores,
    confidence remains strictly 0.0 <= confidence <= 1.0.
    """
    extraction = ProjectExtraction(
        project_name="Test Project",
        summary="A test project summary for verifying confidence score boundaries.",
        requirements=[
            Requirement(description="Sample requirement description", priority="medium", confirmed=True)
        ],
        missing_information=["Sample missing question"],
        scope_constraints=[],
        confidence=initial_conf,
    )

    conf = calculate_extraction_confidence(brief, extraction)
    assert 0.0 <= conf <= 1.0
