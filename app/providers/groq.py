# app/providers/groq.py
import json
import logging
import re
from pathlib import Path
from typing import Optional, Dict, Any, List, Union

import requests
from pydantic import ValidationError

from app.config import settings
from app.models import (
    ProjectExtraction,
    Requirement,
    ExtractionResult,
)
from app.providers.base import BaseLLMProvider
from app.providers.ollama import clean_and_parse_json

logger = logging.getLogger(__name__)

# Base project directory for loading prompt templates
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class GroqProviderError(Exception):
    """Base exception for Groq provider errors."""
    pass


class GroqAuthenticationError(GroqProviderError):
    """Raised when GROQ_API_KEY is missing, invalid, or unauthorized (HTTP 401)."""
    pass


class GroqConnectionError(GroqProviderError):
    """Raised when unable to establish a connection to Groq API."""
    pass


class GroqTimeoutError(GroqProviderError):
    """Raised when a request to Groq API times out."""
    pass


class GroqRateLimitError(GroqProviderError):
    """Raised when Groq API rate limit is exceeded (HTTP 429)."""
    pass


class GroqServerError(GroqProviderError):
    """Raised when Groq server returns 5xx error."""
    pass


def mask_api_key(api_key: Optional[str]) -> str:
    """Mask an API key for safe logging (e.g. 'gsk_...1234')."""
    if not api_key:
        return "<unset>"
    key_clean = api_key.strip()
    if len(key_clean) <= 8:
        return "***"
    return f"{key_clean[:4]}...{key_clean[-4:]}"


