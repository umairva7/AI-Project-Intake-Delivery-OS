# Day 3: Build the Working Core

## Candidate/Project Intake Pipeline

### Objective

Complete the end-to-end workflow so that a non-developer can submit a messy project request and receive a structured, reviewable project intake.

The system should be usable without the developer manually modifying code or running individual pipeline steps.

### Key Question

> **Can someone else run the core workflow when I am not beside them?**

---

# 1. Day 3 Scope

Day 3 takes the v0 from Day 2 and turns it into a usable application.

The target workflow is:

```text
Project Request
      ↓
Submit
      ↓
Extract Requirements
      ↓
Validate Structured Data
      ↓
Identify Missing Information
      ↓
Recommend Team
      ↓
Generate Checklist
      ↓
Human Review
      ↓
Approve / Edit / Reject
      ↓
Store Final Intake
```

The system should work from beginning to end without requiring manual intervention from the developer.

---

# 2. Target User

The target user is a non-developer project coordinator, recruiter, account manager, or delivery manager.

They should not need to understand:

* Python
* FastAPI
* Ollama
* Pydantic
* JSON
* Prompt engineering
* Database operations

They should only need to:

1. Open the application
2. Paste or submit a project request
3. Review the generated intake
4. Approve or edit it

---

# 3. Core Workflow

## Step 1 — Submit Request

The user enters a project brief.

Example:

```text
We need an AI-powered customer support chatbot for our e-commerce
business. It should answer questions about orders and products,
connect to our existing knowledge base, and escalate difficult
questions to human support agents.

We already have a website and product database. We want an MVP
within 4 weeks.
```

---

## Step 2 — Parse Input

The system creates a request record.

```json
{
  "request_id": "REQ-0002",
  "source": "web_form",
  "raw_text": "...",
  "status": "processing"
}
```

---

## Step 3 — Extract Information

The LLM converts the unstructured request into the defined project schema.

The system should extract:

* Project name
* Summary
* Business objective
* Functional requirements
* Technical requirements
* Constraints
* Existing resources
* Missing information

---

## Step 4 — Validate

The structured response is validated against the Pydantic schema.

```text
LLM
 ↓
Structured output
 ↓
Pydantic
 ↓
VALID
```

If invalid:

```text
LLM
 ↓
Invalid output
 ↓
Retry
 ↓
Validation
```

If still invalid:

```text
Human review required
```

---

# 4. Tool / Data Integrations

Day 3 requires at least two meaningful integrations.

## Integration 1 — Ollama

Purpose:

```text
Generate structured project information
Generate team recommendation
Generate checklist
```

The application communicates with the local LLM through the provider abstraction.

---

## Integration 2 — SQLite

Purpose:

```text
Store requests
Store extracted projects
Store recommendations
Store review status
Store final approved intake
```

This gives the system persistence across executions.

---

## Optional Integration 3 — File Input

Support `.txt` or `.md` project briefs.

Example:

```text
Upload project brief
       ↓
Read file
       ↓
Same processing pipeline
```

This demonstrates that the pipeline is not tied exclusively to a text box.

---

# 5. Interface

Use a simple web interface.

The interface should contain three primary states.

## State 1 — New Request

```text
┌─────────────────────────────────────────────┐
│ Project Intake                              │
├─────────────────────────────────────────────┤
│                                             │
│ Project request                             │
│                                             │
│ ┌─────────────────────────────────────────┐ │
│ │ Paste client/project request here...    │ │
│ │                                         │ │
│ │                                         │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│              [ Process Request ]            │
└─────────────────────────────────────────────┘
```

---

## State 2 — Processing

Display:

```text
Processing request...

✓ Request received
✓ Requirements extracted
✓ Output validated
✓ Team recommendation generated
✓ Checklist generated

Preparing review...
```

The user should not see raw technical errors.

---

## State 3 — Review

Display:

