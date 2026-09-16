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
    extraction_is_usable,
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


DEFAULT_CLARIFICATION_CHECKLIST: List[str] = [
    "Clarify the specific operational problem to be solved",
    "Identify the available data and its format",
    "Define the expected AI capability or use case",
    "Define success metrics and expected cost/time savings",
    "Identify required integrations and deployment environment",
]

# Terms that indicate provider errors or technical failures and must NEVER contaminate checklists
ERROR_CONTAMINATION_TERMS: Set[str] = {
    "connection refused", "offline", "http", "traceback", "exception",
    "timed out", "timeout", "error", "failed", "couldn't extract", "ollama",
    "groq", "status code", "internal server error", "stack trace", "errno",
    "500", "404", "400", "pydantic", "validation failed", "bad gateway",
}


def generate_clarification_checklist(
    brief_text: Optional[str] = None,
    missing_information: Optional[List[str]] = None,
) -> Checklist:
    """
    Generate a safe, non-invented clarification checklist when requirement extraction fails or is unusable.
    Strictly avoids any implementation, technical, architecture, framework, model, or database assumptions.
    Derives clarification questions strictly from original brief and known missing information.
    """
    items: List[ChecklistItem] = []
    seen_tasks: List[str] = []
    task_id = 1

    # 1. Add clarification tasks from known missing information (filtered of error contamination)
    if missing_information:
        for missing in missing_information:
            clean = missing.strip().rstrip(".")
            clean_lower = clean.lower()
            # Strict error contamination barrier: skip any item mentioning provider errors
            if any(term in clean_lower for term in ERROR_CONTAMINATION_TERMS):
                continue
            # Skip internal fallback phrases
            if any(phrase in clean_lower for phrase in ["automated extraction", "manual triage", "manual verification", "extraction failure"]):
                continue

            if clean_lower.startswith("clarify "):
                task_text = clean
            elif clean_lower.startswith("confirm "):
                task_text = f"Clarify with client: {clean[8:]}"
            else:
                task_text = f"Clarify with client: {clean}"

            if not _is_duplicate_task(task_text, seen_tasks):
                items.append(
                    ChecklistItem(
                        id=task_id,
                        task=task_text,
                        title=task_text,
                        priority="high",
                        estimated_effort="1-2 hours",
                        depends_on=None,
                    )
                )
                seen_tasks.append(task_text)
                task_id += 1

    # 2. Add standard clarification tasks based on original user brief
    brief_lower = (brief_text or "").lower()
    for default_task in DEFAULT_CLARIFICATION_CHECKLIST:
        task_text = default_task
        # If the brief has zero AI/ML/data keywords and is clearly a standard non-AI app, adapt item 3 gracefully
        if "ai capability" in default_task.lower() and not any(k in brief_lower for k in ["ai", "ml", "model", "algorithm", "intelligence", "operations", "data"]):
            task_text = "Define the expected system capability or core use cases"

        if not _is_duplicate_task(task_text, seen_tasks):
            items.append(
                ChecklistItem(
                    id=task_id,
                    task=task_text,
                    title=task_text,
                    priority="high" if task_id <= 2 else "medium",
                    estimated_effort="2-4 hours",
                    depends_on=None,
                )
            )
            seen_tasks.append(task_text)
            task_id += 1

    logger.info(
        "Clarification checklist generated: %d tasks (checklist_type=clarification)",
        len(items),
    )

    return Checklist(
        checklist_type="clarification",
        type="clarification",
        items=items,
        total_tasks=len(items),
        generated_at=datetime.now(timezone.utc),
    )


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
    - Extraction gating: unusable or failed extractions are strictly routed to clarification checklist
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
    # 0. Authoritative Extraction Gate check: block implementation checklist if extraction failed or confidence 0
    if isinstance(requirements, ProjectExtraction):
        if not extraction_is_usable(requirements):
            logger.warning(
                "generate_checklist: Unusable extraction passed (status=%s, confidence=%.2f); "
                "blocking implementation checklist and generating clarification checklist",
                getattr(requirements, "extraction_status", "failed"),
                getattr(requirements, "confidence", 0.0),
            )
            return generate_clarification_checklist(
                brief_text=requirements.project_name if not requirements.project_name.startswith("Brief:") else None,
                missing_information=requirements.missing_information,
            )

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

    # Safe validation check: empty requirements
    if not req_list:
        logger.warning("generate_checklist called with empty requirements")
        raise ValueError("Cannot generate delivery checklist without project requirements")

    # Gate check: if requirements are purely fallback triage items, block implementation checklist
    if all(
        "review and manually extract requirements" in req.description.lower()
        or "manual triage" in req.description.lower()
        for req in req_list
    ):
        logger.warning(
            "generate_checklist: Fallback triage requirements detected; "
            "blocking implementation checklist and generating clarification checklist"
        )
        return generate_clarification_checklist(
            missing_information=missing_info_list,
        )

    # Unpack team name and supporting teams
    if isinstance(team, TeamRecommendation):
        primary_team = team.team or "Web Development"
        secondary_teams = supporting_teams if supporting_teams is not None else team.supporting_teams
    else:
        primary_team = team or "Web Development"
        secondary_teams = supporting_teams or []

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
        checklist_type="implementation",
        type="implementation",
        items=items,
        total_tasks=len(items),
        generated_at=datetime.now(timezone.utc),
    )
