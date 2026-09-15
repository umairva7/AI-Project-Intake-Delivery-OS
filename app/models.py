from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime
from uuid import uuid4


class RawBrief(BaseModel):
    """Raw input from user"""
    
    brief_text: str = Field(
        ..., 
        min_length=10,  # Require meaningful input
        max_length=5000,
        description="The client/project request text"
    )
    source: str = Field(
        default="web_form",
        description="Where the brief came from: 'web_form', 'api', 'email', etc."
    )
    submitted_at: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "brief_text": "We need a React frontend with Python API...",
                "source": "web_form"
            }
        }


class Request(BaseModel):
    """Tracks a raw incoming request"""
    
    id: str = Field(default_factory=lambda: f"REQ-{uuid4().hex[:8]}")
    raw_text: str
    source: str
    submitted_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(
        default="processing",
        description="processing | pending_review | approved | rejected"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "REQ-abc12345",
                "raw_text": "...",
                "source": "web_form",
                "created_at": "2026-09-14T12:00:00",
                "status": "processing"
            }
        }

from typing import Literal

class Requirement(BaseModel):
    """A single extracted requirement"""
    
    description: str = Field(
        ...,
        min_length=5,
        description="What is required (e.g., 'React frontend')"
    )
    priority: Literal["high", "medium", "low"] = Field(
        default="medium",
        description="How critical is this requirement?"
    )
    confirmed: bool = Field(
        default=True,
        description="Was this explicitly stated or inferred by LLM?"
    )
    source_quote: Optional[str] = Field(
        default=None,
        description="The exact text from the brief that led to this requirement"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "description": "React frontend with TypeScript",
                "priority": "high",
                "confirmed": True,
                "source_quote": "We need a React frontend"
            }
        }

class ProjectExtraction(BaseModel):
    """Structured extraction from raw brief by LLM"""
    
    project_name: str = Field(
        ...,
        min_length=3,
        description="Inferred project name from brief"
    )
    summary: str = Field(
        ...,
        min_length=20,
        description="2-3 sentence summary of what's being asked"
    )
    requirements: List[Requirement] = Field(
        ...,
        min_items=1,
        description="Extracted functional and technical requirements"
    )
    missing_information: List[str] = Field(
        default=[],
        description="Information that would clarify the brief"
    )
    scope_constraints: List[str] = Field(
        default=[],
        description="Budget, timeline, resource constraints mentioned"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="How confident is the LLM in this extraction? (0.0 to 1.0)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "project_name": "Employee Dashboard",
                "summary": "Internal dashboard for tracking employee projects and work hours.",
                "requirements": [
                    {
                        "description": "React frontend",
                        "priority": "high",
                        "confirmed": True,
                        "source_quote": "We need a React frontend"
                    }
                ],
                "missing_information": [
                    "Number of expected users",
                    "Performance requirements"
                ],
                "scope_constraints": [
                    "6 weeks timeline",
                    "$50,000 budget"
                ],
                "confidence": 0.92
            }
        }

class ChecklistItem(BaseModel):
    """Single item in the delivery checklist"""
    
    task: str = Field(
        ...,
        description="What needs to be done?"
    )
    priority: Literal["high", "medium", "low"] = Field(
        default="medium"
    )
    estimated_effort: Optional[str] = Field(
        default=None,
        description="e.g., '2 hours', '1 day', 'TBD'"
    )
    depends_on: Optional[List[int]] = Field(
        default=None,
        description="Task IDs this depends on (if any)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "task": "Confirm user base size with client",
                "priority": "high",
                "estimated_effort": "30 minutes",
                "depends_on": None
            }
        }



class Checklist(BaseModel):
    """Generated delivery checklist"""
    
    items: List[ChecklistItem] = Field(
        ...,
        description="Ordered list of immediate next steps"
    )
    total_tasks: int = Field(
        description="Number of tasks in checklist"
    )
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "task": "Confirm user base size",
                        "priority": "high"
                    }
                ],
                "total_tasks": 6,
                "generated_at": "2026-09-14T12:00:00"
            }
        }