```text
PROJECT
AI Customer Support Assistant

SUMMARY
AI assistant for answering customer questions...

RECOMMENDED TEAM
AI / ML

CONFIDENCE
High

REQUIREMENTS
✓ Product question answering
✓ Order-related questions
✓ Knowledge-base integration
✓ Human escalation

MISSING INFORMATION
⚠ Expected monthly conversation volume
⚠ Existing knowledge-base format
⚠ Escalation workflow

CHECKLIST
□ Confirm knowledge sources
□ Define retrieval architecture
□ Connect product database
□ Implement chatbot
□ Implement escalation flow
□ Test response quality

[ Edit ] [ Approve ] [ Reject ]
```

---

# 6. Approval Workflow

The AI never approves its own output.

Possible states:

```text
draft
  ↓
processing
  ↓
pending_review
  ↓
approved
```

Alternative:

```text
pending_review
      ↓
    edited
      ↓
pending_review
```

Or:

```text
pending_review
      ↓
   rejected
```

---

# 7. Logging

Every execution should produce useful logs.

Example:

```text
2026-09-14 14:32:01 INFO  Request received REQ-0002
2026-09-14 14:32:02 INFO  Starting extraction
2026-09-14 14:32:08 INFO  Extraction completed
2026-09-14 14:32:08 INFO  Validating structured output
2026-09-14 14:32:08 INFO  Validation successful
2026-09-14 14:32:09 INFO  Generating team recommendation
2026-09-14 14:32:10 INFO  Recommendation generated
2026-09-14 14:32:11 INFO  Generating checklist
2026-09-14 14:32:12 INFO  Intake ready for review
```

Do not log:

* API keys
* Passwords
* Authentication tokens
* Sensitive raw data unnecessarily

---

# 8. Error Messages

Errors should be understandable to the target user.

### Bad

```text
ValidationError: 3 validation errors for ProjectIntake...
```

### Better

```text
We could not confidently structure this request.

The request has been saved and requires manual review.
```

Technical details should remain in developer logs.

---

# 9. Configuration

Configuration must not be hardcoded.

Example:

```text
.env

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=<model>
DATABASE_URL=sqlite:///./data/intake.db
LOG_LEVEL=INFO
```

The repository should contain:

```text
.env.example
```

but never the real `.env`.

---

# 10. Secrets

No secrets should appear in:

* Source code
* Git commits
* README
* Prompt files
* Logs
* Screenshots

If a cloud provider is tested later, credentials must come from environment variables or a secret manager.

---

# 11. Core Tests

Day 3 should include tests for:

### Valid request

```text
Input → successful intake
```

### Empty request

```text
Input → useful validation error
```

### Very short request

```text
"Build me an app"

→ Missing information
→ Human review
```

### Invalid LLM output

```text
Invalid JSON/schema
→ retry
→ fallback
```

### Approval

```text
pending_review
→ approve
→ approved
```

---

# 12. First Proxy User

The first proxy user should be someone who has not seen the internal implementation.

Give them only:

```text
1. Open the application.
2. Submit this project brief.
3. Review the result.
4. Approve or edit it.
```

Do not explain the internal architecture first.

Observe:

* Where they hesitate
* What they misunderstand
* Whether they know what to click
* Whether the generated output is understandable
* Whether they trust the recommendation

Record their feedback.

---

# 13. Day 3 Success Criteria

### Core

* [ ] User can submit a project request
* [ ] Request is persisted
* [ ] LLM extracts structured information
* [ ] Output is validated
* [ ] Team recommendation generated
* [ ] Checklist generated
* [ ] Human review available
* [ ] Approved intake stored

### Integrations

* [ ] Ollama integration works
* [ ] SQLite integration works

### Reliability

* [ ] Validation exists
* [ ] Retry exists
* [ ] Fallback exists
* [ ] Useful logs exist
* [ ] User-friendly errors exist

### Interface

* [ ] Non-developer can use the UI
* [ ] No code changes required
* [ ] No terminal commands required during normal usage

---

# 14. Day 3 Definition of Done

Day 3 is complete when another person can:

```text
Open application
      ↓
Paste project request
      ↓
Click Process
      ↓
Review AI-generated intake
      ↓
Edit if necessary
      ↓
Approve
      ↓
See confirmation
```

without the developer explaining what is happening behind the scenes.

The core workflow is now a **product**, not merely a collection of scripts.
