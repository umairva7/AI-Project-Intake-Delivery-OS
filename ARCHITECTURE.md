# Project Intake Pipeline — System Architecture

**Author:** You (owner of decisions)  
**Last Updated:** Day 1  
**Status:** Design phase (before implementation)

---

## 1. System Boundaries

### What This System Does

```
Raw project brief (unstructured text)
    ↓
Extracts structured requirements
    ↓
Identifies missing information
    ↓
Recommends team
    ↓
Generates initial checklist
    ↓
Stores approved intake
```

### What This System Does NOT Do (v0 scope out)

- Email ingestion
- Slack integration
- Historical learning from past projects
- Batch processing (one brief at a time)
- Role-based access control
- Multi-user collaboration
- CRM/project management integration
- Multi-file format handling

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Web Browser                           │
│                (Non-developer user)                      │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
        ┌────────────────────────────┐
        │    FastAPI Web Server      │
        │  (Python, async routes)    │
        └────────────┬───────────────┘
                     │
        ┌────────────┴────────────┐
        ↓                         ↓
   ┌─────────────┐         ┌──────────────┐
   │  Form Route │         │  API Routes  │
   │(GET/POST)   │         │              │
   └──────┬──────┘         └──────┬───────┘
          │                       │
          └───────────┬───────────┘
                      ↓
           ┌──────────────────────┐
           │ Intake Orchestrator  │
           │ (Controller/Service) │
           └─────────┬────────────┘
                     │
        ┌────────────┼────────────┐
        ↓            ↓            ↓
   ┌─────────┐ ┌──────────┐ ┌─────────┐
   │ Ollama  │ │ Pydantic │ │ SQLite  │
   │  LLM    │ │ Models   │ │  DB     │
   │         │ │(Validate)│ │         │
   └─────────┘ └──────────┘ └─────────┘
```

---

## 3. Core Components

### 3.1 Web Interface (FastAPI)

**Responsibility:** Accept user input, display results, handle approvals

**Routes:**
```
GET  /                      → Form page
POST /api/process           → Submit brief + get extracted intake
POST /api/approve           → User marks issues or approves
GET  /api/intake/<id>       → Retrieve stored intake
```

**Data received from user:**
```json
{
  "brief_text": "...",
  "source": "form"
}
```

**Data sent to user:**
```json
{
  "request_id": "REQ-0001",
  "status": "pending_review",
  "extracted": {
    "project_name": "...",
    "requirements": [...],
    "missing_info": [...],
    "team_recommendation": "Web Development",
    "confidence": 0.92
  },
  "issues_detected": [
    "Confidence below threshold",
    "Ambiguous timeline"
  ]
}
```

---

### 3.2 Intake Orchestrator (Service Layer)

**Responsibility:** Coordinate the entire workflow. You will write this.

**Pseudocode:**
```python
class IntakeOrchestrator:
    
    def process_brief(raw_text: str) -> IntakeResult:
        """
        Main workflow: extract, validate, recommend, generate checklist.
        """
        # 1. Store raw request
        request = create_request(raw_text)
        
        # 2. Extract with LLM
        extraction = extract_requirements(raw_text)
        if not extraction.valid:
            if retry_count < 1:
                retry extraction with correction prompt
            else:
                flag for manual review
                return early
        
        # 3. Detect hallucinations / low confidence
        if extraction.confidence < 0.7:
            flag for human review
        
        # 4. Get team recommendation
        team = recommend_team(extraction.requirements)
        
        # 5. Generate checklist
        checklist = generate_checklist(extraction.requirements, team)
        
        # 6. Prepare for review
        return IntakeResult(
            extracted=extraction,
            team=team,
            checklist=checklist,
            status="pending_review"
        )
    
    def approve_intake(request_id: str, issues: List[str]) -> ApprovedIntake:
        """
        User marks issues or approves. Store in database.
        """
        intake = get_pending_intake(request_id)
        
        if issues:
            # User marked problems
            intake.status = "issues_marked"
            intake.issues = issues
        else:
            # User approved
            intake.status = "approved"
            intake.approved_at = now()
        
        store_in_database(intake)
        return intake
```

---

### 3.3 Ollama Integration (LLM Provider)

**Responsibility:** Call Ollama, handle timeouts, parse JSON output

**Failure scenarios you MUST handle:**

```
Scenario 1: Invalid JSON
→ Retry once with: "Return valid JSON"
→ Still invalid? Flag for manual review

Scenario 2: Missing required fields (e.g., no "requirements" key)
→ Pydantic validation catches this
→ Mark as incomplete, flag for review

