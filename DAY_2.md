# Day 2: Design the System and Ship v0

## Candidate/Project Intake Pipeline

### Objective

Translate the Day 1 workflow into a working system design and ship the first end-to-end happy path.

The v0 should take one messy project brief, extract and standardize the important information, recommend the most appropriate team, generate an initial delivery checklist, and present the result for human approval.

The system **does not automatically assign work to a team** in v0.

---

# 1. v0 Scope

### Input

A project request submitted as:

* Plain text
* Email-like text
* Form submission

The initial v0 will use a simple text input interface.

Example:

> We need a web platform for a property company. Users should be able to browse houses, filter by location and price, and contact agents. They also want an admin dashboard where staff can add and update listings. We already have a designer but need development. Ideally React on the frontend and something Python based on the backend. Need an MVP in around 6 weeks.

### Output

The system produces a standardized project intake:

1. Project summary
2. Business objective
3. Functional requirements
4. Technical requirements
5. Constraints
6. Timeline
7. Missing information
8. Recommended team
9. Recommendation reasoning
10. Initial delivery checklist
11. Confidence / review flags

A human reviews the output before it becomes a finalized intake.

---

# 2. End-to-End Architecture

```text
                    ┌─────────────────────┐
                    │   User / Requester  │
                    └──────────┬──────────┘
                               │
                               │ Messy project brief
                               ▼
                    ┌─────────────────────┐
                    │   Intake Interface  │
                    │   CLI / Web Form    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    Input Parser     │
                    │ normalize raw text  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   LLM Extraction    │
                    │ Structured output   │
                    └──────────┬──────────┘
                               │
                               ▼
              ┌──────────────────────────────────┐
              │      Requirement Validator       │
              │ schema + missing-field checks    │
              └───────────────┬──────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │  Team Recommendation│
                    │ rules + LLM context │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Checklist Generator │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Human Review      │
                    │ approve / edit      │
                    └──────────┬──────────┘
                               │
                         Approved?
                         /       \
                       No         Yes
                       │           │
                       ▼           ▼
                  Revise      Store Intake
                                  │
                                  ▼
                         ┌─────────────────┐
                         │ SQLite / JSON   │
                         └─────────────────┘
```

---

# 3. Technology Choices

## Backend: FastAPI

### WhyWhy

FastAPI provides:

* Simple HTTP API
* Pydantic validation
* Automatic API documentation
* Easy local development
* Python ecosystem compatibility
* Straightforward integration with LLMs

The API becomes the central orchestration layer rather than putting business logic directly inside the interface.

---

## LLM: Local model through Ollama

The v0 should use a local LLM through Ollama where practical.

### Why

* No API cost during development
* Easy experimentation
* Keeps project briefs local
* Allows the pipeline to be tested repeatedly
* Provider can be replaced later

The application should keep the LLM behind a small abstraction:

```text
LLMProvider
    ├── OllamaProvider
    └── Future cloud provider
```

The rest of the application should not depend directly on Ollama.

---

## Validation: Pydantic

Pydantic models will define the data contracts.

The LLM should not be trusted to produce arbitrary JSON.

Flow:

```text
LLM output
    ↓
Pydantic validation
    ↓
Valid structured object
```

If validation fails, the system should retry once with a correction prompt.

If it still fails, the request goes to human review instead of silently producing bad data.

---

## Storage: SQLite

SQLite is sufficient for v0.

### Why

The goal is to prove the workflow, not build distributed infrastructure.

SQLite provides:

* Persistent storage
* Zero infrastructure
* Easy local setup
* Simple querying
* Easy migration to PostgreSQL later

Possible future architecture:

```text
v0: SQLite
      ↓
production: PostgreSQL
```

---

## Interface: Simple Web UI

The first interface should expose only the workflow needed to test the system.

```text
┌──────────────────────────────────────────┐
│ Candidate / Project Intake               │
├──────────────────────────────────────────┤
│                                          │
│ Paste project request                    │
│ ┌──────────────────────────────────────┐ │
│ │                                      │ │
│ │  Client's messy project brief...     │ │
│ │                                      │ │
│ └──────────────────────────────────────┘ │
│                                          │
│              [ Process Request ]         │
└──────────────────────────────────────────┘
```

After processing:

