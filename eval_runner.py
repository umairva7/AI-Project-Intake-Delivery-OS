#!/usr/bin/env python3
"""
eval_runner.py - AI Project Intake Evaluation Runner

Executes the intake pipeline against the golden dataset (20 test cases in evaluation_data.json).
Submits ONLY the 'input' string through the normal entry point (IntakeOrchestrator).
A fresh request is run per case with no caching or shared state.
Captures the intake prediction per case into eval_predictions.json according to the required schema.

SECURITY NOTE:
TC-017 contains sensitive credentials and injection strings.
All secrets and sensitive data are strictly redacted to [REDACTED] in all output payloads.
"""

import sys
import json
import time
import re
import logging
from pathlib import Path
from typing import Dict, Any, List

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.models import RawBrief
from app.orchestrator import IntakeOrchestrator

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger("eval_runner")

# Secret redaction patterns
KNOWN_SECRETS = [
    "P@ssw0rd123",
    "sk-123456789abcdef",
]

SECRET_REGEXES = [
    re.compile(r"sk-[a-zA-Z0-9]{10,}", re.IGNORECASE),
    re.compile(r"(?i)(password\s*(?:is|:|=)\s*)([^\s,;]+)"),
]


def redact_secrets(text: str) -> str:
    """Scrub sensitive credentials from any text field."""
    if not isinstance(text, str):
        return text
    redacted = text
    for secret in KNOWN_SECRETS:
        redacted = redacted.replace(secret, "[REDACTED]")
    for pattern in SECRET_REGEXES:
        if "password" in pattern.pattern:
            redacted = pattern.sub(r"\1[REDACTED]", redacted)
        else:
            redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def sanitize_object(obj: Any) -> Any:
    """Recursively redact secrets across dicts, lists, and strings."""
    if isinstance(obj, str):
        return redact_secrets(obj)
    if isinstance(obj, list):
        return [sanitize_object(item) for item in obj]
    if isinstance(obj, dict):
        return {k: sanitize_object(v) for k, v in obj.items()}
    return obj


def load_dataset(dataset_path: Path) -> List[Dict[str, Any]]:
    """Load test cases from golden evaluation dataset."""
    if not dataset_path.exists():
        # Check fallback in test_cases/
        alt_path = PROJECT_ROOT / "test_cases" / dataset_path.name
        if alt_path.exists():
            dataset_path = alt_path
        else:
            raise FileNotFoundError(f"Golden dataset not found at {dataset_path}")

    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "evaluation_set" in data and "cases" in data["evaluation_set"]:
        return data["evaluation_set"]["cases"]
    elif "cases" in data:
        return data["cases"]
    raise ValueError(f"Invalid dataset format in {dataset_path}")