Scenario 3: Hallucinated requirements
→ Can't detect automatically
→ Confidence score + user review catches this

Scenario 4: Timeout (no response in 30 seconds)
→ Catch connection error
→ Show user: "AI system is slow. Please try again."

Scenario 5: Ollama offline
→ Catch connection refused
→ Show user: "AI system unavailable. Please ensure Ollama is running."
```

**Interface:**
```python
class OllamaProvider:
    
    def extract_requirements(brief: str, retry_count: int = 0) -> ExtractionResult:
        """
        Call Ollama. Return structured JSON.
        Retry once if invalid. Escalate on repeated failure.
        """
        try:
            response = call_ollama_with_extraction_prompt(brief)
            extraction = parse_json(response)
            validate_with_pydantic(extraction)  # Raises on missing fields
            return extraction
        except JSONDecodeError:
            if retry_count < 1:
                return extract_requirements(brief, retry_count + 1)
            else:
                return ExtractionResult(
                    valid=False,
                    error="LLM returned invalid JSON twice",
                    requires_manual_review=True
                )
        except ValidationError as e:
            return ExtractionResult(
                valid=False,
                error=f"Missing fields: {e.errors()}",
                requires_manual_review=True
            )
        except TimeoutError:
            return ExtractionResult(
                valid=False,
                error="LLM timeout",
                requires_manual_review=True
            )
```

---

### 3.4 Data Models (Pydantic)

**Responsibility:** Validate structure, catch type errors

You will define these schemas. See `DATA_MODELS.md`.

```python
class Requirement(BaseModel):
    description: str
    priority: Literal["high", "medium", "low"]
    confirmed: bool  # Is this explicitly stated or inferred?

class ProjectExtraction(BaseModel):
    project_name: str
    summary: str
    requirements: List[Requirement]
    missing_information: List[str]
    scope_constraints: List[str]
    confidence: float  # 0.0 to 1.0

class ProjectIntake(BaseModel):
    request_id: str
    raw_brief: str
    extracted: ProjectExtraction
    team_recommendation: str
    team_confidence: float
    checklist: List[str]
    status: Literal["draft", "pending_review", "approved", "rejected"]
    created_at: datetime
```

---

### 3.5 SQLite Database

**Responsibility:** Persist requests and approved intakes

**Tables:**

```sql
-- Raw requests (for audit trail)
CREATE TABLE requests (
    id TEXT PRIMARY KEY,
    raw_text TEXT,
    source TEXT,  -- "form", "api", etc.
    created_at TIMESTAMP,
    status TEXT  -- "processing", "pending_review", "approved", etc.
);

-- Extracted intakes (for analysis + review)
CREATE TABLE intakes (
    id TEXT PRIMARY KEY,
    request_id TEXT FOREIGN KEY,
    extracted_json TEXT,  -- Full JSON blob
    team_recommendation TEXT,
    status TEXT,
    issues_marked TEXT,  -- JSON list of issues user flagged
    approved_at TIMESTAMP,
    created_at TIMESTAMP
);

-- Approved intakes (final record)
CREATE TABLE approved_intakes (
    id TEXT PRIMARY KEY,
    intake_id TEXT FOREIGN KEY,
    final_data JSON,
    approved_by TEXT,  -- For now, always system
    approved_at TIMESTAMP
);
```

---

## 4. Error Handling Strategy

### Type 1: LLM Failures (Recoverable)

```
Invalid JSON → Retry once
Still invalid → Flag for review, show user message

Missing required fields → Flag for review
Timeout → Catch, show message, retry on next attempt
Offline → Show helpful message with troubleshooting
```

### Type 2: Validation Failures (Escalate)

```
Pydantic validation fails → Mark for manual review
Confidence < 0.7 → Flag for human approval
Hallucination detected → User sees flagged requirements for review
```

### Type 3: User Failures (Graceful)

```
Empty input → Show helpful message
Malformed input → Treat as vague, escalate
Sensitive data in input → Flag for security, don't log
```

---

## 5. Data Flow (End-to-End Example)

**Input:**
```
"We need a React frontend with Python backend for an employee 
dashboard. Timeline: 6 weeks. Budget: $50,000."
```

**Step 1: Create Request**
```
request_id: REQ-0001
raw_text: "We need a React frontend..."
status: "processing"
```

**Step 2: Call Ollama**
```
Ollama returns:
{
  "project_name": "Employee Dashboard",
  "summary": "Internal tool for tracking employee projects...",
  "requirements": [
    {"description": "React frontend", "priority": "high", "confirmed": true},
    ...
  ],
  "missing_information": [
    "Number of expected users",
    "Hosting requirements"
  ],
  "confidence": 0.92
}
```

**Step 3: Validate**
```
Pydantic: ✓ Valid structure
Confidence: ✓ 0.92 > 0.7
Hallucination check: ✓ All requirements are stated in input
```

**Step 4: Get Team Recommendation**
```
Team: "Web Development"
Confidence: 0.95
Reasoning: React + Python API detected
```

**Step 5: Generate Checklist**
```
[ ] Confirm user base size
[ ] Determine hosting environment
[ ] Set up React project structure
[ ] Create Python API skeleton
[ ] Connect to existing data source
[ ] Set up authentication
```

**Step 6: Store**
```
INSERT INTO intakes VALUES (
  id: "INT-0001",
  request_id: "REQ-0001",
  extracted_json: {...},
  team_recommendation: "Web Development",
  status: "pending_review"
)
```

**Step 7: Show User**
```
EXTRACTED REQUIREMENTS
✓ React frontend
✓ Python backend
✓ Employee dashboard

