from fastapi import FastAPI, HTTPException
from app.orchestrator import IntakeOrchestrator
from app.models import RawBrief, PendingIntake

app = FastAPI(title="AI Project Intake")
orchestrator = IntakeOrchestrator()

# POST /briefs — Submit a brief
@app.post("/briefs", response_model=PendingIntake)
def create_brief(brief_text: str):
    """Submit a raw project brief. Returns pending intake for review."""
    try:
        result = orchestrator.process_brief(brief_text)
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
def flag_issues(brief_id: str, issues: list[str]):
    """Mark issues with a pending intake, flag for review."""
    try:
        orchestrator.mark_issues(brief_id, issues)
        return {"status": "flagged", "id": brief_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))