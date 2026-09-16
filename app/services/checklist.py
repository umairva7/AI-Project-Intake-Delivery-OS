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
    TaskEvidence,
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
    "threshold", "thresholds", "metric", "metrics", "rule", "rules", "parameter", "parameters", "criteria", "anomaly",
}

# Non-blocking / minor details that should not create formal clarification tasks
MINOR_DETAIL_KEYWORDS: Set[str] = {
    "color", "font", "logo", "icon", "dark mode", "button copy", "favicon", "styling", "theme",
}

# Unsupported technology assumptions that must NEVER be inferred without explicit evidence
UNSUPPORTED_TECH_TERMS: Set[str] = {
    "vector database", "vector store", "chroma", "pinecone", "qdrant", "weaviate",
    "rag", "retrieval augmented", "retrieval strategy",
    "redis", "celery", "rabbitmq", "kafka",
    "docker", "containerize", "container runtime",
    "kubernetes", "k8s",
    "cross-browser", "cross browser",
    "ci/cd", "github actions", "jenkins",
    "aws", "gcp", "azure", "vercel", "heroku", "netlify",
    "cloud platform", "cloud infrastructure", "cloud deployment",
    "z-score", "isolation forest",
}

# Framework and architecture assumptions that cannot be inferred without evidence
FRAMEWORK_ASSUMPTION_TERMS: Set[str] = {
    "react", "vue", "angular", "fastapi", "flask", "django", "express",
    "rest api", "graphql", "postgresql", "mysql", "mongodb",
}


def is_critical_missing_info(info: str) -> bool:
    """
    Determine if a missing information item is critical to architecture, scope, cost,
    or delivery timeline rather than a minor cosmetic detail.
    """
    text_lower = info.lower().strip()
    if any(mk in text_lower for mk in MINOR_DETAIL_KEYWORDS):
        return False
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

    action_verbs = (
        "implement", "build", "create", "develop", "configure", "integrate",
        "design", "deploy", "setup", "set up", "establish", "verify", "validate",
        "connect", "display", "collect", "clean", "flag", "train"
    )
    if not any(clean.lower().startswith(v) for v in action_verbs):
        clean = f"Implement {clean}"

    return clean[0].upper() + clean[1:]


def is_technology_supported_by_evidence(
    task_text: str,
    brief_text: Optional[str],
    requirements: List[Requirement],
) -> bool:
    """
    Verify whether any specific technology, framework, architecture, or algorithm
    mentioned in task_text is explicitly supported by the client's brief or confirmed requirements.

    Returns:
        True if all technical terms in task_text have evidence in brief or requirements.
        False if the task introduces an unsupported assumption.
    """
    task_lower = task_text.lower()

    # Build client evidence text corpus from brief and requirements
    evidence_corpus = (brief_text or "").lower()
    for req in requirements:
        evidence_corpus += " " + (req.description or "").lower()
        if req.source_quote:
            evidence_corpus += " " + req.source_quote.lower()

    def _contains(haystack: str, needle: str) -> bool:
        if not needle:
            return False
        return bool(re.search(r"\b" + re.escape(needle) + r"\b", haystack))

    # 1. Check prohibited unsupported technical assumptions
    for term in UNSUPPORTED_TECH_TERMS:
        if _contains(task_lower, term) and not _contains(evidence_corpus, term):
            return False

    # 2. Check framework and architecture assumptions
    for fw in FRAMEWORK_ASSUMPTION_TERMS:
        if _contains(task_lower, fw) and not _contains(evidence_corpus, fw):
            return False

    return True


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
    "api key", "unauthorized", "rate limit", "bearer",
}


def generate_clarification_checklist(
    brief_text: Optional[str] = None,
    missing_information: Optional[List[str]] = None,
) -> Checklist:
    """
    Generate a safe, non-invented clarification checklist when requirement extraction fails or is unusable.
    Strictly avoids any implementation, technical, architecture, framework, model, or database assumptions.
    Derives clarification questions strictly from original brief and known missing information.
    Attaches TaskEvidence to every item.
    """
    items: List[ChecklistItem] = []
    seen_tasks: List[str] = []
    task_id = 1

    # 1. Add clarification tasks from known missing information (filtered of error contamination)
    if missing_information:
        for missing in missing_information:
            clean = missing.strip().rstrip(".")
            clean_lower = clean.lower()
            if any(term in clean_lower for term in ERROR_CONTAMINATION_TERMS):
                continue
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
                        task_type="clarification",
                        evidence=TaskEvidence(
                            type="missing_information",
                            source_quote=clean,
                            requirement_description=task_text,
                            confirmed=False,
                        ),
                    )
                )
                seen_tasks.append(task_text)
                task_id += 1

    # 2. Add standard clarification tasks based on original user brief
    brief_lower = (brief_text or "").lower()
    for default_task in DEFAULT_CLARIFICATION_CHECKLIST:
        task_text = default_task
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
                    task_type="clarification",
                    evidence=TaskEvidence(
                        type="missing_information",
                        source_quote=task_text,
                        requirement_description=task_text,
                        confirmed=False,
                    ),
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


