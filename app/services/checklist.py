# app/services/checklist.py
import logging
from typing import List, Optional
from datetime import datetime, timezone

from app.models import Checklist, ChecklistItem, Requirement

logger = logging.getLogger(__name__)


def generate_checklist(
    requirements: List[Requirement],
    team: str = "Web Development",
    missing_information: Optional[List[str]] = None,
) -> Checklist:
    """
    Generate an ordered delivery checklist for the intake project.

    Args:
        requirements: Extracted functional and technical requirements.
        team: Recommended delivery team name.
        missing_information: List of missing requirements or unknowns to clarify.

    Returns:
        Checklist instance containing ordered ChecklistItem tasks and metadata.
    """
    items: List[ChecklistItem] = []
    task_id = 1

    # 1. Missing information clarification tasks (High priority, initial step)
    if missing_information:
        for missing in missing_information[:3]:  # Top missing items
            clean_missing = missing.strip().rstrip(".")
            items.append(
                ChecklistItem(
                    id=task_id,
                    task=f"Clarify with client: {clean_missing}",
                    priority="high",
                    estimated_effort="1-2 hours",
                    depends_on=None,
                )
            )
            task_id += 1

    # 2. Team technical architecture & foundation
    arch_task_id = task_id
    items.append(
        ChecklistItem(
            id=arch_task_id,
            task=f"Define technical architecture and project structure for {team}",
            priority="high",
            estimated_effort="1 day",
            depends_on=[1] if task_id > 1 else None,
        )
    )
    task_id += 1

    # 3. Core feature implementation tasks derived from extracted requirements
    prev_id = arch_task_id
    for req in requirements[:6]:  # Process up to 6 core requirements for initial delivery
        desc = req.description.strip().rstrip(".")
        # Clean up leading "We need" or similar if present
        if desc.lower().startswith("we need "):
            desc = desc[8:]
        elif desc.lower().startswith("create ") or desc.lower().startswith("build "):
            desc = desc[0].upper() + desc[1:]
        else:
            desc = f"Implement {desc}"

        items.append(
            ChecklistItem(
                id=task_id,
                task=desc,
                priority=req.priority,
                estimated_effort="2-3 days",
                depends_on=[prev_id],
            )
        )
        prev_id = task_id
        task_id += 1

    # 4. Verification and QA acceptance testing
    items.append(
        ChecklistItem(
            id=task_id,
            task="Perform comprehensive QA acceptance testing and review against requirements",
            priority="high",
            estimated_effort="1-2 days",
            depends_on=[prev_id],
        )
    )

    return Checklist(
        items=items,
        total_tasks=len(items),
        generated_at=datetime.now(timezone.utc),
    )