```text
┌──────────────────────────────────────────┐
│ Standardized Project Intake              │
├──────────────────────────────────────────┤
│ Project: Property Listing Platform       │
│                                          │
│ Recommended Team: Web Development        │
│ Confidence: High                         │
│                                          │
│ Requirements                             │
│ ✓ Property listings                      │
│ ✓ Search and filtering                   │
│ ✓ Agent contact                          │
│ ✓ Admin dashboard                        │
│                                          │
│ Missing Information                     │
│ • Authentication requirements             │
│ • Hosting preference                     │
│ • Exact MVP acceptance criteria          │
│                                          │
│ Initial Checklist                        │
│ □ Confirm requirements                   │
│ □ Define technical architecture          │
│ □ Design database                        │
│ □ Build API                              │
│ □ Build frontend                         │
│                                          │
│ [ Approve ] [ Edit ] [ Reject ]          │
└──────────────────────────────────────────┘
```

---

# 4. Data Contracts

## 4.1 Raw Intake

```json
{
  "request_id": "REQ-0001",
  "source": "web_form",
  "raw_text": "We need a web platform for a property company...",
  "submitted_at": "2026-09-14T12:00:00Z"
}
```

---

# 4.2 Extracted Project

```json
{
  "project_name": "Property Listing Platform",
  "summary": "Web platform for browsing and managing property listings.",
  "business_objective": "Allow customers to discover properties and contact agents while enabling staff to manage listings.",
  "requirements": [
    {
      "description": "Browse property listings",
      "priority": "high"
    },
    {
      "description": "Filter properties by location and price",
      "priority": "high"
    },
    {
      "description": "Contact property agents",
      "priority": "high"
    },
    {
      "description": "Admin dashboard for managing listings",
      "priority": "high"
    }
  ],
  "technical_requirements": [
    "React frontend",
    "Python backend"
  ],
  "constraints": [
    "MVP target of approximately 6 weeks"
  ],
  "existing_resources": [
    "Designer available"
  ],
  "missing_information": [
    "Authentication requirements",
    "Hosting requirements",
    "MVP acceptance criteria"
  ]
}
```

---

# 4.3 Team Recommendation

The recommendation is advisory, not an automatic assignment.

```json
{
  "recommended_team": "Web Development",
  "confidence": 0.91,
  "reasoning": [
    "Primary deliverable is a web application",
    "Requirements include frontend and backend development",
    "Existing designer reduces design workload"
  ],
  "alternative_team": null,
  "requires_human_review": false
}
```

The system should eventually support several team categories, for example:

```text
Web Development
Mobile Development
AI / ML
Data Engineering
Automation
Design
DevOps / Infrastructure
Mixed / Cross-functional
```

For v0, the recommendation logic can remain deliberately small.

---

# 4.4 Delivery Checklist

```json
{
  "checklist": [
    {
      "task": "Confirm project requirements",
      "priority": "high"
    },
    {
      "task": "Define technical architecture",
      "priority": "high"
    },
    {
      "task": "Design database schema",
      "priority": "medium"
    },
    {
      "task": "Implement backend API",
      "priority": "high"
    },
    {
      "task": "Implement frontend",
      "priority": "high"
    },
    {
      "task": "Implement admin dashboard",
      "priority": "medium"
    },
    {
      "task": "QA and acceptance testing",
      "priority": "high"
    }
  ]
}
```

---

# 5. Complete Intake Contract

The final object stored by the system should look approximately like:

```json
{
  "request_id": "REQ-0001",

  "raw_request": "...",

  "project": {
    "name": "Property Listing Platform",
    "summary": "...",
    "business_objective": "...",
    "requirements": [],
    "technical_requirements": [],
    "constraints": [],
    "existing_resources": [],
    "missing_information": []
  },

  "team_recommendation": {
    "team": "Web Development",
    "confidence": 0.91,
    "reasoning": []
  },

  "checklist": [],

  "review": {
    "status": "pending",
    "reviewer": null,
    "review_notes": null
  }
}
```

This becomes the main data contract between pipeline stages.

---

# 6. Pipeline Responsibilities

Each stage has one clear responsibility.

## Stage 1 — Intake

### Input

Raw user request.

### Output

`RawIntake`

No interpretation should happen here.

---

## Stage 2 — Extraction

### Input

Raw text.

### Output

Structured project information.

The model extracts facts that are present in the request.

It should **not invent missing requirements**.

Unknown information should be represented as:

```text
missing_information
```

rather than hallucinated values.

---

## Stage 3 — Validation

Validate:

* Required fields
* Data types
* Priority values
* Empty values
* Schema correctness

Invalid output triggers a retry or human review.

---

## Stage 4 — Team Recommendation

The recommendation uses:

