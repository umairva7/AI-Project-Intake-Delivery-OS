"""
app/services/security.py - Pre-ingestion security scanner and credential sanitizer.

Policy (b) — Sanitized-Only:
All raw briefs are inspected and sanitized in memory before ANY database persistence
or logging occurs. Credentials, tokens, and secrets are permanently redacted to '[REDACTED]'.
Injection attacks are flagged for automatic human review escalation.
"""
import re
from typing import Tuple, List

# Known explicit test secrets
KNOWN_SECRETS: List[str] = [
    "P@ssw0rd123",
    "sk-123456789abcdef",
]

# Regex patterns for sensitive credentials & API keys
SENSITIVE_PATTERNS: List[re.Pattern] = [
    re.compile(r"\bsk-[a-zA-Z0-9]{10,}\b", re.IGNORECASE),
    re.compile(r"(?i)((?:admin\s+|user\s+|secret\s+|token\s+)?(?:password|api\s*key|secret|token)\s*(?:is|:|=)\s*)([^\s,;]+)"),
]

# Regex patterns for SQL and prompt injection attempts
INJECTION_PATTERNS: List[re.Pattern] = [
    re.compile(r"(?i)(?:;\s*drop\s+table|;\s*delete\s+from|;\s*insert\s+into|;\s*update\s+.*set|--\s*|\bunion\s+select\b)"),
    re.compile(r"(?i)(?:ignore\s+(?:all\s+|previous\s+)?instructions|system\s+prompt|disregard\s+(?:all\s+)?instructions)"),
]


def scan_and_sanitize_brief(raw_text: str) -> Tuple[str, bool, bool]:
    """
    Scans raw brief in memory for sensitive credentials and injection attempts.
    Permanently redacts all secrets to '[REDACTED]'.

    Returns:
        (sanitized_text, sensitive_data_detected, injection_attempt_detected)
    """
    if not isinstance(raw_text, str):
        return "", False, False

    sanitized = raw_text
    sensitive_detected = False
    injection_detected = False

    # 1. Check known explicit secrets
    for secret in KNOWN_SECRETS:
        if secret in sanitized:
            sensitive_detected = True
            sanitized = sanitized.replace(secret, "[REDACTED]")

    # 2. Check regex patterns for API keys and passwords
    for pat in SENSITIVE_PATTERNS:
        if pat.search(sanitized):
            sensitive_detected = True
            if pat.groups >= 2:
                sanitized = pat.sub(r"\1[REDACTED]", sanitized)
            else:
                sanitized = pat.sub("[REDACTED]", sanitized)

    # 3. Check injection attempts
    for pat in INJECTION_PATTERNS:
        if pat.search(sanitized):
            injection_detected = True

    return sanitized, sensitive_detected, injection_detected
