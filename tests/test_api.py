import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_brief_returns_pending_intake():
    response = client.post(
        "/briefs",
        json={"brief_text": "We need a React frontend with Python backend..."}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"]
    assert data["status"] == "pending_review"

def test_get_brief_returns_intake():
    # First create
    create_response = client.post(
        "/briefs",
        json={"brief_text": "We need a React frontend with Python backend..."}
    )
    brief_id = create_response.json()["id"]
    
    # Then retrieve
    get_response = client.get(f"/briefs/{brief_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == brief_id

def test_approve_brief_transitions_status():
    # Create
    create_response = client.post(
        "/briefs",
        json={"brief_text": "We need a React frontend with Python backend..."}
    )
    brief_id = create_response.json()["id"]
    
    # Approve
    approve_response = client.post(f"/briefs/{brief_id}/approve")
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"

def test_get_nonexistent_brief_returns_404():
    response = client.get("/briefs/doesnotexist")
    assert response.status_code == 404

def test_mark_issues_flags_problems():
    # Create
    create_response = client.post(
        "/briefs",
        json={"brief_text": "We need a portal for tracking employee hours."}
    )
    brief_id = create_response.json()["id"]

    # Mark issues with list format
    issues = ["Database technology not specified", "Timeline is unclear"]
    flag_response = client.post(
        f"/briefs/{brief_id}/mark-issues",
        json=issues
    )
    assert flag_response.status_code == 200
    assert flag_response.json()["status"] == "flagged"
    assert flag_response.json()["id"] == brief_id


def test_mark_issues_with_dict_payload():
    # Create
    create_response = client.post(
        "/briefs",
        json={"brief_text": "We need a portal for tracking employee hours."}
    )
    brief_id = create_response.json()["id"]

    # Mark issues with dict format {"issues": [...]}
    flag_response = client.post(
        f"/briefs/{brief_id}/mark-issues",
        json={"issues": ["Needs clarifying architecture spec"]}
    )
    assert flag_response.status_code == 200
    assert flag_response.json()["status"] == "flagged"
    assert flag_response.json()["id"] == brief_id


def test_openapi_and_docs_endpoints():
    docs_resp = client.get("/docs")
    assert docs_resp.status_code == 200
    openapi_resp = client.get("/openapi.json")
    assert openapi_resp.status_code == 200


# ============================================================================
# User-Friendly Error Messages & Traceback Suppression Tests
# ============================================================================

def test_validation_failure_returns_user_friendly_message():
    """When brief is invalid or too short (< 10 chars), returns friendly error and no traceback."""
    response = client.post("/briefs", json={"brief_text": "short"})
    assert response.status_code == 400
    data = response.json()
    assert data["detail"] == "This brief is unclear. Please provide more specific details."
    assert "Traceback" not in response.text
    assert "Traceback (most recent call last)" not in response.text


def test_empty_brief_returns_user_friendly_message():
    """When brief text is empty or missing, returns friendly error without traceback."""
    response = client.post("/briefs", json={"brief_text": ""})
    assert response.status_code == 400
    data = response.json()
    assert data["detail"] == "This brief is unclear. Please provide more specific details."
    assert "Traceback" not in response.text


def test_ollama_offline_displays_user_friendly_message():
    """When Ollama is offline / connection refused, returns friendly message with no traceback."""
    from unittest.mock import patch
    from app.models import ExtractionResult

    offline_result = ExtractionResult(
        valid=False,
        error="Ollama connection refused",
        user_message="AI system unavailable. Please ensure Ollama is running on http://localhost:11434",
        requires_manual_review=True,
        review_notes="AI system unavailable. Please ensure Ollama is running on http://localhost:11434",
    )

    with patch("app.services.extraction.ExtractionService.extract", return_value=offline_result):
        response = client.post(
            "/briefs",
            json={"brief_text": "We need an inventory management web app with Python backend."}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["requires_manual_review"] is True
        assert "AI system unavailable. Please ensure Ollama is running on http://localhost:11434" in data["extracted"]["summary"]
        assert "AI system unavailable. Please ensure Ollama is running on http://localhost:11434" in data["review_notes"]
        assert "Traceback" not in response.text


def test_extraction_failure_displays_user_friendly_message():
    """When LLM extraction fails, returns friendly clarification message with no traceback."""
    from unittest.mock import patch
    from app.models import ExtractionResult

    fail_result = ExtractionResult(
        valid=False,
        error="LLM returned invalid JSON after retries",
        user_message=(
            "We couldn't confidently extract requirements from this brief. \n"
            "Could you add more details about: Technology preferences, Timeline, Budget"
        ),
        requires_manual_review=True,
        review_notes="LLM output could not be parsed as valid JSON after retries.",
    )

    with patch("app.services.extraction.ExtractionService.extract", return_value=fail_result):
        response = client.post(
            "/briefs",
            json={"brief_text": "We need something built but we have zero technical details."}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["requires_manual_review"] is True
        assert "We couldn't confidently extract requirements from this brief." in data["extracted"]["summary"]
        assert "Technology preferences, Timeline, Budget" in data["extracted"]["summary"]
        assert "Technology preferences" in data["extracted"]["missing_information"]
        assert "Timeline" in data["extracted"]["missing_information"]
        assert "Budget" in data["extracted"]["missing_information"]
        assert "Traceback" not in response.text


def test_unhandled_server_exception_returns_clean_message_without_traceback():
    """When unexpected exception occurs, global exception handler formats friendly 500 error."""
    from unittest.mock import patch

    with patch("app.main.orchestrator.process_brief", side_effect=RuntimeError("Internal system crash")):
        response = client.post(
            "/briefs",
            json={"brief_text": "We need a standard React and Python web application."}
        )
        assert response.status_code == 500
        data = response.json()
        assert "We couldn't confidently extract requirements from this brief." in data["detail"]
        assert "Traceback" not in response.text
        assert "Traceback (most recent call last)" not in response.text