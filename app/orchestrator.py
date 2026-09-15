# app/orchestrator.py
from app.models import (
    RawBrief, Request, ProjectExtraction, TeamRecommendation,
    PendingIntake, ApprovedIntake, UserFeedback
)
from app.providers.ollama import OllamaProvider
from app.services.recommendation import recommend_team
from app.services.checklist import generate_checklist
from app.storage.db import get_db_connection
from app.config import settings
import json
import logging
from uuid import uuid4
from datetime import datetime

logger = logging.getLogger(__name__)

class IntakeOrchestrator:
    """Orchestrate the project intake workflow"""
    
    def __init__(self):
        self.llm = OllamaProvider()
    
    def process_brief(self, brief: RawBrief) -> PendingIntake:
        """
        Main workflow: extract, validate, recommend, generate checklist.
        Returns PendingIntake ready for user review.
        """
        # 1. Create request record
        request = Request(raw_text=brief.brief_text, source=brief.source)
        self._store_request(request)
        logger.info(f"Created request: {request.id}")
        
        # 2. Call LLM for extraction
        extraction = self.llm.extract_requirements(brief.brief_text)
        if extraction is None:
            logger.warning(f"Extraction failed for request {request.id}")
            # Create placeholder pending intake that requires manual review
            pending = PendingIntake(
                request_id=request.id,
                extracted=None,  # TODO: Handle None case in model
                team_recommendation=None,
                checklist=None,
                requires_manual_review=True,
                review_notes="LLM extraction failed. Manual review required."
            )
            self._store_intake(pending)
            return pending
        
        # 3. Check confidence
        if extraction.confidence < settings.CONFIDENCE_THRESHOLD:
            logger.warning(f"Low confidence extraction: {extraction.confidence}")
            # Mark for review but continue
        
        # 4. Get team recommendation
        team_rec = recommend_team(extraction)
        logger.info(f"Team recommendation: {team_rec.recommended_team}")
        
        # 5. Generate checklist
        checklist = generate_checklist(extraction.requirements, team_rec.recommended_team)
        logger.info(f"Generated checklist with {checklist.total_tasks} items")
        
        # 6. Create pending intake
        pending = PendingIntake(
            request_id=request.id,
            extracted=extraction,
            team_recommendation=team_rec,
            checklist=checklist,
            requires_manual_review=extraction.confidence < settings.CONFIDENCE_THRESHOLD
        )
        
        # 7. Store
        self._store_intake(pending)
        logger.info(f"Intake created: {pending.id}")
        
        return pending
    
    def approve_intake(self, feedback: UserFeedback) -> ApprovedIntake:
        """User marks issues or approves. Store final intake."""
        # TODO: Retrieve pending intake
        # TODO: Validate feedback
        # TODO: Store approved intake
        # TODO: Return approved intake
        pass
    
    def _store_request(self, request: Request):
        """Store raw request in database"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO requests (id, raw_text, source, status, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (request.id, request.raw_text, request.source, request.status, request.created_at))
        conn.commit()
        conn.close()
    
    def _store_intake(self, intake: PendingIntake):
        """Store pending intake in database"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO intakes (id, request_id, extracted_json, team_recommendation_json, checklist_json, requires_manual_review, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            intake.id,
            intake.request_id,
            intake.extracted.model_dump_json() if intake.extracted else None,
            intake.team_recommendation.model_dump_json() if intake.team_recommendation else None,
            intake.checklist.model_dump_json() if intake.checklist else None,
            intake.requires_manual_review,
            intake.status,
            intake.created_at
        ))
        conn.commit()
        conn.close()