```text
Project requirements
+
Technical requirements
+
Project type
+
Constraints
```

The result is:

```text
Recommended team
+
Confidence
+
Reasoning
```

It does not create an assignment.

---

## Stage 5 — Checklist Generation

Generate an initial delivery checklist based on the standardized requirements.

The checklist is a starting point, not a project plan.

---

## Stage 6 — Human Review

The reviewer can:

* Approve
* Edit
* Reject
* Correct team recommendation
* Add missing requirements
* Modify checklist items

Only after approval is the intake considered finalized.

---

# 7. Human Approval Points

Human review is intentionally placed after AI processing.

```text
AI extraction
      ↓
AI recommendation
      ↓
AI checklist
      ↓
┌───────────────────┐
│ HUMAN REVIEW      │
│                   │
│ Approve / Edit    │
│ Reject            │
└─────────┬─────────┘
          ↓
       Finalize
```

### Human approval is required when:

* Confidence is below threshold
* Required information is missing
* Multiple teams are equally plausible
* LLM output fails validation
* Sensitive information is detected
* The recommendation conflicts with explicit requester requirements

---

# 8. Fallback Strategy

The system should fail safely rather than pretending to understand everything.

## LLM unavailable

Return:

```text
Processing unavailable.
Please review this request manually.
```

The raw request is still preserved.

---

## Invalid structured output

```text
LLM
 ↓
Pydantic validation
 ↓
FAIL
 ↓
Retry once
 ↓
FAIL
 ↓
Human review
```

---

## Low-confidence recommendation

Do not force a team.

Return:

```text
Recommended team:
Needs human review

Possible teams:
- Web Development
- AI / ML
```

---

## Missing requirements

Do not manufacture them.

Example:

```text
Missing:
- Authentication requirements
- Hosting preference
- Expected user volume
```

---

# 9. Privacy Boundaries

The v0 should follow a minimum-data principle.

### Store

* Request ID
* Project information
* Requirements
* Recommendation
* Review status
* Checklist

### Avoid storing unnecessarily

* Personal conversations
* Passwords
* API keys
* Authentication tokens
* Unrelated personal information

Raw input should only be retained because it is useful for traceability and review.

For local development, project data remains on the local machine when using the local LLM.

---

# 10. Permission Boundaries

The AI system should be advisory.

### AI can

* Read submitted project information
* Extract requirements
* Normalize information
* Recommend a team
* Generate a checklist
* Flag missing information

### AI cannot

* Automatically assign employees
* Send external emails
* Commit resources
* Change project status without approval
* Approve its own recommendation
* Access unrelated company data

This keeps the v0 useful without giving an LLM the keys to the kingdom, which history suggests is a surprisingly bad architecture.

---

# 11. Evaluation Rubric

The system should be evaluated on five dimensions.

| Category                 |   Weight |
| ------------------------ | -------: |
| Extraction accuracy      |      25% |
| Requirement completeness |      20% |
| Team recommendation      |      20% |
| Checklist usefulness     |      15% |
| Safety / reliability     |      20% |
| **Total**                | **100%** |

---

## 11.1 Extraction Accuracy — 25%

### Pass

At least 90% of explicitly stated important facts are correctly extracted.

### Fail

Important facts are:

* Missing
* Contradicted
* Invented

---

## 11.2 Requirement Completeness — 20%

### Pass

The system identifies:

* Explicit requirements
* Constraints
* Existing resources
* Important missing information

### Fail

The system fills unknown information with assumptions.

---

## 11.3 Team Recommendation — 20%

### Pass

Recommended team is reasonable based on the extracted requirements.

The explanation must reference actual project information.

### Fail

The recommendation is arbitrary or unsupported.

---

## 11.4 Checklist Quality — 15%

### Pass

Checklist contains actionable tasks directly related to the project.

### Fail

Checklist contains generic filler such as:

```text
Start project
Build application
Test application
Deploy application
```

without project-specific actions.

---

## 11.5 Safety / Reliability — 20%

### Pass

System:

* Validates output
* Identifies uncertainty
* Does not hallucinate missing requirements
* Does not automatically assign teams
* Preserves human approval
* Handles LLM failures

### Fail

System confidently produces unsupported information or takes unauthorized actions.

---

# 12. Overall Pass/Fail Criteria

The Day 2 v0 passes if one real project request can successfully complete:

```text
Input
 ↓
Extraction
 ↓
Validation
 ↓
Team recommendation
 ↓
Checklist
 ↓
Human review
 ↓
Stored final intake
```

