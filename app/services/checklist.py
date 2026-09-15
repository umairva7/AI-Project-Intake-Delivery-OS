# app/services/checklist.py
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Union

from app.config import settings
from app.models import (
    Checklist,
    ChecklistItem,
    ProjectExtraction,
    Requirement,
    TeamRecommendation,
)

logger = logging.getLogger(__name__)

# Keywords identifying missing details that materially affect architecture, scope, or delivery
CRITICAL_MISSING_KEYWORDS: Set[str] = {
    "user", "volume", "scale", "traffic", "load", "concurrent", "capacity",
    "database", "db", "storage", "data source", "schema",
    "hosting", "deployment", "cloud", "aws", "gcp", "azure", "environment",
    "hardware", "device", "platform", "target", "infrastructure",
    "auth", "authentication", "authorization", "security", "permission", "compliance",
    "timeline", "deadline", "budget", "cost", "mvp", "schedule", "milestone",
    "api", "integration", "third-party", "external",
    "sla", "latency", "performance", "acceptance criteria",
}

# Non-blocking / minor details that should not create formal clarification tasks
MINOR_DETAIL_KEYWORDS: Set[str] = {
    "color", "font", "logo", "icon", "dark mode", "button copy", "favicon", "styling", "theme",
}


def is_critical_missing_info(info: str) -> bool:
    """
    Determine if a missing information item is critical to architecture, scope, cost,
    or delivery timeline rather than a minor cosmetic detail.
    """
    text_lower = info.lower().strip()
    # Check if explicitly minor
    if any(mk in text_lower for mk in MINOR_DETAIL_KEYWORDS):
        return False
    # Check if matches critical architectural or delivery scope keywords
    return any(re.search(r"\b" + re.escape(ck) + r"\b", text_lower) for ck in CRITICAL_MISSING_KEYWORDS)


GENERIC_PREFIX_VERBS: Set[str] = {
    "conduct", "perform", "execute", "carry out", "do", "complete", "run",
    "implement", "build", "create", "develop",
}


def _normalize_task_text(text: str) -> str:
    """Strip punctuation, stop words, and generic action verbs for semantic deduplication."""
    cleaned = re.sub(r"[^\w\s]", "", text.lower()).strip()
    words = [
        w for w in cleaned.split()
        if w not in {"the", "a", "an", "and", "or", "for", "with", "to", "in", "of", "on"}
        and w not in GENERIC_PREFIX_VERBS
    ]
    return " ".join(words)


def _is_duplicate_task(task: str, existing_tasks: List[str]) -> bool:
    """Check if task is identical or semantically duplicate (>80% word overlap) of an existing task."""
    norm_new = _normalize_task_text(task)
    words_new = set(norm_new.split())
    if not words_new:
        return False

    for existing in existing_tasks:
        norm_exist = _normalize_task_text(existing)
        if norm_new == norm_exist:
            return True
        words_exist = set(norm_exist.split())
        if words_exist:
            jaccard = len(words_new & words_exist) / len(words_new | words_exist)
            if jaccard >= 0.75:
                return True
    return False


def _format_requirement_task(desc: str) -> str:
    """Format raw requirement description into an actionable, specific task."""
    clean = desc.strip().rstrip(".")
    clean_lower = clean.lower()

    if clean_lower.startswith("we need "):
        clean = clean[8:]
    elif clean_lower.startswith("need "):
        clean = clean[5:]

    # Prefix with action verb if not already starting with one
    action_verbs = (
        "implement", "build", "create", "develop", "configure", "integrate",
        "design", "deploy", "setup", "set up", "establish", "verify", "validate"
    )
    if not any(clean.lower().startswith(v) for v in action_verbs):
        clean = f"Implement {clean}"

    return clean[0].upper() + clean[1:]


