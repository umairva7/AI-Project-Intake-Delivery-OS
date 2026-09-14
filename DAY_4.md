# Day 4: Evaluate, Break, and Harden

## Candidate/Project Intake Pipeline

### Objective

Deliberately try to break the system.

The goal is not to prove that the pipeline works once.

The goal is to determine:

* Where it fails
* Why it fails
* How often it fails
* Whether the failure is visible
* Whether the system recovers safely
* Whether human review catches dangerous outputs

### Key Question

> **Can you explain quality and failure across multiple conditions, not just one successful example?**

---

# 1. Evaluation Philosophy

The system should be evaluated using a fixed test set rather than cherry-picked examples.

Create a dataset containing different types of project requests.

```text
Evaluation Set
│
├── Clear requests
├── Ambiguous requests
├── Incomplete requests
├── Very short requests
├── Long requests
├── Technical requests
├── Non-technical requests
├── Multi-team requests
├── Contradictory requests
└── Malformed / adversarial inputs
```

Target:

**At least 20 test cases.**

A larger set can be added later.

---

# 2. Evaluation Dataset

Each test case should contain:

```json
{
  "case_id": "TC-001",
  "input": "...",
  "expected_team": "Web Development",
  "expected_requirements": [
    "..."
  ],
  "expected_missing_information": [
    "..."
  ]
}
```

The expected values should be created manually.

They become the evaluation baseline.

---

# 3. Test Categories

## Category A — Clear Requests

Example:

```text
Build a React frontend with a Python API for an internal
employee dashboard.
```

Expected:

```text
Team: Web Development
```

---

## Category B — AI / ML

```text
We need a system that classifies customer support tickets using
historical labeled data and automatically routes them by category.
```

Expected:

```text
Team: AI / ML
```

---

## Category C — Automation

```text
Every morning collect sales data from three websites, clean it,
and send a summary to the operations team.
```

Expected:

```text
Team: Automation / Data
```

---

## Category D — Ambiguous

```text
We need something to improve our customer service using AI.
```

Expected:

```text
Team: Needs human review
```

The system should not confidently invent a solution.

---

## Category E — Multi-team

```text
Build a mobile app with an AI recommendation engine and a
real-time backend.
```

Expected:

```text
Possible teams:
Mobile Development
AI / ML
Backend

Human review required
```

---

# 4. Metrics

Measure at least:

## Extraction Accuracy

```text
Correct extracted facts
-----------------------
Expected important facts
```

Target:

```text
≥ 90%
```

---

## Requirement Recall

How many expected requirements were identified?

Target:

```text
≥ 85%
```

---

## Hallucination Rate

How many unsupported requirements were added?

Target:

```text
< 5%
```

For this system, hallucination rate is particularly important.

Missing a requirement is bad.

Inventing a requirement and presenting it as fact is worse.

---

## Team Recommendation Accuracy

```text
Correct recommendations
-----------------------
Cases with clear expected team
```

Target:

```text
≥ 85%
```

Ambiguous cases should be excluded from the simple accuracy calculation and measured separately.

---

## Human Review Rate

Track:

```text
Requests requiring human intervention
-------------------------------------
Total requests
```

This is not necessarily a metric to minimize.

A healthy system should escalate uncertain cases instead of pretending certainty.

---

## Latency

Track:

```text
Total processing time
```

Break it down into:

```text
Extraction
Recommendation
Checklist
Database
Total
```

---

# 5. Baseline

Create a baseline before hardening.

For example:

```text
Baseline

Extraction accuracy:       82%
Requirement recall:        76%
Hallucination rate:         9%
Team accuracy:             78%
Human review rate:         20%
Average latency:           14s
```

These numbers are placeholders until measured.

Do not invent final results.

---

# 6. Failure Testing

At least three significant failures must be investigated.

The preferred target is **five**.

---

# 7. Failure Case 1 — Ambiguous Request

### Input

```text
We need an AI system to improve our operations.
```

### Potential failure

The model confidently recommends:

```text
AI / ML
```

without enough information.

### Root Cause

The model is optimizing for producing an answer rather than recognizing uncertainty.

### Fix

Add an ambiguity rule:

```text
If insufficient evidence exists to distinguish between teams,
return NEEDS_HUMAN_REVIEW.
```

---

# 8. Failure Case 2 — Hallucinated Requirement

### Input

```text
Build a property listing website with search and an admin panel.
```

### Potential failure

System adds:

```text
OAuth authentication
Payment processing
Google Maps integration
```

even though none were requested.

### Root Cause

The LLM is filling common product requirements from prior knowledge.

### Fix

Explicit extraction instruction:

