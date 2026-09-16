# tests/test_groq_provider.py
import json
from unittest.mock import patch, MagicMock
import pytest
import requests

from app.config import settings
from app.models import (
    RawBrief,
    ProjectExtraction,
    ExtractionResult,
    extraction_is_usable,
)
from app.providers.base import BaseLLMProvider
from app.providers.groq import (
    GroqProvider,
    GroqClient,
    GroqProviderError,
    GroqAuthenticationError,
    GroqConnectionError,
    GroqTimeoutError,
    GroqRateLimitError,
    GroqServerError,
    mask_api_key,
)
from app.providers.ollama import OllamaProvider
from app.providers import get_llm_provider
from app.orchestrator import IntakeOrchestrator
from app.services.extraction import ExtractionService
from app.storage.db import init_db


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


@pytest.fixture
def groq_provider():
    """Create default GroqProvider with a dummy test API key."""
    return GroqProvider(
        api_key="gsk_test_mock_api_key_12345",
        model="llama-3.3-70b-versatile",
        base_url="https://api.groq.com/openai/v1",
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


def make_mock_groq_response(content: str, status_code: int = 200) -> MagicMock:
    """Helper to create a mock requests.Response for Groq chat completions."""
    mock_resp = MagicMock(spec=requests.Response)
    mock_resp.status_code = status_code
    mock_resp.json.return_value = {
        "id": "chatcmpl-mock-groq-id",
        "object": "chat.completion",
        "created": 1720000000,
        "model": "llama-3.3-70b-versatile",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 120,
            "completion_tokens": 80,
            "total_tokens": 200,
        },
    }
    return mock_resp


# ============================================================================
# 1. Successful Groq Request & Extraction
# ============================================================================

def test_successful_groq_request(groq_provider, sample_valid_brief, sample_extraction_dict):
    """Verify successful requirement extraction through GroqProvider."""
    content = json.dumps(sample_extraction_dict)
    mock_resp = make_mock_groq_response(content)

    with patch.object(groq_provider.client.session, "post", return_value=mock_resp) as mock_post:
        result = groq_provider.extract_requirements(sample_valid_brief)

        assert result.valid is True
        assert result.extraction is not None
        assert result.extraction.project_name == "Employee Dashboard"
        assert len(result.extraction.requirements) == 3
        assert result.extraction.confidence == 0.92
        assert result.requires_manual_review is False
        assert result.retry_count == 0

        # Verify call arguments
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert "https://api.groq.com/openai/v1/chat/completions" in args[0]
        assert kwargs["headers"]["Authorization"] == "Bearer gsk_test_mock_api_key_12345"
        assert kwargs["json"]["model"] == "llama-3.3-70b-versatile"
        assert kwargs["json"]["response_format"] == {"type": "json_object"}


def test_groq_generate_returns_raw_string(groq_provider):
    """Verify general-purpose generate() returns raw completion content."""
    mock_resp = make_mock_groq_response("Hello from Groq LLM")
    with patch.object(groq_provider.client.session, "post", return_value=mock_resp):
        output = groq_provider.generate("Say hello")
        assert output == "Hello from Groq LLM"


# ============================================================================
# 2. Groq Response Parsing
# ============================================================================

def test_groq_response_parsing_markdown_code_fences(groq_provider, sample_valid_brief, sample_extraction_dict):
    """Verify parsing when Groq returns JSON wrapped in markdown code blocks."""
    content = f"```json\n{json.dumps(sample_extraction_dict)}\n```"
    mock_resp = make_mock_groq_response(content)

    with patch.object(groq_provider.client.session, "post", return_value=mock_resp):
        result = groq_provider.extract_requirements(sample_valid_brief)
        assert result.valid is True
        assert result.extraction.project_name == "Employee Dashboard"


def test_groq_response_parsing_conversational_prose(groq_provider, sample_valid_brief, sample_extraction_dict):
    """Verify parsing when Groq includes conversational text before and after the JSON."""
    content = f"Here is the project extraction you requested:\n\n{json.dumps(sample_extraction_dict)}\n\nI hope this helps!"
    mock_resp = make_mock_groq_response(content)

    with patch.object(groq_provider.client.session, "post", return_value=mock_resp):
        result = groq_provider.extract_requirements(sample_valid_brief)
        assert result.valid is True
        assert result.extraction.project_name == "Employee Dashboard"


# ============================================================================
# 3. Missing API Key
# ============================================================================

def test_missing_groq_api_key_returns_user_friendly_error(sample_valid_brief):
    """Missing or empty GROQ_API_KEY must fail gracefully with user-friendly message."""
    provider_no_key = GroqProvider(api_key="")
    result = provider_no_key.extract_requirements(sample_valid_brief)

    assert result.valid is False
    assert result.extraction is None
    assert result.requires_manual_review is True
    assert "GROQ_API_KEY" in result.user_message
    assert "gsk_" not in str(result)
    assert result.error == "Groq API key not configured"


