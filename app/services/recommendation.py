# app/services/recommendation.py
import logging
import re
from typing import List, Optional, Union, Dict

from app.config import settings
from app.models import ProjectExtraction, Requirement, TeamRecommendation

logger = logging.getLogger(__name__)

# Keyword taxonomy for team allocation
TEAM_KEYWORDS: Dict[str, List[str]] = {
    "Web Development": [
        "web", "react", "vue", "angular", "frontend", "backend", "fullstack",
        "django", "fastapi", "flask", "node", "express", "html", "css",
        "javascript", "typescript", "dashboard", "portal", "website", "api", "rest"
    ],
    "Mobile Development": [
        "mobile", "ios", "android", "swift", "kotlin", "flutter",
        "react native", "iphone", "ipad", "app store", "play store"
    ],
    "AI / ML": [
        "ai", "llm", "chatbot", "chat bot", "machine learning", "nlp",
        "deep learning", "computer vision", "model", "rag", "embeddings",
        "vector", "agent", "generative ai", "neural", "ollama", "openai"
    ],
    "Data Engineering": [
        "data pipeline", "etl", "data warehouse", "snowflake", "bigquery",
        "spark", "kafka", "airflow", "dbt", "databricks", "sql", "analytics"
    ],
    "DevOps / Infrastructure": [
        "devops", "infrastructure", "kubernetes", "k8s", "docker", "aws",
        "gcp", "azure", "terraform", "ci/cd", "deployment", "hosting", "cloud"
    ],
}


def recommend_team(
    extraction: Union[ProjectExtraction, List[Requirement], str],
) -> TeamRecommendation:
    """
    Recommend the most appropriate delivery team based on project requirements and tech stack.

    Args:
        extraction: ProjectExtraction instance, list of Requirements, or text string.

    Returns:
        TeamRecommendation instance with team name, confidence, reasoning, and review flags.
    """
    # 1. Aggregate text content to analyze
    text_chunks: List[str] = []

    if isinstance(extraction, ProjectExtraction):
        text_chunks.append(extraction.project_name)
        text_chunks.append(extraction.summary)
        for req in extraction.requirements:
            text_chunks.append(req.description)
        for constraint in extraction.scope_constraints:
            text_chunks.append(constraint)
    elif isinstance(extraction, list):
        for item in extraction:
            if isinstance(item, Requirement):
                text_chunks.append(item.description)
            elif isinstance(item, str):
                text_chunks.append(item)
    elif isinstance(extraction, str):
        text_chunks.append(extraction)

    corpus = " ".join(text_chunks).lower()

    # 2. Score each team against keyword matches
    scores: Dict[str, int] = {}
    match_evidence: Dict[str, List[str]] = {}

    for team, keywords in TEAM_KEYWORDS.items():
        matched = []
        for kw in keywords:
            # Word boundary regex to avoid partial false positives
            pattern = r"\b" + re.escape(kw) + r"\b"
            if re.search(pattern, corpus):
                matched.append(kw)
        if matched:
            scores[team] = len(matched)
            match_evidence[team] = matched

    # 3. Determine best matching team and runner-up
    if not scores:
        # Default fallback when brief is very vague or non-technical
        logger.info("No explicit domain keywords matched; defaulting to Web Development")
        return TeamRecommendation(
            team="Web Development",
            confidence=0.50,
            reasoning=["Default assignment: project brief did not specify distinct technical domain requirements."],
            alternative_team="Mixed / Cross-functional",
            requires_human_review=True,
        )

    # Sort teams by score descending
    sorted_teams = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    best_team, best_score = sorted_teams[0]
    runner_up_team = sorted_teams[1][0] if len(sorted_teams) > 1 else None
    runner_up_score = sorted_teams[1][1] if len(sorted_teams) > 1 else 0

    # 4. Calculate confidence
    # Score of 1 match: 0.70 confidence; 2 matches: 0.85; 3+ matches: 0.92-0.95
    if best_score >= 3:
        raw_confidence = 0.92
    elif best_score == 2:
        raw_confidence = 0.85
    else:
        raw_confidence = 0.70

    # Reduce confidence if runner-up is very close (competing cross-functional scope)
    if runner_up_team and (best_score - runner_up_score) <= 0:
        raw_confidence = max(0.60, raw_confidence - 0.20)
    elif runner_up_team and (best_score - runner_up_score) == 1:
        raw_confidence = max(0.65, raw_confidence - 0.10)

    confidence = round(min(1.0, raw_confidence), 2)
    requires_human_review = confidence < settings.CONFIDENCE_THRESHOLD

    # 5. Build explanatory reasoning
    evidence_str = ", ".join(match_evidence[best_team][:4])
    reasoning = [
        f"Primary deliverable aligns with {best_team} based on detected requirements: {evidence_str}."
    ]
    if runner_up_team and runner_up_score > 0:
        reasoning.append(
            f"Secondary technical domain detected ({runner_up_team}); consider cross-functional support."
        )

    return TeamRecommendation(
        team=best_team,
        confidence=confidence,
        reasoning=reasoning,
        alternative_team=runner_up_team,
        requires_human_review=requires_human_review,
    )