class TeamRecommendation(BaseModel):
    """LLM recommendation for team allocation"""
    
    team: str = Field(
        ...,
        description="Recommended team name, e.g. 'Web Development', 'Mobile Development', 'AI / ML'"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for team fit (0.0 to 1.0)"
    )
    reasoning: List[str] = Field(
        default_factory=list,
        description="List of reasons supporting this recommendation"
    )
    alternative_team: Optional[str] = Field(
        default=None,
        description="Alternative team option if confidence is low or requirements are cross-functional"
    )
    requires_human_review: bool = Field(
        default=False,
        description="Flag if confidence is below threshold or teams are ambiguous"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "team": "Web Development",
                "confidence": 0.91,
                "reasoning": [
                    "Primary deliverable is a web application",
                    "Requirements include React frontend and Python backend"
                ],
                "alternative_team": None,
                "requires_human_review": False
            }
        }


class PendingIntake(BaseModel):
    """Extracted intake awaiting human review/approval"""
    
    id: str = Field(
        default_factory=lambda: f"INT-{uuid4().hex[:8]}"
    )
    request_id: str = Field(
        description="Links back to original request"
    )
    extracted: ProjectExtraction
    team_recommendation: TeamRecommendation
    checklist: Checklist
    status: Literal["draft", "pending_review"] = Field(
        default="pending_review"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    requires_manual_review: bool = Field(
        default=False,
        description="Did LLM fail or low confidence?"
    )
    review_notes: Optional[str] = Field(
        default=None,
        description="Why is manual review required?"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "INT-abc12345",
                "request_id": "REQ-xyz98765",
                "extracted": {...},
                "team_recommendation": {...},
                "checklist": {...},
                "status": "pending_review",
                "requires_manual_review": False
            }
        }

from typing import Optional, List

class UserFeedback(BaseModel):
    """User's response to pending intake"""
    
    intake_id: str
    decision: Literal["approve", "mark_issues", "reject"]
    issues_detected: Optional[List[str]] = Field(
        default=None,
        description="What problems did the user find?"
    )
    corrections: Optional[dict] = Field(
        default=None,
        description="Fields the user corrected (if any)"
    )
    notes: Optional[str] = Field(
        default=None,
        description="Additional feedback from user"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "intake_id": "INT-abc12345",
                "decision": "mark_issues",
                "issues_detected": [
                    "Missing information about database choice",
                    "Team recommendation should include DevOps"
                ],
                "corrections": None,
                "notes": "Please clarify with client first"
            }
        }
class ApprovedIntake(BaseModel):
    """Final approved intake ready for project delivery"""
    
    id: str = Field(
        default_factory=lambda: f"APPROVED-{uuid4().hex[:8]}"
    )
    request_id: str
    intake_id: str = Field(
        description="Links back to pending intake"
    )
    project_name: str
    summary: str
    requirements: List[Requirement]
    missing_information: List[str]
    team_assignment: str
    checklist: List[ChecklistItem]
    approved_at: datetime = Field(default_factory=datetime.utcnow)
    approved_by: Optional[str] = Field(
        default="system",
        description="Who approved this? (For audit trail)"
    )
    status: Literal["approved", "in_progress", "completed"] = Field(
        default="approved"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "APPROVED-abc12345",
                "request_id": "REQ-xyz98765",
                "intake_id": "INT-abc12345",
                "project_name": "Employee Dashboard",
                "summary": "Internal dashboard for employees...",
                "requirements": [...],
                "team_assignment": "Web Development",
                "checklist": [...],
                "approved_at": "2026-09-14T12:05:00",
                "approved_by": "system",
                "status": "approved"
            }
        }

class ErrorResponse(BaseModel):
    """API error response"""
    
    error: str = Field(
        description="User-friendly error message"
    )
    error_code: Optional[str] = Field(
        default=None,
        description="Machine-readable error code for logging"
    )
    details: Optional[str] = Field(
        default=None,
        description="Technical details (only if DEBUG=True)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "We couldn't confidently extract requirements from this brief. Could you add more details about: Technology preferences, Timeline, Budget",
                "error_code": "EXTRACTION_LOW_CONFIDENCE",
                "details": None
            }
        }
