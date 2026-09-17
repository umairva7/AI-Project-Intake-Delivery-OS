import logging
from typing import Union
from pathlib import Path
from fastapi import FastAPI, HTTPException, Body, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import settings
from app.orchestrator import IntakeOrchestrator
from app.models import RawBrief, PendingIntake

logger = logging.getLogger(__name__)

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


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return user-friendly message when request schema validation fails instead of tracebacks."""
    logger.warning("Input validation failed on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=400,
        content={"detail": "This brief is unclear. Please provide more specific details."},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Ensure no unhandled internal exception ever leaks a raw Python traceback to the client."""
    if isinstance(exc, HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    logger.error("API unhandled exception on %s: %s", request.url.path, exc, exc_info=True)
    err_str = str(exc).lower()
    if "connection refused" in err_str or "offline" in err_str or "11434" in err_str:
        if "ollama" in err_str:
            detail = "AI system unavailable. Please ensure Ollama is running on http://localhost:11434"
        elif settings.LLM_PROVIDER.lower() == "groq":
            detail = "AI system unavailable. Please check your network connection or Groq API configuration."
        else:
            detail = f"AI system unavailable. Please ensure {settings.LLM_PROVIDER.capitalize()} is running."
    else:
        detail = (
            "We couldn't confidently extract requirements from this brief. \n"
            "Could you add more details about: Technology preferences, Timeline, Budget"
        )
    return JSONResponse(status_code=500, content={"detail": detail})


@app.get("/health")
@app.get("/api/health")
def health_check():
    """Health check endpoint for deployment verification."""
    return {"status": "ok", "provider": settings.LLM_PROVIDER, "service": "AI Project Intake API"}


class MarkIssuesRequest(BaseModel):
    issues: list[str] = Field(..., min_length=1, description="List of issues detected in brief")


# POST /briefs — Submit a brief
@app.post("/briefs", response_model=PendingIntake)
def create_brief(brief: RawBrief):
    """Submit a raw project brief. Returns pending intake for review."""
    logger.info("API: Processing new brief submission (source=%s, length=%d)", brief.source, len(brief.brief_text))
    try:
        result = orchestrator.process_brief(brief)
        logger.info(
            "API: Brief processed successfully into intake %s (request_id=%s, manual_review=%s)",
            result.id,
            result.request_id,
            result.requires_manual_review,
        )
        return result
    except ValueError as e:
        logger.warning("API: Validation failure in brief processing: %s", e)
        raise HTTPException(
            status_code=400,
            detail="This brief is unclear. Please provide more specific details.",
        )
    except Exception as e:
        logger.error("API: Unexpected error during brief processing: %s", e, exc_info=True)
        err_str = str(e).lower()
        if "connection refused" in err_str or "offline" in err_str:
            if "ollama" in err_str:
                detail = "AI system unavailable. Please ensure Ollama is running on http://localhost:11434"
            elif settings.LLM_PROVIDER.lower() == "groq":
                detail = "AI system unavailable. Please check your network connection or Groq API configuration."
            else:
                detail = f"AI system unavailable. Please ensure {settings.LLM_PROVIDER.capitalize()} is running."
        else:
            detail = (
                "We couldn't confidently extract requirements from this brief. \n"
                "Could you add more details about: Technology preferences, Timeline, Budget"
            )
        raise HTTPException(status_code=500, detail=detail)


# GET /briefs/{brief_id} — Get pending intake
@app.get("/briefs/{brief_id}", response_model=PendingIntake)
def get_brief(brief_id: str):
    """Retrieve a pending intake by ID."""
    logger.info("API: Fetching pending intake %s", brief_id)
    intake = orchestrator.get_pending_intake_by_id(brief_id)
    if not intake:
        logger.warning("API: Intake %s not found", brief_id)
        raise HTTPException(status_code=404, detail="Intake not found")
    logger.info("API: Intake %s retrieved successfully", brief_id)
    return intake


# POST /briefs/{brief_id}/approve — Approve it
@app.post("/briefs/{brief_id}/approve")
def approve_brief(brief_id: str):
    """Approve a pending intake, move to approved_intakes."""
    logger.info("API: Processing approval for intake %s", brief_id)
    try:
        orchestrator.approve_intake(brief_id)
        logger.info("API: Intake %s approved successfully", brief_id)
        return {"status": "approved", "id": brief_id}
    except ValueError as e:
        logger.warning("API: Approval failed for intake %s: %s", brief_id, e)
        raise HTTPException(status_code=400, detail=str(e))


# POST /briefs/{brief_id}/mark-issues — Flag problems
@app.post("/briefs/{brief_id}/mark-issues")
def flag_issues(brief_id: str, payload: Union[MarkIssuesRequest, list[str]] = Body(...)):
    """Mark issues with a pending intake, flag for review."""
    issues = payload.issues if isinstance(payload, MarkIssuesRequest) else payload
    logger.info("API: Flagging %d issue(s) for intake %s", len(issues), brief_id)
    try:
        orchestrator.mark_issues(brief_id, issues)
        logger.info("API: Issues flagged successfully for intake %s", brief_id)
        return {"status": "flagged", "id": brief_id}
    except ValueError as e:
        logger.warning("API: Failed to flag issues for intake %s: %s", brief_id, e)
        raise HTTPException(status_code=400, detail=str(e))


# Mount frontend static files for direct browser access
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/frontend", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")