class GroqClient:
    """
    Low-level client for Groq Cloud API (OpenAI-compatible Chat Completions endpoint).
    Handles authentication, headers, timeouts, and HTTP status codes cleanly.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 30,
        session: Optional[requests.Session] = None,
    ):
        self.api_key = (api_key if api_key is not None else settings.GROQ_API_KEY).strip()
        self.base_url = (base_url or settings.GROQ_BASE_URL).rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        response_format: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Send a chat completion request to the Groq API.

        Args:
            messages: List of message dictionaries with 'role' and 'content'.
            model: Target model name.
            temperature: Sampling temperature (default 0.2 for deterministic output).
            response_format: Optional response format (e.g. {"type": "json_object"}).
            timeout: Request timeout in seconds.

        Returns:
            Parsed JSON dictionary response from Groq.

        Raises:
            GroqAuthenticationError: If API key is missing or invalid.
            GroqConnectionError: If network connection fails.
            GroqTimeoutError: If request times out.
            GroqRateLimitError: If HTTP 429 rate limit is received.
            GroqServerError: If Groq returns HTTP 5xx.
            GroqProviderError: On other API errors.
        """
        if not self.api_key:
            raise GroqAuthenticationError("GROQ_API_KEY is not configured or is empty")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "AI-Project-Intake-Pipeline/1.0",
        }
        payload: Dict[str, Any] = {
            "model": model or settings.GROQ_MODEL,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format:
            payload["response_format"] = response_format

        call_timeout = timeout if timeout is not None else self.timeout

        try:
            logger.debug("Dispatching chat completion request to Groq (%s)", url)
            response = self.session.post(
                url,
                json=payload,
                headers=headers,
                timeout=call_timeout,
            )
        except requests.exceptions.Timeout as te:
            logger.error("Groq request timed out after %ds", call_timeout)
            raise GroqTimeoutError(f"Groq API request timed out after {call_timeout}s") from te
        except requests.exceptions.ConnectionError as ce:
            logger.error("Groq connection failed at %s", self.base_url)
            raise GroqConnectionError("Failed to connect to Groq API endpoint") from ce
        except requests.exceptions.RequestException as re_err:
            logger.error("Groq HTTP request exception: %s", re_err)
            raise GroqProviderError(f"Groq HTTP request failed: {re_err}") from re_err

        # Check HTTP status codes
        if response.status_code == 401 or response.status_code == 403:
            logger.error("Groq authentication failed (status=%d)", response.status_code)
            raise GroqAuthenticationError("Groq authentication failed (invalid or unauthorized API key)")
        elif response.status_code == 429:
            logger.warning("Groq rate limit exceeded (HTTP 429)")
            raise GroqRateLimitError("Groq rate limit exceeded. Please try again later.")
        elif response.status_code >= 500:
            logger.error("Groq server error (HTTP %d)", response.status_code)
            raise GroqServerError(f"Groq server returned HTTP {response.status_code}")
        elif response.status_code != 200:
            logger.error("Groq API error (HTTP %d): %s", response.status_code, response.text[:200])
            raise GroqProviderError(f"Groq API returned unexpected status code {response.status_code}")

        try:
            return response.json()
        except Exception as json_err:
            logger.error("Groq response could not be parsed as JSON: %s", json_err)
            raise GroqProviderError("Groq API returned invalid JSON") from json_err


class GroqProvider(BaseLLMProvider):
    """
    Groq integration for high-speed cloud LLM inference.
    Primary first-priority provider for the AI Project Intake Pipeline.
    Adheres strictly to the BaseLLMProvider interface contract.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
        client: Optional[GroqClient] = None,
    ):
        self.api_key = (api_key if api_key is not None else settings.GROQ_API_KEY).strip()
        self.model = model or settings.GROQ_MODEL
        self.base_url = (base_url or settings.GROQ_BASE_URL).rstrip("/")
        self.timeout = timeout if timeout is not None else settings.GROQ_TIMEOUT
        self.max_retries = max_retries if max_retries is not None else settings.RETRY_COUNT
        self.client = client or GroqClient(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )

    @property
    def provider_name(self) -> str:
        return "groq"

    def check_health(self) -> bool:
        """
        Check if Groq API is reachable and API key is valid.
        Returns True if models endpoint returns 200 OK, False otherwise.
        """
        if not self.api_key:
            return False
        try:
            url = f"{self.base_url}/models"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            resp = requests.get(url, headers=headers, timeout=5)
            return resp.status_code == 200
        except Exception as e:
            logger.debug("Groq health check failed: %s", e)
            return False

    def generate(
        self,
        prompt: str,
        format: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> str:
        """
        General-purpose prompt completion call using Groq chat completions.
        Returns raw string content from model response.
        """
        messages = [{"role": "user", "content": prompt}]
        response_format = {"type": "json_object"} if format == "json" else None

        data = self.client.chat_completion(
            messages=messages,
            model=self.model,
            temperature=0.2,
            response_format=response_format,
            timeout=timeout or self.timeout,
        )

        choices = data.get("choices")
        if not choices or not isinstance(choices, list) or len(choices) == 0:
            raise GroqProviderError("Groq response contained no completion choices")

        choice = choices[0]
        message = choice.get("message", {})
        content = message.get("content")
        if content is None:
            raise GroqProviderError("Groq response message contained null content")

        return str(content)

    def extract_requirements(
        self,
        brief_text: str,
        retry_count: int = 0,
        last_error: Optional[str] = None,
    ) -> ExtractionResult:
        """
        Extract structured requirements from an unstructured project brief via Groq.

        Handles:
          - Missing/empty brief
          - Missing or invalid GROQ_API_KEY
          - API timeouts, rate limits, connection errors, and 5xx errors
          - Invalid JSON syntax (retries with correction prompt, then fails safely)
          - Schema validation errors (retries with correction prompt, then fails safely)
          - Low confidence / hallucination detection
        """
        # Guard clause: Empty or whitespace brief
        if not brief_text or not brief_text.strip():
            logger.warning("Extraction requested with empty brief text")
            return ExtractionResult(
                valid=False,
                error="Project brief is empty",
                user_message="Please provide a project brief.",
                requires_manual_review=False,
                review_notes="Brief input was empty.",
                retry_count=retry_count,
            )

        # Guard clause: Missing API key
        if not self.api_key:
            logger.error("Groq Step 1: Model Invocation - GROQ_API_KEY is not configured")
            return ExtractionResult(
                valid=False,
                error="Groq API key not configured",
                user_message="AI system is not configured. Please ensure GROQ_API_KEY is set.",
                requires_manual_review=True,
                review_notes="AI system unavailable: Groq API key is not configured.",
                retry_count=retry_count,
            )

        logger.info(
            "Groq Step 1: Model Invocation - Extraction attempt %d of %d (model=%s, length=%d chars)",
            retry_count + 1,
            self.max_retries + 1,
            self.model,
            len(brief_text),
        )

        # 1. Build prompt
        if retry_count == 0 or not last_error:
            prompt = self._get_extraction_prompt(brief_text)
        else:
            prompt = self._get_correction_prompt(brief_text, last_error)

        # 2. Call Groq API
        try:
            response_text = self.generate(
                prompt=prompt,
                format="json",
                timeout=self.timeout,
            )
        except GroqAuthenticationError:
            logger.error("Groq Step 1: Model Invocation - Authentication failed for Groq API")
            return ExtractionResult(
                valid=False,
                error="Groq authentication failed",
                user_message="AI system authentication error. Please check your Groq API credentials.",
                requires_manual_review=True,
                review_notes="Groq authentication failed: invalid or expired API key.",
                retry_count=retry_count,
            )
        except GroqTimeoutError:
            logger.error("Groq Step 1: Model Invocation - Request timed out after %ds", self.timeout)
            return ExtractionResult(
                valid=False,
                error=f"Groq API timeout after {self.timeout} seconds",
                user_message="AI system is slow. Please try again.",
                requires_manual_review=True,
                review_notes=f"Groq request timed out after {self.timeout} seconds.",
                retry_count=retry_count,
            )
        except GroqRateLimitError:
            logger.warning("Groq Step 1: Model Invocation - Rate limit encountered")
            return ExtractionResult(
                valid=False,
                error="Groq rate limit exceeded",
                user_message="AI system is temporarily busy due to rate limits. Please try again in a moment.",
                requires_manual_review=True,
                review_notes="Groq rate limit (HTTP 429) exceeded.",
                retry_count=retry_count,
            )
        except GroqConnectionError:
            logger.error("Groq Step 1: Model Invocation - Connection failed to Groq API")
            return ExtractionResult(
                valid=False,
                error="Groq connection failed",
                user_message="AI system unavailable. Please check your network connection.",
                requires_manual_review=True,
                review_notes="Groq connection failed. Service is unreachable.",
                retry_count=retry_count,
            )
        except Exception as exc:
            logger.error("Groq Step 1: Model Invocation - Request failed: %s", exc)
            return ExtractionResult(
                valid=False,
                error=f"Groq provider error: {str(exc)}",
                user_message="Error communicating with AI service. Please try again later.",
                requires_manual_review=True,
                review_notes=f"Groq provider error: {str(exc)}",
                retry_count=retry_count,
            )

        # 3. Parse JSON from output
        logger.info("Groq Step 2: Response Parsing - Parsing and sanitizing JSON output")
        try:
            extracted_json = clean_and_parse_json(response_text)
        except (json.JSONDecodeError, ValueError) as json_err:
            if retry_count < self.max_retries:
                logger.warning(
                    "Groq Step 2: Response Parsing - Invalid JSON received, retrying (attempt %d of %d): %s",
                    retry_count + 1,
                    self.max_retries,
                    json_err,
                )
                return self.extract_requirements(
                    brief_text=brief_text,
                    retry_count=retry_count + 1,
                    last_error="Invalid JSON syntax. Ensure valid JSON matching the exact schema with all required keys.",
                )
            else:
                logger.error(
                    "Groq Step 2: Response Parsing - Invalid JSON after %d retries: %s",
                    retry_count,
                    json_err,
                )
                return ExtractionResult(
                    valid=False,
                    error=f"LLM returned invalid JSON after retries: {str(json_err)}",
                    user_message=(
                        "We couldn't confidently extract requirements from this brief. \n"
                        "Could you add more details about: Technology preferences, Timeline, Budget"
                    ),
                    requires_manual_review=True,
                    review_notes=(
                        "We couldn't confidently extract requirements from this brief. \n"
                        "Could you add more details about: Technology preferences, Timeline, Budget"
                    ),
                    raw_response=response_text,
                    retry_count=retry_count,
                )

        # 4. Validate with Pydantic
        logger.info("Groq Step 3: Schema Validation - Validating schema with Pydantic")
        try:
            extraction = ProjectExtraction.model_validate(extracted_json)
        except ValidationError as val_err:
            err_details = "; ".join(
                [
                    f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}"
                    for err in val_err.errors()
                ]
            )
            if retry_count < self.max_retries:
                logger.warning(
                    "Groq Step 3: Schema Validation - Pydantic validation failed, retrying (attempt %d of %d): %s",
                    retry_count + 1,
                    self.max_retries,
                    err_details,
                )
                return self.extract_requirements(
                    brief_text=brief_text,
                    retry_count=retry_count + 1,
                    last_error=f"Schema validation failed: {err_details}. All required fields must be present and valid.",
                )
            else:
                logger.error(
                    "Groq Step 3: Schema Validation - Validation failed after %d retries: %s",
                    retry_count,
                    err_details,
                )
                return ExtractionResult(
                    valid=False,
                    error=f"Missing or invalid fields: {err_details}",
                    user_message=(
                        "We couldn't confidently extract requirements from this brief. \n"
                        "Could you add more details about: Technology preferences, Timeline, Budget"
                    ),
                    requires_manual_review=True,
                    review_notes=(
                        "We couldn't confidently extract requirements from this brief. \n"
                        "Could you add more details about: Technology preferences, Timeline, Budget"
                    ),
                    raw_response=response_text,
                    retry_count=retry_count,
                )

        # 5. Hallucination & Confidence Audit
        logger.info("Groq Step 4: Confidence & Hallucination Audit - Assessing confidence threshold and confirmed flags")
        requires_manual_review = False
        review_notes_parts = []
        user_message = None

        if extraction.confidence < settings.CONFIDENCE_THRESHOLD:
            requires_manual_review = True
            review_notes_parts.append(
                f"Confidence score ({extraction.confidence:.2f}) is below threshold ({settings.CONFIDENCE_THRESHOLD:.2f})."
            )
            user_message = "Confidence below threshold. Flagged for human review."
            logger.warning(
                "Groq Step 4: Confidence & Hallucination Audit - Low confidence extraction: %s, confidence=%.2f",
                extraction.project_name,
                extraction.confidence,
            )

        unconfirmed = [
            req.description
            for req in extraction.requirements
            if not req.confirmed
        ]
        if unconfirmed:
            requires_manual_review = True
            unconfirmed_preview = ", ".join(f"'{desc}'" for desc in unconfirmed[:3])
            review_notes_parts.append(
                f"Contains {len(unconfirmed)} inferred requirement(s) requiring human verification: {unconfirmed_preview}."
            )
            if not user_message:
                user_message = "Contains inferred requirements. Flagged for human review."
            logger.info(
                "Extraction contains %d unconfirmed requirements needing human review",
                len(unconfirmed),
            )

        review_notes = " ".join(review_notes_parts) if review_notes_parts else None

        logger.info(
            "Groq requirement extraction completed: %s, confidence=%.2f, requires_review=%s",
            extraction.project_name,
            extraction.confidence,
            requires_manual_review,
        )

        return ExtractionResult(
            valid=True,
            extraction=extraction,
            requires_manual_review=requires_manual_review,
            review_notes=review_notes,
            user_message=user_message,
            raw_response=response_text,
            retry_count=retry_count,
        )

    def _get_extraction_prompt(self, brief_text: str) -> str:
        """
        Load extraction prompt template from app/prompts/extraction.txt or fallback to default.
        """
        prompt_file = _PROJECT_ROOT / "app" / "prompts" / "extraction.txt"
        if prompt_file.exists() and prompt_file.stat().st_size > 0:
            try:
                template = prompt_file.read_text(encoding="utf-8")
                if "{brief_text}" in template:
                    return template.replace("{brief_text}", brief_text)
            except Exception as e:
                logger.warning("Could not read extraction prompt from %s: %s", prompt_file, e)

        return f"""You are an expert technical project analyst.
Analyze the project brief and extract structured requirements.
Return ONLY valid JSON matching this structure:
{{
  "project_name": "string (min 3 chars)",
  "summary": "string (min 20 chars)",
  "requirements": [
    {{"description": "string (min 5 chars)", "priority": "high|medium|low", "confirmed": true}}
  ],
  "missing_information": ["string"],
  "scope_constraints": ["string"],
  "confidence": 0.0 to 1.0
}}

BRIEF:
{brief_text}

JSON OUTPUT:
"""

    def _get_correction_prompt(self, brief_text: str, last_error: str) -> str:
        """
        Build correction prompt informing the LLM of the previous failure.
        """
        return f"""CRITICAL CORRECTION REQUIRED:
Your previous extraction attempt failed with the following error:
{last_error}

Please re-extract requirements from the brief below and correct the error.
Requirements for output:
1. Return ONLY a single, valid JSON object matching the schema.
2. Do NOT wrap output in markdown fences (```json or ```).
3. Do NOT include explanatory or conversational text.
4. Ensure all required fields (project_name, summary, requirements, missing_information, scope_constraints, confidence) are present and conform to types.

Output JSON Schema:
{{
  "project_name": "string (min 3 chars)",
  "summary": "string (min 20 chars)",
  "requirements": [
    {{"description": "string (min 5 chars)", "priority": "high|medium|low", "confirmed": true}}
  ],
  "missing_information": ["string"],
  "scope_constraints": ["string"],
  "confidence": 0.0 to 1.0
}}

PROJECT BRIEF:
{brief_text}

JSON OUTPUT:
"""
