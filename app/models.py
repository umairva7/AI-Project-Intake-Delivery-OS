from datetime import datetime, timezone
from typing import Optional, List, Literal, Dict, Any, Union
from uuid import uuid4
from pydantic import BaseModel, Field, ConfigDict, model_validator


VALID_REQUEST_TRANSITIONS: Dict[str, List[str]] = {
    "processing": ["pending_review", "rejected"],
    "pending_review": ["approved", "rejected"],
    "approved": [],  # Terminal state
    "rejected": [],  # Terminal state
}

VALID_INTAKE_TRANSITIONS: Dict[str, List[str]] = {
    "draft": ["pending_review"],
    "pending_review": [],  # Terminal state awaiting final approval
}


class RawBrief(BaseModel):
    """Raw input from user"""

    brief_text: str = Field(
        ...,
        min_length=10,  # Require meaningful input
        max_length=5000,
        description="The client/project request text",
    )
    source: str = Field(
        default="web_form",
        description="Where the brief came from: 'web_form', 'api', 'email', etc.",
    )
    submitted_at: Optional[datetime] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "brief_text": "We need a React frontend with Python API...",
                "source": "web_form",
            }
        }
    )


class Request(BaseModel):
    """Tracks a raw incoming request"""

    id: str = Field(default_factory=lambda: f"REQ-{uuid4().hex[:8]}")
    raw_text: str
    source: str
    submitted_at: Optional[datetime] = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    status: Literal["processing", "pending_review", "approved", "rejected"] = (
        Field(
            default="processing",
            description="processing | pending_review | approved | rejected",
        )
    )

    def transition_to(
        self,
        target_status: Literal[
            "processing", "pending_review", "approved", "rejected"
        ],
    ) -> None:
        """Transitions request to a new status following valid lifecycle workflow."""
        allowed = VALID_REQUEST_TRANSITIONS.get(self.status, [])
        if target_status not in allowed:
            raise ValueError(
                f"Invalid state transition: cannot transition Request from '{self.status}' to '{target_status}'. "
                f"Allowed transitions from '{self.status}': {allowed or 'None (terminal state)'}"
            )
        self.status = target_status

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "REQ-abc12345",
                "raw_text": "...",
                "source": "web_form",
                "created_at": "2026-09-14T12:00:00Z",
                "status": "processing",
            }
        }
    )


class Requirement(BaseModel):
    """A single extracted requirement"""

    description: str = Field(
        ..., min_length=5, description="What is required (e.g., 'React frontend')"
    )
    priority: Literal["high", "medium", "low"] = Field(
        default="medium", description="How critical is this requirement?"
    )
    confirmed: bool = Field(
        default=True,
        description="Was this explicitly stated or inferred by LLM?",
    )
    source_quote: Optional[str] = Field(
        default=None,
        description="The exact text from the brief that led to this requirement",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "description": "React frontend with TypeScript",
                "priority": "high",
                "confirmed": True,
                "source_quote": "We need a React frontend",
            }
        }
    )


class ProjectExtraction(BaseModel):
    """Structured extraction from raw brief by LLM"""

    project_name: str = Field(
        ..., min_length=3, description="Inferred project name from brief"
    )
    summary: str = Field(
        ..., min_length=20, description="2-3 sentence summary of what's being asked"
    )
    requirements: List[Requirement] = Field(
        ...,
        min_length=1,
        description="Extracted functional and technical requirements",
    )
    missing_information: List[str] = Field(
        default_factory=list,
        description="Information that would clarify the brief",
    )
    scope_constraints: List[str] = Field(
        default_factory=list,
        description="Budget, timeline, resource constraints mentioned",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="How confident is the LLM in this extraction? (0.0 to 1.0)",
    )
    extraction_status: Literal["validated", "failed"] = Field(
        default="validated",
        description="Explicit extraction status ('validated' or 'failed')",
    )

    @property
    def extraction_confidence(self) -> float:
        return self.confidence

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_name": "Employee Dashboard",
                "summary": "Internal dashboard for tracking employee projects and work hours.",
                "requirements": [
                    {
                        "description": "React frontend",
                        "priority": "high",
                        "confirmed": True,
                        "source_quote": "We need a React frontend",
                    }
                ],
                "missing_information": [
                    "Number of expected users",
                    "Performance requirements",
                ],
                "scope_constraints": ["6 weeks timeline", "$50,000 budget"],
                "confidence": 0.92,
                "extraction_status": "validated",
            }
        }
    )