def test_groq_client_raises_authentication_error_when_key_is_empty():
    """GroqClient raises GroqAuthenticationError when called without an API key."""
    client = GroqClient(api_key="")
    with pytest.raises(GroqAuthenticationError, match="GROQ_API_KEY is not configured"):
        client.chat_completion(messages=[{"role": "user", "content": "hi"}])


def test_mask_api_key_utility():
    """Ensure API key masking protects secrets."""
    assert mask_api_key("") == "<unset>"
    assert mask_api_key(None) == "<unset>"
    assert mask_api_key("12345") == "***"
    masked = mask_api_key("gsk_supersecretkey123456789")
    assert masked.startswith("gsk_")
    assert masked.endswith("6789")
    assert "supersecret" not in masked


# ============================================================================
# 4. Groq API Failure (Status Codes, Timeouts, Connection Errors)
# ============================================================================

def test_groq_api_401_unauthorized(groq_provider, sample_valid_brief):
    """401 Invalid API key returns friendly authentication error."""
    mock_resp = MagicMock(spec=requests.Response)
    mock_resp.status_code = 401
    mock_resp.text = '{"error": {"message": "Invalid API Key"}}'

    with patch.object(groq_provider.client.session, "post", return_value=mock_resp):
        result = groq_provider.extract_requirements(sample_valid_brief)
        assert result.valid is False
        assert "authentication error" in result.user_message.lower()
        assert result.requires_manual_review is True
        assert "Invalid API Key" not in result.user_message


def test_groq_api_429_rate_limit(groq_provider, sample_valid_brief):
    """429 Rate limit returns user-friendly busy message."""
    mock_resp = MagicMock(spec=requests.Response)
    mock_resp.status_code = 429
    mock_resp.text = '{"error": {"message": "Rate limit reached"}}'

    with patch.object(groq_provider.client.session, "post", return_value=mock_resp):
        result = groq_provider.extract_requirements(sample_valid_brief)
        assert result.valid is False
        assert "rate limits" in result.user_message.lower()
        assert result.requires_manual_review is True


def test_groq_api_500_server_error(groq_provider, sample_valid_brief):
    """500 Internal Server Error fails gracefully."""
    mock_resp = MagicMock(spec=requests.Response)
    mock_resp.status_code = 500
    mock_resp.text = '{"error": "Internal Server Error"}'

    with patch.object(groq_provider.client.session, "post", return_value=mock_resp):
        result = groq_provider.extract_requirements(sample_valid_brief)
        assert result.valid is False
        assert result.requires_manual_review is True
        assert "Error communicating with AI service" in result.user_message


def test_groq_timeout_handling(groq_provider, sample_valid_brief):
    """Request timeout returns slow system message."""
    with patch.object(groq_provider.client.session, "post", side_effect=requests.exceptions.Timeout("Timed out")):
        result = groq_provider.extract_requirements(sample_valid_brief)
        assert result.valid is False
        assert "AI system is slow. Please try again." in result.user_message
        assert result.requires_manual_review is True


def test_groq_connection_error_handling(groq_provider, sample_valid_brief):
    """Connection failure returns friendly connection error."""
    with patch.object(groq_provider.client.session, "post", side_effect=requests.exceptions.ConnectionError("DNS failure")):
        result = groq_provider.extract_requirements(sample_valid_brief)
        assert result.valid is False
        assert "network connection" in result.user_message.lower()
        assert result.requires_manual_review is True


# ============================================================================
# 5. Invalid / Malformed Groq Response (Retries & Failure)
# ============================================================================

def test_groq_invalid_json_recovers_on_retry(groq_provider, sample_valid_brief, sample_extraction_dict):
    """Groq invalid JSON recovers on retry when valid JSON is returned on attempt 2."""
    bad_resp = make_mock_groq_response("This is completely unparseable garbage {")
    good_resp = make_mock_groq_response(json.dumps(sample_extraction_dict))

    with patch.object(groq_provider.client.session, "post", side_effect=[bad_resp, good_resp]):
        result = groq_provider.extract_requirements(sample_valid_brief)
        assert result.valid is True
        assert result.extraction.project_name == "Employee Dashboard"
        assert result.retry_count == 1


def test_groq_invalid_json_exhausts_retries(groq_provider, sample_valid_brief):
    """Groq invalid JSON exhausts all retries and flags for human review."""
    bad_resp = make_mock_groq_response("Not JSON at all")

    with patch.object(groq_provider.client.session, "post", return_value=bad_resp):
        result = groq_provider.extract_requirements(sample_valid_brief)
        assert result.valid is False
        assert result.requires_manual_review is True
        assert "couldn't confidently extract" in result.user_message.lower()


