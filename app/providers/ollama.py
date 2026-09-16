# app/providers/ollama.py
import json
import logging
import re
from pathlib import Path
from typing import Optional, Dict, Any, Union

import requests
from pydantic import ValidationError

from app.config import settings
from app.models import (
    ProjectExtraction,
    Requirement,
    ExtractionResult,
    ErrorResponse,
)

logger = logging.getLogger(__name__)

# Base project directory for loading prompt files
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class OllamaProviderError(Exception):
    """Base exception for Ollama provider errors"""
    pass


class OllamaConnectionError(OllamaProviderError):
    """Raised when unable to connect to Ollama service (offline / connection refused)"""
    pass


class OllamaTimeoutError(OllamaProviderError):
    """Raised when Ollama request times out"""
    pass


def clean_and_parse_json(text: str) -> Dict[str, Any]:
    """
    Attempt to extract and parse JSON from raw LLM output.
    Handles markdown code blocks (```json ... ```), surrounding conversational prose,
    and raw JSON objects.
    """
    if not text or not text.strip():
        raise ValueError("Empty response from LLM")

    cleaned = text.strip()

    # 1. Check for markdown code fences (```json ... ``` or ``` ... ```)
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if fence_match:
        cleaned = fence_match.group(1).strip()
    else:
        # 2. Extract substring between the first '{' and the last '}'
        first_brace = cleaned.find("{")
        last_brace = cleaned.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            cleaned = cleaned[first_brace : last_brace + 1]

    return json.loads(cleaned)


