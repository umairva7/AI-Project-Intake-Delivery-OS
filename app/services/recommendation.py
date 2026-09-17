# app/services/recommendation.py
import logging
import re
from typing import Dict, List, Optional, Set, Tuple, Union

from app.config import settings
from app.models import ProjectExtraction, Requirement, TeamRecommendation

logger = logging.getLogger(__name__)


def _match_signal(signal: str, text: str) -> bool:
    """
    Check if a signal matches within text using word boundaries.
    Ensures 'ai' does not match 'email' or 'chair', and 'react' does not match 'reactionary'.
    """
    pattern = r"\b" + re.escape(signal.lower()) + r"\b"
    return bool(re.search(pattern, text.lower()))


def recommend_team(
    extraction: Union[ProjectExtraction, List[Requirement], str, None],
    team_signals: Optional[Dict[str, Dict[str, int]]] = None,
) -> TeamRecommendation:
    """
    Recommend delivery team(s) using config-driven weighted scoring over extracted requirements.

    Advisory only — recommends teams for human review, does NOT perform automatic assignment.

    Args:
        extraction: Validated ProjectExtraction, list of Requirements, brief text, or None.
        team_signals: Optional dictionary of team definitions and signal weights.
                      Defaults to settings.TEAM_SIGNALS.

    Returns:
        Validated TeamRecommendation model with primary team, supporting teams,
        heuristic confidence (0.0–1.0), transparent reasoning, and review flag.
    """
    signals_config = team_signals or settings.TEAM_SIGNALS

    # 1. Handle empty / None extraction edge case
    if extraction is None:
        logger.warning("Empty or None extraction provided to recommendation service")
        return TeamRecommendation(
            team=None,
            recommended_team=None,
            supporting_teams=[],
            confidence=0.0,
            reasoning=["No extraction or requirements provided; cannot determine team allocation."],
            alternative_team=None,
            requires_human_review=True,
        )

    # 2. Extract requirement descriptions and overall context
    req_descriptions: List[str] = []
    context_chunks: List[str] = []

    if isinstance(extraction, ProjectExtraction):
        context_chunks.append(extraction.project_name)
        context_chunks.append(extraction.summary)
        for req in extraction.requirements:
            req_descriptions.append(req.description)
        for constraint in extraction.scope_constraints:
            context_chunks.append(constraint)
    elif isinstance(extraction, list):
        for item in extraction:
            if isinstance(item, Requirement):
                req_descriptions.append(item.description)
            elif isinstance(item, str):
                req_descriptions.append(item)
    elif isinstance(extraction, str):
        if not extraction.strip():
            logger.warning("Empty text string provided to recommendation service")
            return TeamRecommendation(
                team=None,
                recommended_team=None,
                supporting_teams=[],
                confidence=0.0,
                reasoning=["Empty requirements provided; cannot determine team allocation."],
                alternative_team=None,
                requires_human_review=True,
            )
        context_chunks.append(extraction)

    total_requirements = len(req_descriptions)
    full_corpus = " ".join(context_chunks + req_descriptions)

    # Edge case: No content to evaluate
    if not full_corpus.strip():
        logger.warning("No text content found in extraction requirements")
        return TeamRecommendation(
            team=None,
            recommended_team=None,
            supporting_teams=[],
            confidence=0.0,
            reasoning=["Empty requirements provided; cannot determine team allocation."],
            alternative_team=None,
            requires_human_review=True,
        )

    # 3. Calculate weighted scores and track matched signals per team
    team_scores: Dict[str, int] = {}
    team_matched_signals: Dict[str, Dict[str, int]] = {}
    team_req_matches: Dict[str, Set[int]] = {}

    for team_name, signals in signals_config.items():
        matched: Dict[str, int] = {}
        matched_req_indices: Set[int] = set()

        for signal, weight in signals.items():
            # Check if signal matches anywhere in the corpus
            if _match_signal(signal, full_corpus):
                matched[signal] = weight

                # Track which requirements contained this signal for coverage calculation
                for idx, req_text in enumerate(req_descriptions):
                    if _match_signal(signal, req_text):
                        matched_req_indices.add(idx)

        total_score = sum(matched.values())
        if total_score > 0:
            team_scores[team_name] = total_score
            team_matched_signals[team_name] = matched
            team_req_matches[team_name] = matched_req_indices

    # 4. Handle edge case: No configured team matches
    if not team_scores:
        logger.info("No configured team signals matched project requirements")
        return TeamRecommendation(
            team=None,
            recommended_team=None,
            supporting_teams=[],
            confidence=0.0,
            reasoning=["No configured team signals matched project requirements. Human triage required."],
            alternative_team=None,
            requires_human_review=True,
        )

    # 4b. Precedence & Tie-break: Enterprise Data Engineering vs File/Workflow Automation
    # When enterprise data platform indicators (Snowflake, BigQuery, Databricks, Spark, Kafka, Data Warehouse, Lakehouse)
    # are present alongside file/workflow automation signals, Data Engineering takes precedence as the primary team
    # because enterprise data warehouse schema governance, security, and ingestion pipelines form the
    # foundational architectural dependency. Automation / Data is preserved as a supporting team.
    enterprise_platform_signals = {
        "snowflake",
        "bigquery",
        "databricks",
        "spark",
        "kafka",
        "data warehouse",
        "lakehouse",
        "data lake",
    }
    has_enterprise_platform = any(
        _match_signal(sig, full_corpus) for sig in enterprise_platform_signals
    )
    de_score = team_scores.get("Data Engineering", 0)
    auto_score = team_scores.get("Automation / Data", 0)

    if has_enterprise_platform and de_score >= 3 and auto_score > 0:
        if de_score <= auto_score:
            team_scores["Data Engineering"] = auto_score + 1

    # 5. Rank teams descending by weighted score
    ranked: List[Tuple[str, int]] = sorted(
        team_scores.items(), key=lambda item: item[1], reverse=True
    )
    primary_team, primary_score = ranked[0]
    second_team, second_score = ranked[1] if len(ranked) > 1 else (None, 0)
    score_margin = primary_score - second_score

    # 6. Multi-team identification: materially relevant secondary teams
    supporting_teams: List[str] = []
    if len(ranked) > 1:
        for other_team, other_score in ranked[1:]:
            # Material relevance: score at least 3 points and at least 20% of primary score
            if other_score >= 3 and (other_score / primary_score) >= 0.20:
                supporting_teams.append(other_team)

    # 7. Heuristic Confidence Calculation (0.0 to 1.0)
    # Component A: Winning score strength
    if primary_score >= 12:
        strength_score = 0.85
    elif primary_score >= 8:
        strength_score = 0.75
    elif primary_score >= 5:
        strength_score = 0.65
    elif primary_score >= 3:
        strength_score = 0.50
    else:
        strength_score = 0.35

    # Component B: Score margin / separation from runner-up
    if second_score == 0:
        margin_adj = 0.10  # Clear, undisputed single-team focus
    elif score_margin == 0:
        margin_adj = -0.20  # Ambiguous tie between competing teams
    elif score_margin <= 2 or (primary_score > 0 and (second_score / primary_score) >= 0.70):
        margin_adj = -0.15  # Close competition / strongly contested lead
    elif len(supporting_teams) > 0:
        margin_adj = -0.10  # Cross-functional split across multiple domains
    elif score_margin >= 6:
        margin_adj = 0.05  # Decisive lead
    else:
        margin_adj = 0.00

    # Component C: Requirement coverage
    coverage_adj = 0.00
    if total_requirements > 0:
        covered_count = len(team_req_matches.get(primary_team, set()))
        coverage_ratio = covered_count / total_requirements
        if coverage_ratio >= 0.67:
            coverage_adj = 0.05
        elif coverage_ratio <= 0.33:
            coverage_adj = -0.05

    # Clamp confidence strictly to [0.0, 1.0]
    raw_confidence = strength_score + margin_adj + coverage_adj
    confidence = round(max(0.0, min(1.0, raw_confidence)), 2)

    # 8. Determine Human Review Flag
    # Flag when confidence < threshold, close competing scores, or multi-team cross-functional complexity
    is_close_competition = (second_score >= 3) and (score_margin <= 2)
    is_cross_functional = len(supporting_teams) > 0
    below_threshold = confidence < settings.CONFIDENCE_THRESHOLD

    requires_human_review = bool(
        below_threshold or is_close_competition or is_cross_functional
    )

    # 9. Build Explainable, Human-Readable Reasoning
    reasoning: List[str] = []

    # Sort matched signals by weight descending for display
    primary_signals = sorted(
        team_matched_signals[primary_team].items(),
        key=lambda item: item[1],
        reverse=True,
    )
    signals_summary = ", ".join(f"'{sig}' (+{wt})" for sig, wt in primary_signals[:5])
    reasoning.append(
        f"Primary recommendation: {primary_team} (score: {primary_score}). "
        f"Matched signals: {signals_summary}."
    )

    # Multi-team and supporting team reasoning
    if supporting_teams:
        sup_details = []
        for st in supporting_teams:
            st_signals = sorted(
                team_matched_signals[st].items(),
                key=lambda item: item[1],
                reverse=True,
            )
            st_sig_str = ", ".join(f"'{s}' (+{w})" for s, w in st_signals[:3])
            sup_details.append(f"{st} (score: {team_scores[st]}, matched: {st_sig_str})")
        reasoning.append(
            f"Cross-functional scope detected; supporting teams: {'; '.join(sup_details)}."
        )

    # Ambiguity / close competition reasoning
    if score_margin == 0 and second_team:
        reasoning.append(
            f"Tie score with {second_team} ({primary_score} pts each); human review required to decide lead."
        )
    elif is_close_competition and second_team:
        reasoning.append(
            f"Close margin ({score_margin} pt difference) with {second_team}; manual verification recommended."
        )

    if below_threshold:
        reasoning.append(
            f"Confidence score ({confidence:.2f}) is below threshold ({settings.CONFIDENCE_THRESHOLD:.2f})."
        )

    logger.info(
        "Team recommendation completed: %s (confidence=%.2f, supporting=%s, human_review=%s)",
        primary_team,
        confidence,
        supporting_teams,
        requires_human_review,
    )

    return TeamRecommendation(
        team=primary_team,
        recommended_team=primary_team,
        supporting_teams=supporting_teams,
        confidence=confidence,
        reasoning=reasoning,
        alternative_team=supporting_teams[0] if supporting_teams else None,
        requires_human_review=requires_human_review,
    )