def run_evaluation(dataset_path: Path, output_path: Path) -> Dict[str, Any]:
    """Run all test cases through the intake pipeline and record predictions."""
    cases = load_dataset(dataset_path)
    total_cases = len(cases)
    print(f"Loaded {total_cases} test cases from {dataset_path}")
    print(f"Executing intake pipeline (live LLM, unmocked, fresh request per case)...")
    print("-" * 75)

    predictions: Dict[str, Any] = {}

    for i, case in enumerate(cases):
        case_id = case["case_id"]
        category = case.get("category", "unknown")
        case_input = case.get("input", "")

        safe_snippet = redact_secrets(case_input.strip()[:40].replace("\n", " "))
        print(f"[{i+1:02d}/{total_cases:02d}] {case_id} ({category}) \"{safe_snippet}...\" -> ", end="", flush=True)

        # Retry loop specifically for transient infrastructure rate limits (HTTP 429)
        max_rate_limit_retries = 3
        for attempt in range(max_rate_limit_retries + 1):
            start_time = time.perf_counter()
            try:
                orchestrator = IntakeOrchestrator()
                raw_brief = RawBrief(brief_text=case_input, source="evaluation")
                result = orchestrator.process_brief(raw_brief)
                latency_ms = int((time.perf_counter() - start_time) * 1000)

                # Check if this execution failed specifically due to Groq rate limit
                review_notes_str = (result.review_notes or "").lower()
                summary_str = (result.extracted.summary if result.extracted else "").lower()
                is_rate_limited = "rate limit" in review_notes_str or "rate limit" in summary_str or "429" in review_notes_str

                if is_rate_limited and attempt < max_rate_limit_retries:
                    wait_sec = 12 * (attempt + 1)
                    print(f"[Rate limit 429, waiting {wait_sec}s to retry]... ", end="", flush=True)
                    time.sleep(wait_sec)
                    continue

                # Map extracted requirements
                extracted_reqs = []
                if result.extracted and result.extracted.requirements:
                    for req in result.extracted.requirements:
                        req_conf = getattr(req, "confidence", None)
                        if req_conf is None:
                            req_conf = result.extracted.confidence
                        extracted_reqs.append({
                            "text": req.description,
                            "confidence": round(float(req_conf), 2),
                            "confirmed": bool(req.confirmed),
                            "source_evidence": req.source_quote or "",
                        })

                # Map team recommendation
                recommended_team = ""
                team_confidence = 0.0
                supporting_teams = []
                team_requires_review = False

                if result.team_recommendation:
                    recommended_team = result.team_recommendation.team or ""
                    team_confidence = round(float(result.team_recommendation.confidence), 2)
                    supporting_teams = list(result.team_recommendation.supporting_teams or [])
                    team_requires_review = bool(result.team_recommendation.requires_human_review)

                flagged = bool(result.requires_manual_review or team_requires_review)

                missing_info = []
                if result.extracted and result.extracted.missing_information:
                    missing_info = list(result.extracted.missing_information)

                sensitive_detected = bool(getattr(result, "sensitive_data_detected", False))
                injection_detected = bool(getattr(result, "injection_attempt_detected", False))

                pred = {
                    "requirements": extracted_reqs,
                    "recommended_team": recommended_team,
                    "team_confidence": team_confidence,
                    "flagged_for_review": flagged,
                    "missing_information": missing_info,
                    "supporting_teams": supporting_teams,
                    "sensitive_data_detected": sensitive_detected,
                    "injection_attempt_detected": injection_detected,
                    "latency_ms": latency_ms,
                    "error": None,
                }

                print(f"OK | team: '{recommended_team}' (conf={team_confidence}) | reqs: {len(extracted_reqs)} | flagged: {flagged} | {latency_ms}ms")
                break

            except Exception as exc:
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                error_str = str(exc)

                if ("429" in error_str.lower() or "rate limit" in error_str.lower()) and attempt < max_rate_limit_retries:
                    wait_sec = 12 * (attempt + 1)
                    print(f"[Rate limit exception, waiting {wait_sec}s to retry]... ", end="", flush=True)
                    time.sleep(wait_sec)
                    continue

                pred = {
                    "requirements": [],
                    "recommended_team": "",
                    "team_confidence": 0.0,
                    "flagged_for_review": True,
                    "missing_information": [],
                    "supporting_teams": [],
                    "sensitive_data_detected": False,
                    "injection_attempt_detected": False,
                    "latency_ms": latency_ms,
                    "error": error_str,
                }

                safe_err = redact_secrets(error_str)[:60].replace("\n", " ")
                print(f"HANDLED ERROR | {safe_err} | flagged: True | {latency_ms}ms")
                break

        # Sanitize any secrets from predictions
        predictions[case_id] = sanitize_object(pred)

        # Pause between cases to respect token rate replenishment
        time.sleep(5.0)

    print("-" * 75)
    print(f"Saving predictions to {output_path}...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(predictions, f, indent=2)

    print(f"Saved {len(predictions)} case predictions successfully.")
    return predictions


def main():
    dataset_file = Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT_ROOT / "evaluation_data.json"
    output_file = Path(sys.argv[2]) if len(sys.argv) > 2 else PROJECT_ROOT / "eval_predictions.json"
    run_evaluation(dataset_file, output_file)


if __name__ == "__main__":
    main()