def validate_checklist_evidence(
    items: List[ChecklistItem],
    brief_text: Optional[str] = None,
    requirements: Optional[List[Requirement]] = None,
) -> List[ChecklistItem]:
    """
    Application-level validation layer enforcing evidence-boundedness.
    Rejects tasks that lack evidence or introduce unsupported technical assumptions.
    """
    validated: List[ChecklistItem] = []
    reqs = requirements or []

    for item in items:
        if item.task_type == "implementation":
            # Invariant 1: Every implementation task must have evidence
            if not item.has_evidence:
                logger.warning("Application Validation: Rejecting task without evidence: '%s'", item.task)
                continue

            # Invariant 2: Cannot introduce unsupported technical assumptions
            if not is_technology_supported_by_evidence(item.task, brief_text, reqs):
                logger.warning(
                    "Application Validation: Rejecting task with unsupported assumptions: '%s'",
                    item.task,
                )
                continue

        validated.append(item)

    return validated


def generate_checklist(
    requirements: Union[List[Requirement], ProjectExtraction, None],
    team: Union[str, TeamRecommendation, None] = "Web Development",
    missing_information: Optional[List[str]] = None,
    supporting_teams: Optional[List[str]] = None,
    team_templates: Optional[Dict[str, Dict[str, Any]]] = None,
    brief_text: Optional[str] = None,
    extraction: Optional[ProjectExtraction] = None,
    delivery_policy: Optional[str] = None,
    evidence_bound: Optional[bool] = None,
) -> Checklist:
    """
    Generate an evidence-bound delivery checklist for planning and human review.

    Every implementation task must be justified by:
      1. An explicit statement from the client brief, or
      2. A confirmed requirement from extraction.

    Enforces:
    - Extraction gating: failed or unusable extractions produce clarification checklists
    - Evidence traceability: every task has a TaskEvidence record
    - Hallucination prevention: rejects ungrounded architecture, frameworks, and tools
    - Controlled task count: minimum 5, maximum 12 tasks
    - Sequential dependency tracking (depends_on)
    """
    # 0. Authoritative Extraction Gate check
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
        if brief_text is None and requirements.summary:
            brief_text = requirements.summary
        extraction = requirements
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
            brief_text=brief_text,
            missing_information=missing_info_list,
        )

    # Unpack team name and supporting teams
    if isinstance(team, TeamRecommendation):
        primary_team = team.team or "Web Development"
        secondary_teams = supporting_teams if supporting_teams is not None else team.supporting_teams
    else:
        primary_team = team or "Web Development"
        secondary_teams = supporting_teams or []

    # Determine execution mode:
    # When brief_text is passed OR evidence_bound=True, enforce evidence-bounded generation.
    # When brief_text is None and evidence_bound is not explicitly True, maintain legacy template mode.
    is_evidence_bound = (
        evidence_bound is True
        or (evidence_bound is None and (brief_text is not None or isinstance(requirements, ProjectExtraction)))
    )

    items: List[ChecklistItem] = []
    seen_tasks: List[str] = []
    task_id = 1

    # ========================================================================
    # Category B: Clarification of Critical Missing Information
    # ========================================================================
    clarification_task_ids: List[int] = []
    critical_missing = [
        item for item in missing_info_list
        if is_critical_missing_info(item)
        or (is_evidence_bound and not any(mk in item.lower() for mk in MINOR_DETAIL_KEYWORDS))
    ]

    for missing_item in critical_missing[:3]:
        clean_item = missing_item.strip().rstrip(".")
        if clean_item.lower().startswith("confirm "):
            clean_item = clean_item[8:]
        elif clean_item.lower().startswith("clarify "):
            clean_item = clean_item[8:]
        task_text = f"Clarify with client: {clean_item}"
        if not _is_duplicate_task(task_text, seen_tasks):
            evidence = TaskEvidence(
                type="missing_information",
                source_quote=clean_item,
                requirement_description=clean_item,
                confirmed=False,
            )
            items.append(
                ChecklistItem(
                    id=task_id,
                    task=task_text,
                    priority="high",
                    estimated_effort="2-4 hours",
                    depends_on=None,
                    task_type="clarification",
                    evidence=evidence,
                )
            )
            seen_tasks.append(task_text)
            clarification_task_ids.append(task_id)
            task_id += 1

    if is_evidence_bound:
        # ====================================================================
        # EVIDENCE-BOUND MODE: Evidence-bound generation strictly derived from requirements
        # ====================================================================
        prev_id = clarification_task_ids[-1] if clarification_task_ids else None

        # 1. Necessary Engineering Lifecycle: Architecture for confirmed requirements
        arch_task_id = task_id
        arch_text = "Define technical architecture for confirmed requirements"
        evidence_arch = TaskEvidence(
            type="implied",
            source_quote="Architecture design for confirmed scope",
            requirement_description="Confirmed project requirements",
            confirmed=True,
        )
        items.append(
            ChecklistItem(
                id=arch_task_id,
                task=arch_text,
                priority="high",
                estimated_effort="1-2 days",
                depends_on=[prev_id] if prev_id else None,
                task_type="implementation",
                evidence=evidence_arch,
            )
        )
        seen_tasks.append(arch_text)
        prev_id = arch_task_id
        task_id += 1

        # 2. Necessary Engineering Lifecycle: Workspace setup for confirmed requirements
        setup_task_id = task_id
        setup_text = "Set up development workspace and repository for confirmed requirements"
        evidence_setup = TaskEvidence(
            type="implied",
            source_quote="Workspace and repository initialization",
            requirement_description="Confirmed project requirements",
            confirmed=True,
        )
        items.append(
            ChecklistItem(
                id=setup_task_id,
                task=setup_text,
                priority="high",
                estimated_effort="4-8 hours",
                depends_on=[prev_id] if prev_id else None,
                task_type="implementation",
                evidence=evidence_setup,
            )
        )
        seen_tasks.append(setup_text)
        prev_id = setup_task_id
        task_id += 1

        # 3. Core Feature Implementation Tasks (Derived directly from confirmed requirements)
        max_impl_tasks = max(1, 10 - len(items))
        for req in req_list[:max_impl_tasks]:
            task_text = _format_requirement_task(req.description)
            if not _is_duplicate_task(task_text, seen_tasks):
                evidence_req = TaskEvidence(
                    type="requirement",
                    source_quote=req.source_quote or req.description,
                    requirement_description=req.description,
                    confirmed=req.confirmed,
                )
                items.append(
                    ChecklistItem(
                        id=task_id,
                        task=task_text,
                        priority=req.priority,
                        estimated_effort="2-3 days",
                        depends_on=[prev_id] if prev_id else None,
                        task_type="implementation",
                        evidence=evidence_req,
                    )
                )
                seen_tasks.append(task_text)
                prev_id = task_id
                task_id += 1

        # 4. Multi-team supporting integration tasks (if secondary teams exist)
        if secondary_teams:
            for st in secondary_teams[:2]:
                st_task_text = f"Integrate cross-functional components with {st}"
                if not _is_duplicate_task(st_task_text, seen_tasks) and len(items) < 11:
                    evidence_st = TaskEvidence(
                        type="implied",
                        source_quote=f"Cross-functional coordination with {st}",
                        requirement_description=f"Supporting team: {st}",
                        confirmed=True,
                    )
                    items.append(
                        ChecklistItem(
                            id=task_id,
                            task=st_task_text,
                            priority="high",
                            estimated_effort="1-2 days",
                            depends_on=[prev_id] if prev_id else None,
                            task_type="implementation",
                            evidence=evidence_st,
                        )
                    )
                    seen_tasks.append(st_task_text)
                    prev_id = task_id
                    task_id += 1

        # 5. Necessary Engineering Lifecycle: QA and Testing against confirmed requirements
        qa_task_id = task_id
        qa_text = "Conduct quality assurance and testing for confirmed requirements"
        evidence_qa = TaskEvidence(
            type="implied",
            source_quote="Verification against confirmed specifications",
            requirement_description="Confirmed project requirements",
            confirmed=True,
        )
        if not _is_duplicate_task(qa_text, seen_tasks):
            items.append(
                ChecklistItem(
                    id=qa_task_id,
                    task=qa_text,
                    priority="high",
                    estimated_effort="1-2 days",
                    depends_on=[prev_id] if prev_id else None,
                    task_type="implementation",
                    evidence=evidence_qa,
                )
            )
            seen_tasks.append(qa_text)
            prev_id = qa_task_id
            task_id += 1

        # Minimum 5 tasks constraint
        if len(items) < 5:
            expansion_candidates = [
                (
                    "Validate core deliverables against client acceptance criteria",
                    "high",
                    "4 hours",
                    TaskEvidence(type="implied", source_quote="Acceptance criteria validation", confirmed=True),
                ),
                (
                    "Prepare project documentation and delivery walkthrough",
                    "medium",
                    "4 hours",
                    TaskEvidence(type="implied", source_quote="Delivery documentation", confirmed=True),
                ),
            ]
            for exp_task, exp_pri, exp_effort, exp_ev in expansion_candidates:
                if len(items) >= 5:
                    break
                if not _is_duplicate_task(exp_task, seen_tasks):
                    items.append(
                        ChecklistItem(
                            id=task_id,
                            task=exp_task,
                            priority=exp_pri,
                            estimated_effort=exp_effort,
                            depends_on=[prev_id] if prev_id else None,
                            task_type="implementation",
                            evidence=exp_ev,
                        )
                    )
                    seen_tasks.append(exp_task)
                    prev_id = task_id
                    task_id += 1

        # Step 6: Application-Level Validation Layer
        items = validate_checklist_evidence(items, brief_text=brief_text, requirements=req_list)

    else:
        # ====================================================================
        # LEGACY TEMPLATE MODE: Maintained for backward compatibility
        # ====================================================================
        team_tpl = templates.get(primary_team, templates.get("Web Development", {}))

        # Architecture & Technical Planning
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
                    task_type="implementation",
                    evidence=TaskEvidence(type="policy", source_quote=planning_text, confirmed=True),
                )
            )
            seen_tasks.append(planning_text)
            task_id += 1

        # Setup & Workspace Environment
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
                    task_type="implementation",
                    evidence=TaskEvidence(type="policy", source_quote=setup_text, confirmed=True),
                )
            )
            seen_tasks.append(setup_text)
            task_id += 1

        # Core Feature Implementation
        prev_id = setup_task_id
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
                        task_type="implementation",
                        evidence=TaskEvidence(
                            type="requirement",
                            source_quote=req.source_quote or req.description,
                            requirement_description=req.description,
                            confirmed=req.confirmed,
                        ),
                    )
                )
                seen_tasks.append(task_text)
                prev_id = task_id
                task_id += 1

        # Supporting teams
        if secondary_teams:
            for st in secondary_teams[:2]:
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
                            task_type="implementation",
                            evidence=TaskEvidence(type="policy", source_quote=st_task_text, confirmed=True),
                        )
                    )
                    seen_tasks.append(st_task_text)
                    prev_id = task_id
                    task_id += 1

        # Testing & QA
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
                    task_type="implementation",
                    evidence=TaskEvidence(type="policy", source_quote=testing_text, confirmed=True),
                )
            )
            seen_tasks.append(testing_text)
            prev_id = qa_task_id
            task_id += 1

        # Deployment
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
                    task_type="implementation",
                    evidence=TaskEvidence(type="policy", source_quote=deployment_text, confirmed=True),
                )
            )
            seen_tasks.append(deployment_text)
            task_id += 1

        # Minimum 5 tasks constraint
        if len(items) < 5:
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
                            task_type="implementation",
                            evidence=TaskEvidence(type="policy", source_quote=exp_task, confirmed=True),
                        )
                    )
                    seen_tasks.append(exp_task)
                    task_id += 1

    # Cap to maximum 12 tasks
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
        "Checklist generated: %d tasks for team '%s' (evidence_bound=%s)",
        len(items),
        primary_team,
        is_evidence_bound,
    )

    return Checklist(
        checklist_type="implementation",
        type="implementation",
        items=items,
        total_tasks=len(items),
        generated_at=datetime.now(timezone.utc),
    )