class ExtractionResult(BaseModel):
    """Result of LLM extraction process, including validation and review metadata"""

    valid: bool = Field(
        default=True, description="Whether extraction was valid and parsed"
    )
    extraction_status: Optional[Literal["validated", "failed"]] = Field(
        default=None, description="Explicit extraction status ('validated' or 'failed')"
    )
    extraction: Optional[ProjectExtraction] = Field(
        default=None, description="Structured project extraction if valid"
    )
    error: Optional[str] = Field(
        default=None, description="Internal error message if extraction failed"
    )
    user_message: Optional[str] = Field(
        default=None, description="User-friendly message explaining status"
    )
    requires_manual_review: bool = Field(
        default=False, description="Whether human review is required"
    )
    review_notes: Optional[str] = Field(
        default=None, description="Notes on why manual review is needed"
    )
    raw_response: Optional[str] = Field(
        default=None, description="Raw LLM response string"
    )
    retry_count: int = Field(
        default=0, description="Number of retries attempted"
    )

    @model_validator(mode="after")
    def sync_extraction_status(self) -> "ExtractionResult":
        if self.extraction_status is None:
            self.extraction_status = (
                "validated" if (self.valid and self.extraction is not None) else "failed"
            )
        if self.extraction is not None:
            if not hasattr(self.extraction, "extraction_status") or self.extraction.extraction_status != self.extraction_status:
                self.extraction.extraction_status = self.extraction_status
        return self

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    def __bool__(self) -> bool:
        return self.valid

    @property
    def project_name(self) -> str:
        return self.extraction.project_name if self.extraction else ""

    @property
    def summary(self) -> str:
        return self.extraction.summary if self.extraction else ""

    @property
    def requirements(self) -> List[Requirement]:
        return self.extraction.requirements if self.extraction else []

    @property
    def missing_information(self) -> List[str]:
        return self.extraction.missing_information if self.extraction else []

    @property
    def scope_constraints(self) -> List[str]:
        return self.extraction.scope_constraints if self.extraction else []

    @property
    def confidence(self) -> float:
        return self.extraction.confidence if self.extraction else 0.0

    @property
    def extraction_confidence(self) -> float:
        return self.confidence

    def to_project_extraction(self) -> Optional[ProjectExtraction]:
        return self.extraction


def extraction_is_usable(
    extraction: Optional[Union[ProjectExtraction, ExtractionResult, Any]]
) -> bool:
    """
    Authoritative Extraction Gate.
    Determines whether an extraction is valid and confident enough to be used
    for downstream implementation-specific team recommendation and checklist generation.

    Invariants:
      - extraction must not be None
      - extraction_status must be 'validated' (not 'failed')
      - extraction_confidence / confidence must be > 0.0
    """
    if extraction is None:
        return False

    if isinstance(extraction, ExtractionResult):
        if not extraction.valid or extraction.extraction is None:
            return False
        extraction = extraction.extraction

    status = getattr(extraction, "extraction_status", "validated")
    if status == "failed":
        return False

    conf = getattr(extraction, "confidence", None)
    if conf is None:
        conf = getattr(extraction, "extraction_confidence", 0.0)

    if conf is None or conf <= 0.0:
        return False

    return status == "validated"


class ChecklistItem(BaseModel):
    """Single item in the delivery checklist"""

    id: Optional[int] = Field(
        default=None, description="Sequential task ID for dependency tracking"
    )
    task: str = Field(..., description="What needs to be done?")
    title: Optional[str] = Field(default=None, description="Alias for task")
    priority: Literal["high", "medium", "low"] = Field(default="medium")
    estimated_effort: Optional[str] = Field(
        default=None, description="e.g., '2 hours', '1 day', 'TBD'"
    )
    depends_on: Optional[List[int]] = Field(
        default=None, description="Task IDs this depends on (if any)"
    )

    @model_validator(mode="before")
    @classmethod
    def sync_task_and_title(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "task" in data and not data.get("title"):
                data["title"] = data["task"]
            elif "title" in data and not data.get("task"):
                data["task"] = data["title"]
        return data

    @property
    def item_title(self) -> str:
        return self.title or self.task

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "task": "Confirm user base size with client",
                "title": "Confirm user base size with client",
                "priority": "high",
                "estimated_effort": "30 minutes",
                "depends_on": None,
            }
        }
    )