RECOMMENDED TEAM
Web Development (confidence: 95%)

MISSING INFORMATION
⚠ Number of expected users
⚠ Hosting requirements

CHECKLIST
□ Confirm user base size
□ Determine hosting environment
...

Issues detected?
[ ] Yes, there are problems
[ ] No, looks good - approve
```

**Step 8: User Approves**
```
INSERT INTO approved_intakes VALUES (
  id: "APPROVED-0001",
  intake_id: "INT-0001",
  final_data: {...},
  approved_at: NOW()
)
```

---

## 6. Technology Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend | HTML + Jinja2 templates | Simple, no build step, works with FastAPI |
| Backend | FastAPI (Python) | Async, fast, easy to test |
| LLM | Ollama + local model | Free, offline, good enough for MVP |
| Validation | Pydantic | Type safety, clear errors |
| Storage | SQLite | Persistent, queryable, no server |
| Testing | pytest | Standard, integrated |

---

## 7. Dependencies

```
fastapi            # Web framework
uvicorn            # ASGI server
pydantic           # Data validation
requests           # HTTP calls to Ollama
sqlalchemy         # Database ORM (optional, can use raw SQL)
jinja2             # Template rendering
pytest             # Testing
```

---

## 8. Environment Configuration

```bash
# .env (not checked in)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral  # or your chosen model
DATABASE_URL=sqlite:///./data/intake.db
LOG_LEVEL=INFO
CONFIDENCE_THRESHOLD=0.7  # Flag for review if below this
RETRY_COUNT=1  # Retry LLM calls this many times on failure
```

---

## 9. Logging & Observability

Every major step should log:

```python
logger.info(f"Request created: {request_id}")
logger.info(f"LLM extraction started: {request_id}")
logger.info(f"LLM extraction completed: {request_id}, confidence={confidence}")
logger.warning(f"Low confidence extraction: {request_id}, confidence={confidence}")
logger.error(f"LLM extraction failed: {request_id}, error={error}")
```

Do **NOT** log:
- Sensitive data (passwords, API keys, PII)
- Full raw briefs (too verbose)
- User input that might be adversarial

---

## 10. What You (The Developer) Will Write

You own these decisions and implementations:

- [x] Architecture (this doc)
- [ ] FastAPI routes (who? what? where? why?)
- [ ] Orchestrator class (workflow logic)
- [ ] Error handling (each scenario)
- [ ] Logging (what to capture)
- [ ] Database schema (storage)
- [ ] Pydantic models (data contracts)

You can ask Antigravity for help on:
- "Generate the Pydantic schema for ProjectExtraction"
- "Write the SQLite schema for requests and intakes"
- "Generate the Ollama extraction prompt"

But YOU integrate it. YOU make decisions about flow. YOU understand it.

---

## 11. Decision Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| LLM | Ollama local | Free, offline, MVP scope |
| Output format | Structured JSON | Avoid user confusion, enable validation |
| Failure handling | Retry once → escalate | Balance reliability with speed |
| Human approval | Option B (mark issues) | Simpler UX, clearer decision flow |
| Storage | SQLite | Persistent, good for v0 |
| Interface | Web form | Non-developer friendly |
| Error messages | User-friendly text | No Python stack traces shown |
| Scope boundaries | No email/Slack/learning | Deliverable in 5 days |

---

## 12. What Success Looks Like

Day 2 end: This architecture document exists, you understand every line, you could explain it to someone else.

Day 3 end: You've implemented this architecture. The orchestrator works end-to-end.

Day 4 end: Failures are handled, metrics are measured, quality is known.

Day 5 end: Another person can read this doc + your code and understand what you built.