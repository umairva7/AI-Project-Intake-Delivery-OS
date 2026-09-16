from typing import Union
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.orchestrator import IntakeOrchestrator
from app.models import RawBrief, PendingIntake

app = FastAPI(title="AI Project Intake")
orchestrator = IntakeOrchestrator()

# Configure CORS for local development and frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:5000",
        "http://localhost:5500",
        "http://localhost:8000",
        "http://localhost:8080",
        "http://127.0.0.1",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5000",
        "http://127.0.0.1:5500",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8080",
        "null",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MarkIssuesRequest(BaseModel):
    issues: list[str] = Field(..., min_length=1, description="List of issues detected in brief")


# POST /briefs — Submit a brief
@app.post("/briefs", response_model=PendingIntake)
def create_brief(brief: RawBrief):
    """Submit a raw project brief. Returns pending intake for review."""
    try:
        result = orchestrator.process_brief(brief)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal error")


# GET /briefs/{brief_id} — Get pending intake
@app.get("/briefs/{brief_id}", response_model=PendingIntake)
def get_brief(brief_id: str):
    """Retrieve a pending intake by ID."""
    intake = orchestrator.get_pending_intake_by_id(brief_id)
    if not intake:
        raise HTTPException(status_code=404, detail="Intake not found")
    return intake


# POST /briefs/{brief_id}/approve — Approve it
@app.post("/briefs/{brief_id}/approve")
def approve_brief(brief_id: str):
    """Approve a pending intake, move to approved_intakes."""
    try:
        orchestrator.approve_intake(brief_id)
        return {"status": "approved", "id": brief_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# POST /briefs/{brief_id}/mark-issues — Flag problems
@app.post("/briefs/{brief_id}/mark-issues")
def flag_issues(brief_id: str, payload: Union[MarkIssuesRequest, list[str]] = Body(...)):
    """Mark issues with a pending intake, flag for review."""
    issues = payload.issues if isinstance(payload, MarkIssuesRequest) else payload
    try:
        orchestrator.mark_issues(brief_id, issues)
        return {"status": "flagged", "id": brief_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Mount frontend static files for direct browser access
from pathlib import Path
from fastapi.staticfiles import StaticFiles

frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/frontend", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")