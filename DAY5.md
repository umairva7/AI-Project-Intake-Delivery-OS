# Day 5: Handoff, Prove Value, and Present

## Candidate/Project Intake Pipeline

### Objective

Package the system so another person can understand it, run it, operate it, evaluate it, and continue improving it without relying on the original developer.

The final deliverable should demonstrate not only that the system works, but that it is understandable and maintainable.

### Key Question

> **Can another person understand, run, trust, and improve the system?**

---

# 1. Final Deliverable

The final submission should contain:

```text
project-intake-pipeline/
│
├── application
├── tests
├── evaluation
├── documentation
├── sample-data
├── screenshots
├── demo
└── README.md
```

---

# 2. Repository README

The main README should answer:

1. What problem does this solve?
2. Who is it for?
3. How does it work?
4. What technologies are used?
5. How do I run it?
6. How was it evaluated?
7. Where does it fail?
8. What are the limitations?
9. What would be built next?

---

# 3. Three-Step Setup

The setup should be as short as realistically possible.

Example:

```text
1. Clone repository and install dependencies.

2. Start Ollama and pull the configured model.

3. Start the application and open the local web interface.
```

The exact commands should be documented and tested on a clean environment.

Do not write setup instructions that only work on the developer's machine.

---

# 4. User README

Create a separate document for the non-technical user.

Example:

```text
# Using Project Intake

## 1. Submit a Request

Paste the project request into the input box.

## 2. Process

Click "Process Request".

The system extracts the project information.

## 3. Review

Check:

- Requirements
- Missing information
- Team recommendation
- Checklist

## 4. Edit

Correct anything that is inaccurate.

## 5. Approve

Click "Approve" when the intake is correct.
```

Do not explain Python, APIs, databases, or LLM providers here.

The user documentation should explain the product, not the machinery.

---

# 5. Operator Runbook

The operator needs different information.

Document:

## Starting the application

```text
Start Ollama
Start application
Verify database
Open interface
```

---

## Checking logs

Explain:

* Where logs are located
* What normal execution looks like
* How errors appear

---

## Common failures

### Ollama unavailable

Symptom:

```text
LLM processing unavailable
```

Action:

```text
Check Ollama service
Check configured model
Retry request
```

---

### Database unavailable

Action:

```text
Check database path
Check permissions
Restart application
```

---

### Invalid model output

Action:

```text
Check logs
Retry request
If repeated, review manually
```

---

# 6. Architecture Documentation

Create a final architecture diagram.

```text
                    ┌──────────────────┐
                    │   Non-Developer  │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │     Web UI       │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │     FastAPI      │
                    │  Orchestration   │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌──────────┐  ┌────────────┐  ┌──────────┐
        │  Parser  │  │ LLM/Ollama │  │ Validator│
        └──────────┘  └────────────┘  └──────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ Recommendation   │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ Checklist        │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ Human Review     │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │     SQLite       │
                    └──────────────────┘
```

---

# 7. Data Flow Documentation

Document one complete request.

```text
Raw project brief
      ↓
RawIntake
      ↓
LLM extraction
      ↓
ProjectIntake
      ↓
Pydantic validation
      ↓
Team recommendation
      ↓
Checklist generation
      ↓
Human review
      ↓
ApprovedIntake
      ↓
SQLite
```

For every transition, document:

```text
Input
Output
Validation
Failure behavior
```

---

# 8. Evaluation Documentation

Publish the actual evaluation results.

Example:

```text
Evaluation Set: 20 cases

Extraction accuracy:       92%
Requirement recall:        88%
Hallucination rate:         3%
Team accuracy:             89%
Average latency:           11.4s
Human review rate:         25%
```

These numbers are examples only.

Replace them with actual measured results.

---

# 9. Limitations

Be explicit.

Possible limitations:

```text
- Recommendation quality depends on the clarity of the input.
- Very ambiguous requests require human review.
- Team taxonomy is intentionally small in v0.
- Local LLM performance depends on the selected model.
- Checklist generation is not equivalent to detailed project planning.
- SQLite is intended for v0 rather than high-concurrency production use.
```

A good engineering project does not pretend limitations don't exist.

---

# 10. Value Measurement

The system should demonstrate why it exists.

Compare:

## Before

Manual process:

```text
Read request
 ↓
Identify requirements
 ↓
Rewrite request
 ↓
Decide appropriate team
 ↓
Create checklist
```

Measure the average manual time.

Example:

```text
Manual intake: 20 minutes
```

---

## After

```text
Paste request
 ↓
Process
 ↓
Review
```

Measure:

```text
AI processing: 10 seconds
Human review: 4 minutes
```

The meaningful metric is therefore:

```text
Total human effort
```

rather than simply claiming:

> "The AI is 100x faster."

The human still needs to review the output. Civilization has not yet reached the stage where we can let the language model run the company unsupervised.

---

# 11. Adoption Metrics

For the first two weeks after deployment, track:

## Usage

```text
Requests submitted
Requests approved
Requests rejected
Requests requiring manual correction
```

---

## Quality

```text
Average correction count
Human review rate
Hallucination incidents
Recommendation overrides
```

---

## Efficiency

```text
Average processing time
Average human review time
Estimated manual time saved
```

---

## Reliability

```text
Successful executions
Failed executions
LLM failures
Validation failures
Fallback executions
```

---

# 12. Two-Week Measurement Plan

Create a simple table:

| Metric                | Week 1 | Week 2 |
| --------------------- | -----: | -----: |
| Requests processed    |      — |      — |
| Approval rate         |      — |      — |
| Human correction rate |      — |      — |
| Team override rate    |      — |      — |
| Average review time   |      — |      — |
| Failure rate          |      — |      — |
| Estimated time saved  |      — |      — |

Do not fabricate values before deployment.

---

# 13. Five-Minute Demo

The demo should tell a story rather than simply clicking through screens.

## 0:00–0:40 — Problem

Explain:

> Project requests arrive as messy, inconsistent descriptions. Someone has to interpret them, identify requirements, decide which team should handle them, and turn the request into an actionable starting point.

---

## 0:40–1:20 — Solution

Show:

```text
Messy request
      ↓
AI intake pipeline
      ↓
Structured project intake
```

Explain that the AI recommends rather than automatically assigns.

---

## 1:20–2:30 — Live Happy Path

Submit one realistic project request.

Show:

* Extraction
* Requirements
* Missing information
* Team recommendation
* Reasoning
* Checklist

---

## 2:30–3:15 — Human Review

Edit one generated field.

Then approve the intake.

Show that the final state is stored.

---

## 3:15–4:10 — Failure Handling

Demonstrate an ambiguous request.

Show:

```text
Insufficient confidence
      ↓
Human review
```

This is important.

It demonstrates that the system knows when not to pretend it knows.

---

## 4:10–4:40 — Evaluation

Show:

* Evaluation dataset
* Key metrics
* Before/after reliability
* Three major failure cases

---

## 4:40–5:00 — Value + Next Step

Explain:

* Manual effort reduced
* Current limitations
* What would be built next

---

# 14. Portfolio Case Study

Create a concise case study containing:

## Problem

Messy project requests create inconsistent requirements and slow down project intake.

## Solution

An AI-powered intake pipeline that transforms unstructured project requests into standardized, reviewable project records.

## Architecture

```text
Web UI
 ↓
FastAPI
 ↓
LLM
 ↓
Validation
 ↓
Recommendation
 ↓
Checklist
 ↓
Human Review
 ↓
SQLite
```

## Key Engineering Decisions

* Structured LLM outputs
* Pydantic validation
* Human approval
* Local LLM for development
* SQLite for v0
* Provider abstraction
* Explicit uncertainty handling

## Evaluation

Include actual measured results.

## Failure Handling

Explain the three most important failures and how they were fixed.

## Outcome

Explain the measurable reduction in manual effort.

## Limitations

Be honest.

## Next Steps

Examples:

```text
Email ingestion
Form integrations
PostgreSQL
Role-based access
Team capacity data
Historical recommendation learning
Project management integrations
Cloud deployment
```

---

# 15. What Should NOT Be Claimed

Do not claim:

```text
Fully autonomous project management
```

The system does not do that.

Do not claim:

```text
AI automatically assigns projects to teams
```

The v0 only recommends a team.

Do not claim:

```text
100% accurate
```

No meaningful evaluation supports that.

Do not claim:

```text
Production-ready enterprise platform
```

unless the infrastructure and security actually justify it.

Instead say:

```text
AI-assisted project intake pipeline with human approval.
```

---

# 16. Final Repository Structure

```text
project-intake-pipeline/
│
├── app/
│   ├── main.py
│   ├── models/
│   ├── services/
│   ├── providers/
│   ├── storage/
│   └── prompts/
│
├── tests/
│
├── evaluation/
│   ├── dataset.json
│   ├── baseline.json
│   ├── results.json
│   └── regression.json
│
├── docs/
│   ├── architecture.md
│   ├── data-flow.md
│   ├── evaluation.md
│   ├── user-guide.md
│   └── operator-runbook.md
│
├── demo/
│   └── demo-script.md
│
├── screenshots/
│
├── data/
│
├── .env.example
├── requirements.txt
└── README.md
```

---

# 17. Final Day 5 Checklist

## Product

* [ ] Final workflow works
* [ ] Human review works
* [ ] Final intake persists
* [ ] Error handling works

## Documentation

* [ ] Main README
* [ ] User guide
* [ ] Operator runbook
* [ ] Architecture documentation
* [ ] Data flow documentation
* [ ] Evaluation documentation
* [ ] Limitations documented

## Evaluation

* [ ] Test set included
* [ ] Actual results included
* [ ] Failure cases documented
* [ ] Regression results included

## Demo

* [ ] Five-minute demo recorded
* [ ] Happy path shown
* [ ] Failure case shown
* [ ] Evaluation shown
* [ ] Value demonstrated

## Portfolio

* [ ] Case study written
* [ ] Architecture diagram included
* [ ] Screenshots included
* [ ] Metrics included
* [ ] Limitations included
* [ ] Future roadmap included

---

# 18. Day 5 Definition of Done

Day 5 is complete when someone who has never seen the project can:

```text
Read README
     ↓
Understand the problem
     ↓
Understand the architecture
     ↓
Set up the application
     ↓
Run a project request
     ↓
Understand the output
     ↓
Review the evaluation
     ↓
Understand the limitations
     ↓
Modify the system
```

The final result should demonstrate more than:

> "I built an AI application."

It should demonstrate:

> **"I identified a workflow, designed an AI-assisted system around it, built the core, evaluated its behavior, hardened its failure modes, measured its value, and packaged it so another person can operate and improve it."**

That is the story you want MUST to see.