```text
Only classify information explicitly present in the input
as confirmed requirements.

Potential requirements inferred from context must be placed
under suggestions or missing information.
```

---

# 9. Failure Case 3 — Invalid Structured Output

### Failure

LLM returns malformed JSON.

### Root Cause

LLM output is probabilistic.

### Fix

Pipeline:

```text
LLM
 ↓
Parse
 ↓
Pydantic
 ↓
FAIL
 ↓
Retry with correction
 ↓
FAIL
 ↓
Human review
```

---

# 10. Failure Case 4 — Multi-Team Project

### Input

```text
Build a mobile application with an AI recommendation engine,
real-time messaging and cloud infrastructure.
```

### Potential failure

System returns:

```text
AI / ML
```

as though this were a single-team project.

### Root Cause

Team recommendation assumes a single dominant team.

### Fix

Allow:

```json
{
  "recommended_team": "Mixed / Cross-functional",
  "supporting_teams": [
    "Mobile Development",
    "AI / ML",
    "DevOps"
  ],
  "requires_human_review": true
}
```

---

# 11. Failure Case 5 — Very Long Input

Test:

* Repeated information
* Irrelevant background
* Contradictory requirements
* Large amounts of text

### Measure

Does the system:

* Preserve important requirements?
* Ignore irrelevant information?
* Detect contradictions?
* Remain within latency limits?

---

# 12. Hardening Strategy

Use the appropriate control for each failure.

## Validation

Use when:

```text
Output structure is wrong
```

---

## Retry

Use when:

```text
Temporary LLM failure
Malformed structured output
```

---

## Fallback

Use when:

```text
LLM unavailable
Repeated validation failure
```

---

## Confidence Indicator

Use when:

```text
Recommendation is uncertain
```

---

## Human Approval

Use when:

```text
High-impact uncertainty
Multi-team project
Contradictory information
Missing critical information
```

---

# 13. Regression Testing

After every major fix:

```text
Old test set
     ↓
Run again
     ↓
Compare results
```

Create a table:

| Metric              |   Before |    After | Change |
| ------------------- | -------: | -------: | -----: |
| Extraction accuracy | measured | measured |    +/- |
| Requirement recall  | measured | measured |    +/- |
| Hallucination rate  | measured | measured |    +/- |
| Team accuracy       | measured | measured |    +/- |
| Human review rate   | measured | measured |    +/- |
| Avg latency         | measured | measured |    +/- |

Never claim improvement unless the test data demonstrates it.

---

# 14. Quality Gates

The final system should meet minimum thresholds.

Suggested initial gates:

| Metric                              | Minimum |
| ----------------------------------- | ------: |
| Extraction accuracy                 |   ≥ 90% |
| Requirement recall                  |   ≥ 85% |
| Hallucination rate                  |    ≤ 5% |
| Clear-case team accuracy            |   ≥ 85% |
| Invalid-output recovery             |    100% |
| Critical failures silently accepted |       0 |

These are engineering targets, not guaranteed results.

If the system misses them, document the gap instead of quietly changing the numbers.

---

# 15. Target User Feedback

Run the improved version with the proxy user again.

Ask them to complete the workflow without developer assistance.

Collect feedback on:

### Understanding

* Did they understand the output?
* Did they understand the recommendation?

### Trust

* Did they trust the AI recommendation?
* Did confidence indicators help?

### Editing

* Could they easily correct mistakes?

### Workflow

* Did the interface feel faster than manual intake?

---

# 16. Feedback Log

Record:

```text
Feedback
--------
"The missing information section was useful."

Action
------
Keep missing-information section visible.

Feedback
--------
"I didn't understand why Web Development was recommended."

Action
------
Show recommendation reasoning directly below team recommendation.

Feedback
--------
"I wanted to edit the checklist."

Action
------
Make checklist items editable before approval.
```

---

# 17. Day 4 Deliverables

* [ ] Evaluation dataset created
* [ ] At least 20 test cases
* [ ] Baseline measured
* [ ] Extraction accuracy measured
* [ ] Requirement recall measured
* [ ] Hallucination rate measured
* [ ] Team recommendation accuracy measured
* [ ] Latency measured
* [ ] At least 3 failures documented
* [ ] Root causes identified
* [ ] Hardening changes implemented
* [ ] Regression test completed
* [ ] Proxy user feedback collected
* [ ] Feedback-driven changes implemented

---

# 18. Day 4 Definition of Done

Day 4 is complete when you can confidently explain:

> "The system performs at X% on my evaluation set. It fails mainly under these conditions. I identified those failures, changed the system to handle them, and regression testing showed these before-and-after results."

That statement is considerably more valuable than:

> "It worked when I tested it."

The second statement is how demos die in production.