class Checklist(BaseModel):
    """Generated delivery checklist"""

    checklist_type: Literal["implementation", "clarification"] = Field(
        default="implementation",
        description="Type of checklist: 'implementation' for validated extraction, 'clarification' for failed/unusable extraction",
    )
    type: Optional[str] = Field(
        default="implementation",
        description="Alias for checklist_type ('implementation' | 'clarification')",
    )
    items: List[ChecklistItem] = Field(
        ..., description="Ordered list of immediate next steps"
    )
    total_tasks: int = Field(description="Number of tasks in checklist")
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @model_validator(mode="before")
    @classmethod
    def sync_checklist_types(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "checklist_type" in data and "type" not in data:
                data["type"] = data["checklist_type"]
            elif "type" in data and "checklist_type" not in data:
                data["checklist_type"] = data["type"]
        return data

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "checklist_type": "implementation",
                "type": "implementation",
                "items": [
                    {"id": 1, "task": "Confirm user base size", "title": "Confirm user base size", "priority": "high"}
                ],
                "total_tasks": 1,
                "generated_at": "2026-09-14T12:00:00Z",
            }
        }
    )


class TeamRecommendation(BaseModel):
    """Recommendation for team allocation"""

    team: Optional[str] = Field(
        default=None,
        description="Recommended primary team name, e.g. 'Web Development', 'Mobile Development', 'AI / ML'",
    )
    recommended_team: Optional[str] = Field(
        default=None,
        description="Alias for recommended primary team name",
    )
    supporting_teams: List[str] = Field(
        default_factory=list,
        description="Secondary or supporting teams for cross-functional projects",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for team fit (0.0 to 1.0)",
    )
    reasoning: List[str] = Field(
        default_factory=list,
        description="List of reasons supporting this recommendation",
    )
    alternative_team: Optional[str] = Field(
        default=None,
        description="Alternative team option if confidence is low or requirements are cross-functional",
    )
    requires_human_review: bool = Field(
        default=False,
        description="Flag if confidence is below threshold or teams are ambiguous",
    )

    @model_validator(mode="before")
    @classmethod
    def sync_team_and_supporting(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Sync team and recommended_team
            if "recommended_team" in data and not data.get("team"):
                data["team"] = data["recommended_team"]
            elif "team" in data and not data.get("recommended_team"):
                data["recommended_team"] = data["team"]

            # Sync alternative_team and supporting_teams
            if "supporting_teams" in data and data["supporting_teams"] and not data.get("alternative_team"):
                data["alternative_team"] = data["supporting_teams"][0]
            elif "alternative_team" in data and data["alternative_team"] and not data.get("supporting_teams"):
                data["supporting_teams"] = [data["alternative_team"]]
        return data

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "team": "Web Development",
                "recommended_team": "Web Development",
                "supporting_teams": [],
                "confidence": 0.91,
                "reasoning": [
                    "Primary deliverable is a web application",
                    "Requirements include React frontend and Python backend",
                ],
                "alternative_team": None,
                "requires_human_review": False,
            }
        }
    )


