# tests/test_ollama_provider.py
import json
from unittest.mock import patch, MagicMock
import pytest
import requests

from app.config import settings
from app.models import ProjectExtraction, ExtractionResult
from app.providers.ollama import (
    OllamaProvider,
    clean_and_parse_json,
)


@pytest.fixture
def provider():
    """Create default OllamaProvider for testing"""
    return OllamaProvider(
        base_url="http://localhost:11434",
        model="mistral",
        timeout=30,
        max_retries=1,
    )


@pytest.fixture
def sample_valid_brief():
    return (
        "We need a React frontend with Python backend for an employee dashboard. "
        "Timeline: 6 weeks. Budget: $50,000. It must track hours and projects."
    )


@pytest.fixture
def sample_extraction_dict():
    return {
        "project_name": "Employee Dashboard",
        "summary": "Internal tool for tracking employee projects and work hours over 6 weeks.",
        "requirements": [
            {
                "description": "React frontend",
                "priority": "high",
                "confirmed": True,
                "source_quote": "We need a React frontend",
            },
            {
                "description": "Python backend API",
                "priority": "high",
                "confirmed": True,
                "source_quote": "Python backend",
            },
            {
                "description": "Track hours and projects",
                "priority": "medium",
                "confirmed": True,
                "source_quote": "It must track hours and projects",
            },
        ],
        "missing_information": [
            "Number of expected users",
            "Hosting requirements",
        ],
        "scope_constraints": ["6 weeks timeline", "$50,000 budget"],
        "confidence": 0.92,
    }


def make_mock_ollama_response(content: str, status_code: int = 200):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = {"response": content, "done": True}
    mock_resp.raise_for_status.return_value = None
    return mock_resp


# ============================================================================
# 1. JSON Parser & Markdown Stripping Tests
# ============================================================================


def test_clean_and_parse_raw_json():
    raw = '{"project_name": "Test Project", "confidence": 0.9}'
    parsed = clean_and_parse_json(raw)
    assert parsed["project_name"] == "Test Project"
    assert parsed["confidence"] == 0.9


def test_clean_and_parse_markdown_fence():
    raw = """Here is the extracted JSON:
```json
{
  "project_name": "Test Project",
  "confidence": 0.85
}
```
Hope this helps!"""
    parsed = clean_and_parse_json(raw)
    assert parsed["project_name"] == "Test Project"
    assert parsed["confidence"] == 0.85


def test_clean_and_parse_surrounding_prose_without_fences():
    raw = 'Sure, here is the result: {"project_name": "Test Project", "confidence": 0.8} Thanks!'
    parsed = clean_and_parse_json(raw)
    assert parsed["project_name"] == "Test Project"


def test_clean_and_parse_empty_string_raises():
    with pytest.raises(ValueError, match="Empty response"):
        clean_and_parse_json("")


def test_clean_and_parse_invalid_syntax_raises():
    with pytest.raises(json.JSONDecodeError):
        clean_and_parse_json("Definitely not json at all")


# ============================================================================
# 2. Successful Extraction Scenario
# ============================================================================


def test_extract_requirements_success(provider, sample_valid_brief, sample_extraction_dict):
    mock_resp = make_mock_ollama_response(json.dumps(sample_extraction_dict))

    with patch("requests.post", return_value=mock_resp) as mock_post:
        result = provider.extract_requirements(sample_valid_brief)

        assert result.valid is True
        assert bool(result) is True
        assert result.requires_manual_review is False
        assert result.review_notes is None
        assert result.error is None
        assert result.retry_count == 0

        # Model properties
        assert result.project_name == "Employee Dashboard"
        assert len(result.requirements) == 3
        assert result.confidence == 0.92
        assert len(result.scope_constraints) == 2

        # Verify Ollama was called with expected payload
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["json"]["model"] == "mistral"
        assert call_kwargs["json"]["format"] == "json"
        assert "Employee Dashboard" in str(mock_resp.json())


# ============================================================================
# 3. Scenario 1: Invalid JSON (Retry once -> manual review)
# ============================================================================


def test_scenario_1_invalid_json_recovers_on_retry(
    provider, sample_valid_brief, sample_extraction_dict
):
    """First attempt returns invalid JSON; retry returns valid JSON."""
    invalid_resp = make_mock_ollama_response("Sorry, I cannot format this as JSON.")
    valid_resp = make_mock_ollama_response(json.dumps(sample_extraction_dict))

    with patch("requests.post", side_effect=[invalid_resp, valid_resp]) as mock_post:
        result = provider.extract_requirements(sample_valid_brief)

        assert result.valid is True
        assert result.retry_count == 1
        assert result.project_name == "Employee Dashboard"
        assert mock_post.call_count == 2

        # Verify second call included correction prompt
        second_prompt = mock_post.call_args_list[1].kwargs["json"]["prompt"]
        assert "CRITICAL CORRECTION REQUIRED" in second_prompt


def test_scenario_1_invalid_json_exhausts_retries(provider, sample_valid_brief):
    """Both attempts return invalid JSON; flags for manual review."""
    invalid_resp1 = make_mock_ollama_response("Malformed { broken json")
    invalid_resp2 = make_mock_ollama_response("Still not valid JSON")

    with patch("requests.post", side_effect=[invalid_resp1, invalid_resp2]) as mock_post:
        result = provider.extract_requirements(sample_valid_brief)

        assert result.valid is False
        assert bool(result) is False
        assert result.requires_manual_review is True
        assert "LLM returned invalid JSON after retries" in result.error
        assert "AI output format was invalid" in result.user_message
        assert mock_post.call_count == 2