### Minimum acceptance criteria

* [ ] One real input processed end-to-end
* [ ] Structured output passes schema validation
* [ ] Explicit requirements are preserved
* [ ] Missing information is identified
* [ ] Team is recommended rather than automatically assigned
* [ ] Recommendation includes reasoning
* [ ] Checklist is project-specific
* [ ] Human approval exists
* [ ] Final result is stored
* [ ] Failure path exists for invalid LLM output
* [ ] No unsupported facts are silently invented

---

# 13. v0 Project Structure

```text
project-intake-pipeline/
│
├── app/
│   ├── main.py
│   │
│   ├── models/
│   │   ├── intake.py
│   │   ├── project.py
│   │   └── recommendation.py
│   │
│   ├── services/
│   │   ├── parser.py
│   │   ├── extractor.py
│   │   ├── recommender.py
│   │   ├── checklist.py
│   │   └── validator.py
│   │
│   ├── providers/
│   │   └── llm.py
│   │
│   ├── storage/
│   │   └── database.py
│   │
│   └── prompts/
│       ├── extraction.txt
│       ├── recommendation.txt
│       └── checklist.txt
│
├── tests/
│   ├── test_extraction.py
│   ├── test_recommendation.py
│   └── test_pipeline.py
│
├── data/
│   └── intake.db
│
├── .env.example
├── requirements.txt
└── README.md
```

---

# 14. v0 API

The initial API can remain extremely small.

## Process request

```http
POST /intake
```

### Request

```json
{
  "raw_text": "We need a web platform for a property company..."
}
```

### Response

```json
{
  "request_id": "REQ-0001",
  "status": "pending_review",
  "project": {},
  "team_recommendation": {},
  "checklist": []
}
```

---

## Approve intake

```http
POST /intake/{request_id}/approve
```

This changes:

```text
pending_review
```

to:

```text
approved
```

---

## Get intake

```http
GET /intake/{request_id}
```

Returns the complete standardized intake.

---

# 15. First Happy Path

The first v0 test will use this representative request:

```text
We need a web platform for a property company. Users should be able
to browse houses, filter by location and price, and contact agents.
We also want an admin dashboard where staff can add and update
listings. We already have a designer but need development.

Ideally use React for the frontend and something Python based for
the backend. We want an MVP in around 6 weeks.
```

Expected processing:

```text
RAW REQUEST
    ↓
Property web platform
    ↓
Requirements extracted
    ↓
React + Python identified
    ↓
6-week constraint identified
    ↓
Existing designer identified
    ↓
Missing information identified
    ↓
Web Development recommended
    ↓
Project-specific checklist generated
    ↓
Human review
    ↓
Approved intake stored
```

---

# 16. Example Final Result

```text
PROJECT
Property Listing Platform

SUMMARY
Web platform for browsing and managing property listings.

BUSINESS OBJECTIVE
Enable customers to discover properties and contact agents while
allowing internal staff to manage listings.

RECOMMENDED TEAM
Web Development

CONFIDENCE
High

WHY
- Primary product is a web application
- Requires frontend and backend development
- React and Python are explicitly requested
- Designer is already available

KNOWN REQUIREMENTS
✓ Property browsing
✓ Location filtering
✓ Price filtering
✓ Agent contact
✓ Admin listing management
✓ React frontend
✓ Python backend
✓ Approximately 6-week MVP target

MISSING INFORMATION
⚠ Authentication requirements
⚠ Hosting requirements
⚠ Expected number of users
⚠ MVP acceptance criteria

INITIAL CHECKLIST
□ Confirm functional requirements
□ Define application architecture
□ Define database schema
□ Implement property API
□ Implement property browsing UI
□ Implement filtering
□ Implement agent contact flow
□ Implement admin dashboard
□ QA against acceptance criteria

STATUS
Pending human approval
```

---

# 17. Day 2 Definition of Done

Day 2 is complete when the repository contains:

```text
✓ Architecture
✓ Data contracts
✓ Pydantic schemas
✓ LLM provider abstraction
✓ Extraction pipeline
✓ Team recommendation
✓ Checklist generation
✓ Validation
✓ Human review state
✓ SQLite persistence
✓ Minimal interface/API
✓ One end-to-end successful run
✓ Evaluation criteria
✓ Failure/fallback handling
```

The objective is **not** to build every possible feature.

The objective is to prove:

> A messy project request can enter the system and become a structured, reviewable project intake that a human can approve.

That is the first meaningful proof that the AI OS workflow actually works.