def generate_checklist(
    requirements: Union[List[Requirement], ProjectExtraction, None],
    team: Union[str, TeamRecommendation, None] = "Web Development",
    missing_information: Optional[List[str]] = None,
    supporting_teams: Optional[List[str]] = None,
    team_templates: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Checklist:
    """
    Generate an ordered, team-specific delivery checklist for planning and human review.

    Advisory planning tool — does NOT execute work or automatically assign ownership.

    Enforces:
    - Team-specific delivery lifecycle (Clarification -> Architecture -> Setup -> Implementation -> Integration -> QA -> Deployment)
    - Controlled task count: minimum 5, maximum 12 tasks
    - Selective clarification for critical missing info only
    - Multi-team cross-functional integration tasks
    - Deduplication of redundant tasks
    - Sequential dependency tracking (depends_on)

    Args:
        requirements: Extracted requirements list or ProjectExtraction model.
        team: Recommended team name or TeamRecommendation model.
        missing_information: List of missing requirements to evaluate for clarification.
        supporting_teams: Optional list of secondary teams for multi-team projects.
        team_templates: Optional config dictionary of team checklist templates.

    Returns:
        Validated Checklist Pydantic model.
    """
    templates = team_templates or settings.TEAM_CHECKLIST_TEMPLATES

    # 1. Unpack input arguments
    req_list: List[Requirement] = []
    missing_info_list: List[str] = []

    if isinstance(requirements, ProjectExtraction):
        req_list = requirements.requirements or []
        missing_info_list = missing_information if missing_information is not None else (requirements.missing_information or [])
    elif isinstance(requirements, list):
        req_list = requirements
        missing_info_list = missing_information or []
    elif requirements is None:
        req_list = []
        missing_info_list = missing_information or []

    # Unpack team name and supporting teams
    if isinstance(team, TeamRecommendation):
        primary_team = team.team or "Web Development"
        secondary_teams = supporting_teams if supporting_teams is not None else team.supporting_teams
    else:
        primary_team = team or "Web Development"
        secondary_teams = supporting_teams or []

    # Safe validation check: empty requirements
    if not req_list:
        logger.warning("generate_checklist called with empty requirements")
        raise ValueError("Cannot generate delivery checklist without project requirements")

    # Retrieve team template (or fallback to Web Development defaults)
    team_tpl = templates.get(primary_team, templates.get("Web Development", {}))

    items: List[ChecklistItem] = []
    seen_tasks: List[str] = []
    task_id = 1

    # ========================================================================
    # Phase 1: Clarification of Critical Missing Information
    # ========================================================================
    clarification_task_ids: List[int] = []
    critical_missing = [item for item in missing_info_list if is_critical_missing_info(item)]

    # Cap clarification tasks to top 2 critical items to avoid overwhelming checklist
    for missing_item in critical_missing[:2]:
        clean_item = missing_item.strip().rstrip(".")
        if clean_item.lower().startswith("confirm "):
            clean_item = clean_item[8:]
        elif clean_item.lower().startswith("clarify "):
            clean_item = clean_item[8:]
        task_text = f"Clarify with client: {clean_item}"
        if not _is_duplicate_task(task_text, seen_tasks):
            items.append(
                ChecklistItem(
                    id=task_id,
                    task=task_text,
                    priority="high",
                    estimated_effort="2-4 hours",
                    depends_on=None,
                )
            )
            seen_tasks.append(task_text)
            clarification_task_ids.append(task_id)
            task_id += 1

    # ========================================================================
    # Phase 2: Architecture & Technical Planning (Team-Specific)
    # ========================================================================
    arch_task_id = task_id
    planning_text = team_tpl.get(
        "planning", f"Define technical architecture and design specifications for {primary_team}"
    )
    if not _is_duplicate_task(planning_text, seen_tasks):
        items.append(
            ChecklistItem(
                id=arch_task_id,
                task=planning_text,
                priority="high",
                estimated_effort="1-2 days",
                depends_on=clarification_task_ids if clarification_task_ids else None,
            )
        )
        seen_tasks.append(planning_text)
        task_id += 1

    # ========================================================================
    # Phase 3: Setup & Workspace Environment (Team-Specific)
    # ========================================================================
    setup_task_id = task_id
    setup_text = team_tpl.get(
        "setup", f"Set up development workspace, repository, and dependencies for {primary_team}"
    )
    if not _is_duplicate_task(setup_text, seen_tasks):
        items.append(
            ChecklistItem(
                id=setup_task_id,
                task=setup_text,
                priority="high",
                estimated_effort="4-8 hours",
                depends_on=[arch_task_id],
            )
        )
        seen_tasks.append(setup_text)
        task_id += 1

    # ========================================================================
    # Phase 4: Core Feature Implementation Tasks (Derived from Requirements)
    # ========================================================================
    impl_task_ids: List[int] = []
    prev_id = setup_task_id

    # Filter out duplicates and limit implementation tasks so total tasks stay within max 12
    # Reserve space for: supporting team tasks (up to 2) + testing (1) + deployment (1)
    max_impl_tasks = max(1, 12 - len(items) - (len(secondary_teams[:2])) - 2)

    for req in req_list[:max_impl_tasks]:
        task_text = _format_requirement_task(req.description)
        if not _is_duplicate_task(task_text, seen_tasks):
            items.append(
                ChecklistItem(
                    id=task_id,
                    task=task_text,
                    priority=req.priority,
                    estimated_effort="2-3 days",
                    depends_on=[prev_id],
                )
            )
            seen_tasks.append(task_text)
            impl_task_ids.append(task_id)
            prev_id = task_id
            task_id += 1

    # If requirements exceeded max_impl_tasks, combine remaining into cohesive batch task
    remaining_reqs = req_list[max_impl_tasks:]
    if remaining_reqs and len(items) < 10:
        combined_text = f"Implement remaining features: {', '.join(r.description[:30] for r in remaining_reqs[:3])}"
        if not _is_duplicate_task(combined_text, seen_tasks):
            items.append(
                ChecklistItem(
                    id=task_id,
                    task=combined_text,
                    priority="medium",
                    estimated_effort="3-4 days",
                    depends_on=[prev_id],
                )
            )
            seen_tasks.append(combined_text)
            impl_task_ids.append(task_id)
            prev_id = task_id
            task_id += 1

    # ========================================================================
    # Phase 5: Multi-Team / Supporting Team Integration Tasks
    # ========================================================================
    integration_task_ids: List[int] = []
    if secondary_teams:
        for st in secondary_teams[:2]:  # Support up to 2 secondary teams
            st_tpl = templates.get(st, {})
            st_task_text = st_tpl.get("supporting", f"Integrate cross-functional components with {st}")
            if not _is_duplicate_task(st_task_text, seen_tasks) and len(items) < 10:
                items.append(
                    ChecklistItem(
                        id=task_id,
                        task=st_task_text,
                        priority="high",
                        estimated_effort="1-2 days",
                        depends_on=[prev_id],
                    )
                )
                seen_tasks.append(st_task_text)
                integration_task_ids.append(task_id)
                prev_id = task_id
                task_id += 1

    # ========================================================================
    # Phase 6: Testing & Quality Assurance (Team-Specific)
    # ========================================================================
    qa_task_id = task_id
    testing_text = team_tpl.get(
        "testing", f"Conduct quality assurance and integration testing for {primary_team}"
    )
    if not _is_duplicate_task(testing_text, seen_tasks):
        items.append(
            ChecklistItem(
                id=qa_task_id,
                task=testing_text,
                priority="high",
                estimated_effort="1-2 days",
                depends_on=[prev_id],
            )
        )
        seen_tasks.append(testing_text)
        prev_id = qa_task_id
        task_id += 1

    # ========================================================================
    # Phase 7: Deployment & Operational Handoff (Team-Specific)
    # ========================================================================
    deployment_text = team_tpl.get(
        "deployment", f"Prepare release build and configure deployment for {primary_team}"
    )
    if not _is_duplicate_task(deployment_text, seen_tasks):
        items.append(
            ChecklistItem(
                id=task_id,
                task=deployment_text,
                priority="medium",
                estimated_effort="4-8 hours",
                depends_on=[prev_id],
            )
        )
        seen_tasks.append(deployment_text)
        task_id += 1

    # ========================================================================
    # Enforcement: Minimum 5 Tasks Constraint
    # ========================================================================
    # For very simple projects, expand delivery stages to guarantee at least 5 meaningful tasks
    if len(items) < 5:
        logger.info("Checklist has %d tasks; expanding delivery stages to meet 5-task minimum", len(items))
        expansion_candidates = [
            ("Confirm detailed user stories and acceptance criteria with client", "high", "2 hours", None),
            ("Configure CI build checks, unit tests, and code coverage thresholds", "medium", "4 hours", [arch_task_id]),
            ("Perform user acceptance walkthrough and handoff documentation", "medium", "4 hours", [items[-1].id]),
        ]
        for exp_task, exp_pri, exp_effort, exp_deps in expansion_candidates:
            if len(items) >= 5:
                break
            if not _is_duplicate_task(exp_task, seen_tasks):
                items.append(
                    ChecklistItem(
                        id=task_id,
                        task=exp_task,
                        priority=exp_pri,
                        estimated_effort=exp_effort,
                        depends_on=exp_deps,
                    )
                )
                seen_tasks.append(exp_task)
                task_id += 1

    # ========================================================================
    # Enforcement: Maximum 12 Tasks Constraint
    # ========================================================================
    if len(items) > 12:
        logger.info("Checklist has %d tasks; capping to 12 maximum tasks", len(items))
        items = items[:12]

    # Renumber IDs sequentially (1..N) and re-link dependencies to guarantee schema integrity
    id_mapping: Dict[int, int] = {}
    for new_idx, item in enumerate(items, start=1):
        id_mapping[item.id] = new_idx
        item.id = new_idx

    for item in items:
        if item.depends_on:
            remapped = [id_mapping[d] for d in item.depends_on if d in id_mapping and id_mapping[d] < item.id]
            item.depends_on = remapped if remapped else None

    logger.info(
        "Checklist generated: %d tasks for team '%s' (supporting=%s)",
        len(items),
        primary_team,
        secondary_teams,
    )

    return Checklist(
        items=items,
        total_tasks=len(items),
        generated_at=datetime.now(timezone.utc),
    )