def test_groq_missing_required_fields_recovers_on_retry(groq_provider, sample_valid_brief, sample_extraction_dict):
    """Groq missing fields recovers on retry."""
    incomplete_dict = {"project_name": "Incomplete"}  # missing summary, requirements, confidence
    bad_resp = make_mock_groq_response(json.dumps(incomplete_dict))
    good_resp = make_mock_groq_response(json.dumps(sample_extraction_dict))

    with patch.object(groq_provider.client.session, "post", side_effect=[bad_resp, good_resp]):
        result = groq_provider.extract_requirements(sample_valid_brief)
        assert result.valid is True
        assert result.retry_count == 1


def test_groq_empty_brief_input(groq_provider):
    """Empty or whitespace brief returns immediate validation message without calling API."""
    with patch.object(groq_provider.client.session, "post") as mock_post:
        result = groq_provider.extract_requirements("   ")
        assert result.valid is False
        assert result.user_message == "Please provide a project brief."
        mock_post.assert_not_called()


# ============================================================================
# 6. Provider Selection Defaults to Groq
# ============================================================================

def test_provider_selection_defaults_to_groq():
    """get_llm_provider() defaults to GroqProvider as primary provider."""
    provider = get_llm_provider()
    assert isinstance(provider, GroqProvider)
    assert isinstance(provider, BaseLLMProvider)
    assert provider.provider_name == "groq"


def test_provider_selection_honors_ollama_setting():
    """get_llm_provider('ollama') returns OllamaProvider."""
    provider = get_llm_provider("ollama")
    assert isinstance(provider, OllamaProvider)
    assert isinstance(provider, BaseLLMProvider)
    assert provider.provider_name == "ollama"


def test_provider_selection_unknown_defaults_to_groq():
    """Unknown provider name logs warning and falls back to Groq."""
    provider = get_llm_provider("unsupported_provider_xyz")
    assert isinstance(provider, GroqProvider)
    assert provider.provider_name == "groq"


def test_orchestrator_defaults_to_groq():
    """IntakeOrchestrator() without args initializes with GroqProvider."""
    orchestrator = IntakeOrchestrator()
    assert isinstance(orchestrator.llm, GroqProvider)
    assert orchestrator.llm.provider_name == "groq"


def test_extraction_service_defaults_to_groq():
    """ExtractionService() without args initializes with GroqProvider."""
    service = ExtractionService()
    assert isinstance(service.provider, GroqProvider)
    assert service.provider.provider_name == "groq"


# ============================================================================
# 7. Existing Ollama Provider Still Works
# ============================================================================

def test_ollama_provider_still_works_under_base_interface():
    """Verify OllamaProvider satisfies BaseLLMProvider contract and works as expected."""
    ollama = OllamaProvider(base_url="http://localhost:11434", model="mistral")
    assert isinstance(ollama, BaseLLMProvider)
    assert ollama.provider_name == "ollama"

    # Verify check_health works
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        assert ollama.check_health() is True

        mock_get.side_effect = requests.RequestException("offline")
        assert ollama.check_health() is False


# ============================================================================
# 8. Existing Extraction Gating Behavior Remains Unchanged With Groq
# ============================================================================

def test_groq_extraction_failure_blocks_implementation_checklist(sample_valid_brief):
    """
    Ensure Groq extraction failures trigger extraction gating:
    - Checklist generated is marked 'clarification'
    - No implementation tasks generated
    - Human review required
    """
    groq = GroqProvider(api_key="gsk_mock_test")
    # Simulate failed extraction (e.g. rate limit / network error)
    failed_result = ExtractionResult(
        valid=False,
        error="Groq rate limit exceeded",
        user_message="AI system is temporarily busy due to rate limits. Please try again in a moment.",
        requires_manual_review=True,
        review_notes="Groq rate limit (HTTP 429) exceeded.",
    )

    with patch.object(groq, "extract_requirements", return_value=failed_result):
        orchestrator = IntakeOrchestrator(provider=groq)
        pending = orchestrator.process_brief(RawBrief(brief_text=sample_valid_brief))

        # 1. Gate blocked implementation checklist
        assert pending.checklist.checklist_type == "clarification"
        assert pending.checklist.type == "clarification"
        assert pending.requires_manual_review is True

        # 2. Checklist tasks are clarification tasks
        tasks = [item.task.lower() for item in pending.checklist.items]
        assert any("clarify" in t or "identify" in t or "define" in t for t in tasks)

        # 3. No Groq errors leaked into checklist tasks
        for t in tasks:
            assert "groq" not in t
            assert "rate limit" not in t
            assert "429" not in t
            assert "api key" not in t


def test_groq_health_check_online_and_offline():
    """Verify GroqProvider health check endpoint handling."""
    provider = GroqProvider(api_key="gsk_test_key", base_url="https://api.groq.com/openai/v1")

    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        assert provider.check_health() is True

        mock_get.return_value.status_code = 401
        assert provider.check_health() is False

        mock_get.side_effect = Exception("network error")
        assert provider.check_health() is False

    # Without API key, health check returns False immediately
    provider_no_key = GroqProvider(api_key="")
    assert provider_no_key.check_health() is False