# ============================================================================
# 4. Scenario 2: Missing Required Fields / Pydantic Validation Error
# ============================================================================


def test_scenario_2_missing_fields_recovers_on_retry(
    provider, sample_valid_brief, sample_extraction_dict
):
    """First attempt is missing 'requirements'; retry provides complete schema."""
    incomplete_dict = {
        "project_name": "Employee Dashboard",
        "summary": "Internal dashboard for tracking hours.",
        # Missing 'requirements' key
        "confidence": 0.9,
    }
    incomplete_resp = make_mock_ollama_response(json.dumps(incomplete_dict))
    valid_resp = make_mock_ollama_response(json.dumps(sample_extraction_dict))

    with patch("requests.post", side_effect=[incomplete_resp, valid_resp]) as mock_post:
        result = provider.extract_requirements(sample_valid_brief)

        assert result.valid is True
        assert result.retry_count == 1
        assert result.project_name == "Employee Dashboard"
        assert mock_post.call_count == 2

        # Check correction prompt noted the validation failure
        second_prompt = mock_post.call_args_list[1].kwargs["json"]["prompt"]
        assert "requirements" in second_prompt


def test_scenario_2_missing_fields_exhausts_retries(provider, sample_valid_brief):
    """Both attempts fail schema validation; flags for manual review."""
    incomplete_dict = {
        "project_name": "No requirements project",
        "summary": "Valid length summary here but missing requirements.",
        # missing requirements
        "confidence": 0.9,
    }
    resp1 = make_mock_ollama_response(json.dumps(incomplete_dict))
    resp2 = make_mock_ollama_response(json.dumps(incomplete_dict))

    with patch("requests.post", side_effect=[resp1, resp2]) as mock_post:
        result = provider.extract_requirements(sample_valid_brief)

        assert result.valid is False
        assert result.requires_manual_review is True
        assert "Missing or invalid fields" in result.error
        assert "requirements" in result.error
        assert "incomplete or missing required fields" in result.user_message
        assert mock_post.call_count == 2


# ============================================================================
# 5. Scenario 3: Hallucinated Requirements / Low Confidence
# ============================================================================


def test_scenario_3_low_confidence_flags_manual_review(
    provider, sample_valid_brief, sample_extraction_dict
):
    """Confidence 0.55 < threshold (0.7); marks valid=True but requires_manual_review=True."""
    sample_extraction_dict["confidence"] = 0.55
    mock_resp = make_mock_ollama_response(json.dumps(sample_extraction_dict))

    with patch("requests.post", return_value=mock_resp):
        result = provider.extract_requirements(sample_valid_brief)

        assert result.valid is True
        assert result.requires_manual_review is True
        assert "Confidence score (0.55) is below threshold" in result.review_notes
        assert "Confidence below threshold" in result.user_message


def test_scenario_3_unconfirmed_requirements_flag_manual_review(
    provider, sample_valid_brief, sample_extraction_dict
):
    """Unconfirmed/inferred requirements flag manual review."""
    sample_extraction_dict["requirements"][0]["confirmed"] = False  # Inferred
    mock_resp = make_mock_ollama_response(json.dumps(sample_extraction_dict))

    with patch("requests.post", return_value=mock_resp):
        result = provider.extract_requirements(sample_valid_brief)

        assert result.valid is True
        assert result.requires_manual_review is True
        assert "inferred requirement(s) requiring human verification" in result.review_notes


# ============================================================================
# 6. Scenario 4: Timeout (No response in 30 seconds)
# ============================================================================


def test_scenario_4_timeout_handling(provider, sample_valid_brief):
    """Request times out; returns user-friendly slow message and review flag."""
    with patch("requests.post", side_effect=requests.exceptions.Timeout("Read timed out")):
        result = provider.extract_requirements(sample_valid_brief)

        assert result.valid is False
        assert result.requires_manual_review is True
        assert result.user_message == "AI system is slow. Please try again."
        assert "LLM timeout" in result.error


# ============================================================================
# 7. Scenario 5: Ollama Offline (Connection Refused)
# ============================================================================


def test_scenario_5_ollama_offline_connection_refused(provider, sample_valid_brief):
    """Ollama daemon is offline; returns user-friendly offline message and review flag."""
    with patch(
        "requests.post",
        side_effect=requests.exceptions.ConnectionError("Connection refused to localhost:11434"),
    ):
        result = provider.extract_requirements(sample_valid_brief)

        assert result.valid is False
        assert result.requires_manual_review is True
        assert (
            result.user_message
            == "AI system unavailable. Please ensure Ollama is running."
        )
        assert "Ollama connection refused" in result.error


# ============================================================================
# 8. Edge Cases & Additional Capabilities
# ============================================================================


def test_empty_brief_input(provider):
    """Empty or whitespace input does not call Ollama and returns early."""
    with patch("requests.post") as mock_post:
        result = provider.extract_requirements("   ")

        assert result.valid is False
        assert result.error == "Project brief is empty"
        assert result.user_message == "Please provide a project brief."
        assert result.requires_manual_review is False
        mock_post.assert_not_called()


def test_check_health_online(provider):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    with patch("requests.get", return_value=mock_resp):
        assert provider.check_health() is True


def test_check_health_offline(provider):
    with patch(
        "requests.get",
        side_effect=requests.exceptions.ConnectionError("Connection refused"),
    ):
        assert provider.check_health() is False


def test_generate_general_prompt(provider):
    mock_resp = make_mock_ollama_response('{"result": "ok"}')
    with patch("requests.post", return_value=mock_resp) as mock_post:
        output = provider.generate("Recommend a team for this project")
        assert output == '{"result": "ok"}'
        mock_post.assert_called_once()
