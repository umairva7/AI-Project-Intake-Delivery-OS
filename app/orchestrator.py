# app/orchestrator.py
import json
import logging
from datetime import datetime, timezone
from typing import Optional, List, Union

from app.config import settings
from app.models import (
    RawBrief,
    Request,
    ProjectExtraction,
    Requirement,
    TeamRecommendation,
    Checklist,
    ChecklistItem,
    PendingIntake,
    ApprovedIntake,
    UserFeedback,
)
from app.providers.ollama import OllamaProvider
from app.services.recommendation import recommend_team
from app.services.checklist import generate_checklist
from app.storage.db import get_db_connection, init_db

logger = logging.getLogger(__name__)


class IntakeOrchestrator:
    """
    Coordinates the project intake pipeline:
    1. Ingestion: Records raw client brief as a tracked Request.
    2. Extraction: Invokes LLM provider to extract structured requirements.
    3. Allocation: Derives team recommendation and confidence.
    4. Delivery Checklist: Generates initial actionable checklist.
    5. Persistence: Stores pending intake and audits in SQLite database.
    6. Approval: Handles human review, issue marking, and final approval.
    """

    def __init__(self, provider: Optional[OllamaProvider] = None):
        """
        Initialize the orchestrator with an optional LLM provider.
        Defaults to OllamaProvider. Ensures database tables are initialized.
        """
        self.llm = provider or OllamaProvider()
        init_db()

    def process_brief(self, brief: Union[RawBrief, str]) -> PendingIntake:
        """
        Main pipeline workflow:
        Raw brief -> Request -> LLM Extraction -> Team Recommendation -> Checklist -> PendingIntake.

        Args:
            brief: RawBrief model instance or raw brief string.

        Returns:
            PendingIntake ready for human review.
        """
        # Coerce raw string to RawBrief if needed
        if isinstance(brief, str):
            brief = RawBrief(brief_text=brief, source="web_form")

        logger.info(
            "Starting intake processing for brief (source=%s, length=%d)",
            brief.source,
            len(brief.brief_text),
        )

        # 1. Create and persist raw Request record (status: processing)
        request = Request(raw_text=brief.brief_text, source=brief.source)
        self._store_request(request)
        logger.info("Request created: %s", request.id)

        # 2. Call LLM for requirement extraction
        logger.info("LLM extraction started: %s", request.id)
        extraction_result = self.llm.extract_requirements(brief.brief_text)

        # Handle extraction failure or invalid LLM response
        if not extraction_result.valid or not extraction_result.extraction:
            logger.warning(
                "LLM extraction failed for request %s: %s",
                request.id,
                extraction_result.error,
            )
            # Create a safe fallback extraction for human review
            first_line = brief.brief_text.strip().split("\n")[0][:50].strip()
            fallback_title = f"Brief: {first_line}" if len(first_line) >= 3 else "Unstructured Request"

            project_extraction = ProjectExtraction(
                project_name=fallback_title,
                summary=(
                    f"Automated extraction could not be completed ({extraction_result.error or 'Extraction failed'}). "
                    "Raw brief preserved for human triage."
                ),
                requirements=[
                    Requirement(
                        description="Review and manually extract requirements from raw brief",
                        priority="high",
                        confirmed=False,
                        source_quote=brief.brief_text[:200],
                    )
                ],
                missing_information=[
                    "Automated extraction failed; all technical details require manual verification."
                ],
                scope_constraints=[],
                confidence=0.0,
            )
            requires_manual_review = True
            note_content = extraction_result.review_notes or extraction_result.error or "LLM extraction failed"
            review_notes = f"Manual review required: {note_content}"
        else:
            project_extraction = extraction_result.to_project_extraction()
            requires_manual_review = extraction_result.requires_manual_review
            review_notes = extraction_result.review_notes

            logger.info(
                "LLM extraction completed: %s, confidence=%.2f",
                request.id,
                project_extraction.confidence,
            )
            if project_extraction.confidence < settings.CONFIDENCE_THRESHOLD:
                logger.warning(
                    "Low confidence extraction: %s, confidence=%.2f",
                    request.id,
                    project_extraction.confidence,
                )

        # 3. Generate team recommendation (with stage-level fault isolation)
        logger.info("Generating team recommendation: %s", request.id)
        try:
            team_rec = recommend_team(project_extraction)
            logger.info(
                "Team recommendation generated: %s -> %s (confidence=%.2f)",
                request.id,
                team_rec.team,
                team_rec.confidence,
            )
        except Exception as team_err:
            logger.error("Team recommendation failed for %s: %s", request.id, team_err)
            requires_manual_review = True
            team_fail_note = f"Team recommendation failed: {team_err}. Manual team assignment required."
            review_notes = f"{review_notes} {team_fail_note}".strip() if review_notes else team_fail_note
            team_rec = TeamRecommendation(
                team="Pending Triage",
                confidence=0.0,
                reasoning=["Automated team recommendation encountered an error."],
                requires_human_review=True,
            )

        if team_rec.requires_human_review:
            requires_manual_review = True
            rec_note = (
                f"Team recommendation confidence is low ({team_rec.confidence:.2f}); "
                "manual verification advised."
            )
            review_notes = f"{review_notes} {rec_note}".strip() if review_notes else rec_note

        # 4. Generate checklist (with stage-level fault isolation)
        logger.info("Generating checklist: %s", request.id)
        try:
            checklist = generate_checklist(
                requirements=project_extraction.requirements,
                team=team_rec.team,
                missing_information=project_extraction.missing_information,
                supporting_teams=team_rec.supporting_teams,
            )
            logger.info(
                "Checklist generated: %s (%d items)",
                request.id,
                checklist.total_tasks,
            )
        except Exception as check_err:
            logger.error("Checklist generation failed for %s: %s", request.id, check_err)
            requires_manual_review = True
            check_fail_note = f"Checklist generation failed: {check_err}. Manual task entry required."
            review_notes = f"{review_notes} {check_fail_note}".strip() if review_notes else check_fail_note
            checklist = Checklist(
                items=[
                    ChecklistItem(
                        id=1,
                        task="Manually review requirements and compile delivery checklist",
                        priority="high",
                        estimated_effort="1-2 hours",
                    )
                ],
                total_tasks=1,
            )

        # 5. Assemble PendingIntake
        pending = PendingIntake(
            request_id=request.id,
            extracted=project_extraction,
            team_recommendation=team_rec,
            checklist=checklist,
            status="pending_review",
            requires_manual_review=requires_manual_review,
            review_notes=review_notes if requires_manual_review else None,
        )

        # 6. Persist pending intake and update request status
        self._store_intake(pending)
        request.transition_to("pending_review")
        self._update_request_status(request.id, "pending_review")

        logger.info(
            "Intake ready for review: %s (request_id=%s, manual_review=%s)",
            pending.id,
            request.id,
            pending.requires_manual_review,
        )

        return pending

    def approve_intake(self, feedback: UserFeedback) -> ApprovedIntake:
        """
        User reviews and approves the pending intake or marks issues.
        On approval: stores record in approved_intakes and updates status.
        On mark_issues: flags issues in intakes table for corrections.
        """
        pending = self.get_intake(feedback.intake_id)
        if not pending:
            raise ValueError(f"Pending intake '{feedback.intake_id}' not found.")

        if feedback.decision == "approve":
            # Create ApprovedIntake record
            approved = ApprovedIntake(
                request_id=pending.request_id,
                intake_id=pending.id,
                project_name=pending.extracted.project_name,
                summary=pending.extracted.summary,
                requirements=pending.extracted.requirements,
                missing_information=pending.extracted.missing_information,
                team_assignment=pending.team_recommendation.team,
                checklist=pending.checklist.items,
                approved_at=datetime.now(timezone.utc),
                approved_by="system",
                status="approved",
            )
            self._store_approved_intake(approved)
            self._update_intake_status(pending.id, "approved")
            self._update_request_status(pending.request_id, "approved")
            logger.info("Intake approved: %s -> %s", pending.id, approved.id)
            return approved

        elif feedback.decision == "mark_issues":
            issues_json = json.dumps(feedback.issues_detected or [])
            self._update_intake_issues(pending.id, issues_json, feedback.notes)
            logger.info(
                "Intake issues marked: %s (%d issues)",
                pending.id,
                len(feedback.issues_detected or []),
            )
            # Re-fetch updated intake
            return self.get_intake(pending.id)

        elif feedback.decision == "reject":
            self._update_intake_status(pending.id, "rejected")
            self._update_request_status(pending.request_id, "rejected")
            logger.info("Intake rejected: %s", pending.id)
            return None

    # ========================================================================
    # Database Storage & Query Methods
    # ========================================================================

    def _store_request(self, request: Request) -> None:
        """Store raw incoming request in SQLite database"""
        conn = get_db_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO requests (id, raw_text, source, status, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        request.id,
                        request.raw_text,
                        request.source,
                        request.status,
                        request.created_at.isoformat(),
                    ),
                )
        finally:
            conn.close()

    def _update_request_status(self, request_id: str, new_status: str) -> None:
        """Update request status in SQLite database"""
        conn = get_db_connection()
        try:
            with conn:
                conn.execute(
                    "UPDATE requests SET status = ? WHERE id = ?",
                    (new_status, request_id),
                )
        finally:
            conn.close()

    def _store_intake(self, intake: PendingIntake) -> None:
        """Store pending intake in SQLite database"""
        conn = get_db_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO intakes (
                        id, request_id, extracted_json, team_recommendation_json,
                        checklist_json, requires_manual_review, review_notes,
                        issues_marked, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        intake.id,
                        intake.request_id,
                        intake.extracted.model_dump_json() if intake.extracted else None,
                        intake.team_recommendation.model_dump_json()
                        if intake.team_recommendation
                        else None,
                        intake.checklist.model_dump_json() if intake.checklist else None,
                        1 if intake.requires_manual_review else 0,
                        intake.review_notes,
                        None,
                        intake.status,
                        intake.created_at.isoformat(),
                    ),
                )
        finally:
            conn.close()

    def _update_intake_status(self, intake_id: str, new_status: str) -> None:
        """Update intake status in SQLite database"""
        conn = get_db_connection()
        try:
            with conn:
                conn.execute(
                    "UPDATE intakes SET status = ? WHERE id = ?",
                    (new_status, intake_id),
                )
        finally:
            conn.close()

    def _update_intake_issues(
        self,
        intake_id: str,
        issues_json: str,
        notes: Optional[str] = None,
    ) -> None:
        """Record marked issues on intake record"""
        conn = get_db_connection()
        try:
            with conn:
                conn.execute(
                    """
                    UPDATE intakes
                    SET issues_marked = ?,
                        review_notes = CASE WHEN ? IS NOT NULL THEN ? ELSE review_notes END
                    WHERE id = ?
                    """,
                    (issues_json, notes, notes, intake_id),
                )
        finally:
            conn.close()

    def _store_approved_intake(self, approved: ApprovedIntake) -> None:
        """Store approved intake final record in SQLite database"""
        conn = get_db_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO approved_intakes (
                        id, intake_id, request_id, final_data_json,
                        approved_at, approved_by, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        approved.id,
                        approved.intake_id,
                        approved.request_id,
                        approved.model_dump_json(),
                        approved.approved_at.isoformat(),
                        approved.approved_by,
                        approved.status,
                    ),
                )
        finally:
            conn.close()

    def get_request(self, request_id: str) -> Optional[Request]:
        """Retrieve a Request record by ID"""
        conn = get_db_connection()
        try:
            row = conn.execute(
                "SELECT * FROM requests WHERE id = ?", (request_id,)
            ).fetchone()
            if not row:
                return None
            return Request(
                id=row["id"],
                raw_text=row["raw_text"],
                source=row["source"],
                status=row["status"],
                created_at=datetime.fromisoformat(row["created_at"])
                if row["created_at"]
                else datetime.now(timezone.utc),
            )
        finally:
            conn.close()

    def get_intake(self, intake_id: str) -> Optional[PendingIntake]:
        """Retrieve a PendingIntake record by ID"""
        conn = get_db_connection()
        try:
            row = conn.execute(
                "SELECT * FROM intakes WHERE id = ?", (intake_id,)
            ).fetchone()
            if not row:
                return None
            return self._row_to_pending_intake(row)
        finally:
            conn.close()

    def get_intake_by_request_id(self, request_id: str) -> Optional[PendingIntake]:
        """Retrieve a PendingIntake record by its Request ID"""
        conn = get_db_connection()
        try:
            row = conn.execute(
                "SELECT * FROM intakes WHERE request_id = ?", (request_id,)
            ).fetchone()
            if not row:
                return None
            return self._row_to_pending_intake(row)
        finally:
            conn.close()

    def get_approved_intake(self, approved_id: str) -> Optional[ApprovedIntake]:
        """Retrieve an ApprovedIntake record by ID"""
        conn = get_db_connection()
        try:
            row = conn.execute(
                "SELECT * FROM approved_intakes WHERE id = ?", (approved_id,)
            ).fetchone()
            if not row or not row["final_data_json"]:
                return None
            return ApprovedIntake.model_validate_json(row["final_data_json"])
        finally:
            conn.close()

    def _row_to_pending_intake(self, row) -> PendingIntake:
        """Helper to deserialize SQLite row into PendingIntake model"""
        extracted_dict = (
            json.loads(row["extracted_json"]) if row["extracted_json"] else None
        )
        team_rec_dict = (
            json.loads(row["team_recommendation_json"])
            if row["team_recommendation_json"]
            else None
        )
        checklist_dict = (
            json.loads(row["checklist_json"]) if row["checklist_json"] else None
        )

        created_dt = (
            datetime.fromisoformat(row["created_at"])
            if row["created_at"]
            else datetime.now(timezone.utc)
        )

        return PendingIntake(
            id=row["id"],
            request_id=row["request_id"],
            extracted=ProjectExtraction.model_validate(extracted_dict),
            team_recommendation=TeamRecommendation.model_validate(team_rec_dict),
            checklist=Checklist.model_validate(checklist_dict),
            status=row["status"] or "pending_review",
            requires_manual_review=bool(row["requires_manual_review"]),
            review_notes=row["review_notes"],
            created_at=created_dt,
        )