class PendingIntake(BaseModel):
    """Extracted intake awaiting human review/approval"""

    id: str = Field(default_factory=lambda: f"INT-{uuid4().hex[:8]}")
    request_id: str = Field(description="Links back to original request")
    raw_brief: Optional[str] = Field(
        default=None, description="Original unparsed client brief text"
    )
    original_brief: Optional[str] = Field(
        default=None, description="Alias for raw_brief"
    )
    extracted: ProjectExtraction
    team_recommendation: TeamRecommendation
    checklist: Checklist
    status: Literal["draft", "pending_review"] = Field(default="pending_review")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    requires_manual_review: bool = Field(
        default=False, description="Did LLM fail or low confidence?"
    )
    review_notes: Optional[str] = Field(
        default=None, description="Why is manual review required?"
    )

    @model_validator(mode="before")
    @classmethod
    def sync_brief_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "raw_brief" in data and not data.get("original_brief"):
                data["original_brief"] = data["raw_brief"]
            elif "original_brief" in data and not data.get("raw_brief"):
                data["raw_brief"] = data["original_brief"]
        return data

    @model_validator(mode="after")
    def validate_manual_review_relationship(self) -> "PendingIntake":
        """Ensures that if manual review is required, explanation notes are provided."""
        if self.requires_manual_review:
            if not self.review_notes or not self.review_notes.strip():
                raise ValueError(
                    "review_notes are required when requires_manual_review is True"
                )
        return self

    def transition_to(
        self, target_status: Literal["draft", "pending_review"]
    ) -> None:
        """Transitions pending intake following valid lifecycle workflow."""
        allowed = VALID_INTAKE_TRANSITIONS.get(self.status, [])
        if target_status not in allowed:
            raise ValueError(
                f"Invalid state transition: cannot transition PendingIntake from '{self.status}' to '{target_status}'. "
                f"Allowed transitions from '{self.status}': {allowed or 'None (terminal state)'}"
            )
        self.status = target_status

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "INT-abc12345",
                "request_id": "REQ-xyz98765",
                "extracted": {},
                "team_recommendation": {},
                "checklist": {},
                "status": "pending_review",
                "requires_manual_review": False,
            }
        }
    )


# Alias for semantic clarity across documentation
ReviewedBrief = PendingIntake


class UserFeedback(BaseModel):
    """User's response to pending intake"""

    intake_id: str
    decision: Literal["approve", "mark_issues", "reject"]
    issues_detected: Optional[List[str]] = Field(
        default=None, description="What problems did the user find?"
    )
    corrections: Optional[Dict[str, Any]] = Field(
        default=None, description="Fields the user corrected (if any)"
    )
    notes: Optional[str] = Field(
        default=None, description="Additional feedback from user"
    )

    @model_validator(mode="after")
    def validate_feedback_relationship(self) -> "UserFeedback":
        """Ensures that issues are documented when decision is 'mark_issues'."""
        if self.decision == "mark_issues" and not self.issues_detected:
            raise ValueError(
                "issues_detected list cannot be empty or None when decision is 'mark_issues'"
            )
        return self

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "intake_id": "INT-abc12345",
                "decision": "mark_issues",
                "issues_detected": [
                    "Missing information about database choice",
                    "Team recommendation should include DevOps",
                ],
                "corrections": None,
                "notes": "Please clarify with client first",
            }
        }
    )


class ApprovedIntake(BaseModel):
    """Final approved intake ready for project delivery"""

    id: str = Field(default_factory=lambda: f"APPROVED-{uuid4().hex[:8]}")
    request_id: str
    intake_id: str = Field(description="Links back to pending intake")
    project_name: str
    summary: str
    requirements: List[Requirement]
    missing_information: List[str] = Field(default_factory=list)
    team_assignment: str
    checklist: List[ChecklistItem]
    approved_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    approved_by: Optional[str] = Field(
        default="system", description="Who approved this? (For audit trail)"
    )
    status: Literal["approved", "in_progress", "completed"] = Field(
        default="approved"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "APPROVED-abc12345",
                "request_id": "REQ-xyz98765",
                "intake_id": "INT-abc12345",
                "project_name": "Employee Dashboard",
                "summary": "Internal dashboard for employees...",
                "requirements": [],
                "team_assignment": "Web Development",
                "checklist": [],
                "approved_at": "2026-09-14T12:05:00Z",
                "approved_by": "system",
                "status": "approved",
            }
        }
    )


class ErrorResponse(BaseModel):
    """API error response"""

    error: str = Field(description="User-friendly error message")
    error_code: Optional[str] = Field(
        default=None, description="Machine-readable error code for logging"
    )
    details: Optional[str] = Field(
        default=None, description="Technical details (only if DEBUG=True)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "We couldn't confidently extract requirements from this brief.",
                "error_code": "EXTRACTION_LOW_CONFIDENCE",
                "details": None,
            }
        }
    )