class OllamaProvider:
    """
    Ollama integration for local LLM inference.
    Handles communication with Ollama API, retries, JSON parsing,
    Pydantic schema validation, and failure scenarios.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 30,
        max_retries: Optional[int] = None,
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL
        self.timeout = timeout
        self.max_retries = (
            max_retries if max_retries is not None else settings.RETRY_COUNT
        )

    def check_health(self) -> bool:
        """
        Check if the Ollama service is reachable and responsive.
        Returns True if running, False otherwise.
        """
        try:
            url = f"{self.base_url}/api/tags"
            response = requests.get(url, timeout=3)
            return response.status_code == 200
        except (requests.RequestException, Exception):
            return False

    def generate(
        self,
        prompt: str,
        format: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> str:
        """
        General-purpose call to Ollama /api/generate endpoint.
        Returns the raw response text.
        """
        return self._call_ollama(prompt, timeout=timeout, format=format)

    def extract_requirements(
        self,
        brief_text: str,
        retry_count: int = 0,
        last_error: Optional[str] = None,
    ) -> ExtractionResult:
        """
        Extract structured requirements from an unstructured project brief.

        Handles all 5 failure scenarios from ARCHITECTURE.md:
          - Scenario 1: Invalid JSON (Retries once with correction prompt; flags for manual review if still invalid)
          - Scenario 2: Missing required fields (Pydantic validation catches; retries once, then flags for review)
          - Scenario 3: Hallucinated requirements / Low confidence (Flags for human review if confidence < 0.7 or unconfirmed)
          - Scenario 4: Timeout in 30s (Returns user-friendly slow message + review flag)
          - Scenario 5: Ollama offline / connection refused (Returns user-friendly offline message + review flag)

        Args:
            brief_text: The client's raw project brief text.
            retry_count: Current retry iteration counter.
            last_error: Description of previous failure when retrying.

        Returns:
            ExtractionResult object containing extraction model, status, and review flags.
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

        logger.info(
            "Ollama Step 1: Model Invocation - Extraction attempt %d of %d (length=%d chars)",
            retry_count + 1,
            self.max_retries + 1,
            len(brief_text),
        )

        # 1. Build prompt (initial extraction vs. correction prompt)
        if retry_count == 0 or not last_error:
            prompt = self._get_extraction_prompt(brief_text)
        else:
            prompt = self._get_correction_prompt(brief_text, last_error)

        # 2. Call Ollama API (handles timeouts and connection refused)
        try:
            logger.info("Ollama Step 1: Model Invocation - Dispatching POST request to %s/api/generate", self.base_url)
            response_text = self._call_ollama(
                prompt=prompt,
                timeout=self.timeout,
                format="json",
            )
        except requests.exceptions.Timeout:
            # Scenario 4: Timeout (no response in 30 seconds)
            logger.error(
                "Ollama Step 1: Model Invocation - Ollama timed out after %s seconds on attempt %d",
                self.timeout,
                retry_count + 1,
            )
            return ExtractionResult(
                valid=False,
                error=f"LLM timeout after {self.timeout} seconds",
                user_message="AI system is slow. Please try again.",
                requires_manual_review=True,
                review_notes=f"Ollama request timed out after {self.timeout} seconds.",
                retry_count=retry_count,
            )
        except requests.exceptions.ConnectionError:
            # Scenario 5: Ollama offline (connection refused)
            logger.error(
                "Ollama Step 1: Model Invocation - Ollama connection refused at %s (service offline)",
                self.base_url,
            )
            return ExtractionResult(
                valid=False,
                error="Ollama connection refused",
                user_message="AI system unavailable. Please ensure Ollama is running on http://localhost:11434",
                requires_manual_review=True,
                review_notes="AI system unavailable. Please ensure Ollama is running on http://localhost:11434",
                retry_count=retry_count,
            )
        except requests.exceptions.RequestException as exc:
            logger.error(
                "Ollama Step 1: Model Invocation - HTTP request exception: %s", exc
            )
            return ExtractionResult(
                valid=False,
                error=f"Ollama HTTP error: {str(exc)}",
                user_message="Error communicating with AI service. Please try again later.",
                requires_manual_review=True,
                review_notes=f"HTTP communication error: {str(exc)}",
                retry_count=retry_count,
            )

        # 3. Parse JSON (Scenario 1: Invalid JSON)
        logger.info("Ollama Step 2: Response Parsing - Parsing and sanitizing JSON output")
        try:
            extracted_json = clean_and_parse_json(response_text)
        except (json.JSONDecodeError, ValueError) as json_err:
            if retry_count < self.max_retries:
                logger.warning(
                    "Ollama Step 2: Response Parsing - Invalid JSON received, retrying (attempt %d of %d): %s",
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
                    "Ollama Step 2: Response Parsing - Invalid JSON after %d retries: %s",
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

        # 4. Validate with Pydantic (Scenario 2: Missing required fields)
        logger.info("Ollama Step 3: Schema Validation - Validating schema with Pydantic")
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
                    "Ollama Step 3: Schema Validation - Pydantic validation failed, retrying (attempt %d of %d): %s",
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
                    "Ollama Step 3: Schema Validation - Validation failed after %d retries: %s",
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

        # 5. Hallucination & Low Confidence Detection (Scenario 3)
        logger.info("Ollama Step 4: Confidence & Hallucination Audit - Assessing confidence threshold and confirmed flags")
        requires_manual_review = False
        review_notes_parts = []
        user_message = None

        # Check confidence threshold
        if extraction.confidence < settings.CONFIDENCE_THRESHOLD:
            requires_manual_review = True
            review_notes_parts.append(
                f"Confidence score ({extraction.confidence:.2f}) is below threshold ({settings.CONFIDENCE_THRESHOLD:.2f})."
            )
            user_message = "Confidence below threshold. Flagged for human review."
            logger.warning(
                "Ollama Step 4: Confidence & Hallucination Audit - Low confidence extraction: %s, confidence=%.2f",
                extraction.project_name,
                extraction.confidence,
            )

        # Check for inferred or unconfirmed requirements
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
            "LLM extraction completed: %s, confidence=%.2f, requires_review=%s",
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

    def _call_ollama(
        self,
        prompt: str,
        timeout: Optional[int] = None,
        format: Optional[str] = "json",
    ) -> str:
        """
        Execute an HTTP POST to Ollama's /api/generate endpoint.
        """
        url = f"{self.base_url}/api/generate"
        call_timeout = timeout if timeout is not None else self.timeout

        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,  # Low temp for consistency and determinism
            },
            "temperature": 0.2,
        }

        if format:
            payload["format"] = format

        response = requests.post(url, json=payload, timeout=call_timeout)
        response.raise_for_status()

        result = response.json()
        return result.get("response", "")

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

        # Fallback inline prompt if file is missing or unreadable
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