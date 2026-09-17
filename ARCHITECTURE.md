# System Architecture — AI Project Intake & Delivery OS

> **Operational Standard:** AI-assisted decision preparation with deterministic governance and human-in-the-loop validation.

---

## 1. System Overview

The **AI Project Intake & Delivery OS** is a production-grade FastAPI application engineered to ingest unstructured, ambiguous, or multi-faceted client project briefs and transform them into standardized, review-ready project intake packages. The system couples probabilistic large language model (LLM) semantic extraction with strict deterministic validation layers: pre-ingestion credential sanitization, extraction usability circuit breakers, rule-based team recommendation scoring, and evidence-bound delivery checklist synthesis. Irreversible operational decisions (e.g., project team assignment and client commitment) are strictly prohibited from occurring autonomously; the system prepares structured decisions for human review, verification, and sign-off.

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                      Client Layer (Browser / REST API)                  │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ HTTP JSON
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         FastAPI Web Server Layer                        │
│         Endpoints, CORS Middleware, Global Safe Exception Handlers      │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         Intake Orchestrator                             │
│                  Workflow Coordinator & Transaction Boundary            │
└──────┬─────────────────────┬─────────────────────┬──────────────────────┘
       │                     │                     │
       │ 1. Scan & Sanitize  │ 2. Extract JSON     │ 3. Score & Allocate
       ▼                     ▼                     ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  Security    │      │  AI Provider │      │ Team Routing │
│  Sanitizer   │      │ (Groq/Ollama)│      │ Deterministic│
│ (Policy b)   │      └──────┬───────┘      │  Taxonomy    │
└──────────────┘             │              └──────────────┘
                             ▼
                      ┌──────────────┐
                      │ Usability    │
                      │ Gating Check │
                      └──────┬───────┘
                             │
                             ▼
                      ┌──────────────┐
                      │ Checklist    │
                      │ Generator    │
                      │(Evidence-Bnd)│
                      └──────┬───────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Persistence & Human Governance                       │
│     SQLite Audit Tables (requests, intakes, approved_intakes)           │
│     Human Review & Approval Workflow (Approve / Mark Issues)            │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Request Lifecycle

Every project brief submitted to the intake pipeline transitions through an 11-step deterministic lifecycle:

```text
1. Ingestion: Client submits raw brief text via Web UI or POST /briefs
   ↓
2. Security Sanitization: Brief is scanned in memory for credentials and injection payloads
   ↓
3. Storage (Pre-flight): Sanitized brief is written to SQLite 'requests' table as 'processing'
   ↓
4. AI Requirement Extraction: Sanitized text sent to LLM provider (Groq Cloud or local Ollama)
   ↓
5. Schema Validation: Raw LLM output parsed into Pydantic ProjectExtraction schema
   ↓
6. Extraction Usability Gating: System checks confidence (>= 0.70) and status ('validated')
   ↓
7. Missing Information Analysis: System isolates critical unknowns affecting scope and delivery
   ↓
8. Team Recommendation: Deterministic scoring evaluates keyword signals across taxonomy
   ↓
9. Checklist Generation: Tasks compiled with explicit TaskEvidence; unrequested tech pruned
   ↓
10. Intake Persistence: Full structured payload persisted to SQLite 'intakes' table
   ↓
11. Human Review: Project coordinator inspects intake, resolves flags, and approves/rejects
```

---

## 3. API Layer

The REST API is implemented with FastAPI in [`app/main.py`](app/main.py). All internal exceptions are intercepted by global exception handlers to prevent raw Python tracebacks from leaking to clients.

### Implemented Endpoints

| Method | Endpoint | Request Body | Response Model | Description |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/health` | None | `{"status": "ok", ...}` | Service health probe for deployment checks. |
| `GET` | `/api/health` | None | `{"status": "ok", ...}` | Alias health probe for API clients. |
| `POST` | `/briefs` | `RawBrief` (`brief_text`, `source`) | `PendingIntake` | Ingests, sanitizes, and processes a new brief. |
| `GET` | `/briefs/{brief_id}` | None | `PendingIntake` | Retrieves an existing pending intake record by ID. |
| `POST` | `/briefs/{brief_id}/approve` | None | `{"status": "approved", "id": "..."}` | Approves pending intake and moves it to `approved_intakes`. |
| `POST` | `/briefs/{brief_id}/mark-issues`| `MarkIssuesRequest` (`issues: list[str]`) | `{"status": "flagged", "id": "..."}` | Flags issues on an intake and retains human review status. |
| `GET` | `/frontend/*` | Static assets | HTML / JS / CSS | Serves lightweight browser UI for manual intake review. |

### Obsolete Routes (Removed)
Earlier design prototypes referenced endpoints such as `/api/process` and `/api/approve`. These were deprecated and replaced by the RESTful `/briefs` hierarchy above.

---

## 4. AI Provider Architecture

The LLM integration is decoupled from core workflow logic via the [`BaseLLMProvider`](app/providers/base.py) abstract interface:

```text
                           ┌─────────────────────┐
                           │   BaseLLMProvider   │
                           │   (app/providers/   │
                           │      base.py)       │
                           └──────────┬──────────┘
                                      │
                   ┌──────────────────┴──────────────────┐
                   ▼                                     ▼
        ┌─────────────────────┐               ┌─────────────────────┐
        │    GroqProvider     │               │   OllamaProvider    │
        │ (app/providers/     │               │ (app/providers/     │
        │     groq.py)        │               │     ollama.py)      │
        └─────────────────────┘               └─────────────────────┘
```

### Provider Configurations

* **Groq Cloud (`GroqProvider`)**:
  * **Primary Model**: `openai/gpt-oss-120b` (configured in `app/config.py`).
  * **Protocol**: OpenAI-compatible REST completions endpoint (`https://api.groq.com/openai/v1`).
  * **Parameters**: Temperature $0.20$ (deterministic extraction), `response_format={"type": "json_object"}`.
  * **Resilience**: Explicit error classification for HTTP 401 (Auth), HTTP 429 (Rate Limit with backoff), and HTTP 500 (Server Error). Safe API key masking in all logs (`gsk_...1234`).
* **Ollama Local (`OllamaProvider`)**:
  * **Default Model**: `llama3:8b` via local daemon (`http://localhost:11434/api/generate`).
  * **Resilience**: JSON markdown fence stripper ([`clean_and_parse_json()`](app/providers/ollama.py#L41-L64)), multi-tier fallback for surrounding prose, retry handling on missing schema fields, and graceful recovery when the local daemon is offline.
* **Provider Selection**:
  * Managed via `LLM_PROVIDER` in `app/config.py` (`"groq"` or `"ollama"`).

---

## 5. Extraction Architecture

The extraction pipeline transforms raw text into a validated [`ProjectExtraction`](app/models.py) model using the system prompt defined in [`app/prompts/extraction.txt`](app/prompts/extraction.txt).

### Core Prompt Rules

1. **Rule 1 & 2 (No Inventions)**: Model must extract only information explicitly present in the brief. Inventing frameworks, databases, or budgets is strictly prohibited.
2. **Rule 2b (Atomic Functional Decomposition)**: If a sentence contains multiple deliverables (e.g., *"display employee info, project assignments, and work hours"*), the model must decompose them into individual atomic requirements rather than one compound string.
3. **Rule 4 (Source-Quote Grounding)**: Every extracted requirement must include an exact `source_quote` substring from the client's original brief.
4. **Rule 11 (Confidence Calibration)**: Confidence reflects **clarity of project goals**, not commercial completeness. Standard actionable requests score in $[0.80, 0.95]$ even if minor operational questions remain. Confidence drops below $0.60$ only when goals are contradictory or incoherent.
5. **Rule 12 (Vague Brief Handling)**: For extremely vague, contradictory, or placeholder briefs (e.g., *"Build me an app"*, *"Lorem Ipsum"*), the model is instructed to output an empty requirements array (`"requirements": []`) and populate `missing_information`.

---

## 6. Confidence and Gating (Circuit Breaker)

To prevent ungrounded LLM outputs from propagating into downstream delivery workflows, the orchestrator executes the [`extraction_is_usable()`](app/models.py) circuit breaker:

```python
def extraction_is_usable(extraction: Optional[ProjectExtraction]) -> bool:
    if extraction is None:
        return False
    if getattr(extraction, "extraction_status", None) == "failed":
        return False
    if extraction.confidence < settings.CONFIDENCE_THRESHOLD:  # 0.70
        return False
    return True
```

### Boundary Guarantees
* **Strict Zero-Confidence Clamping**: If extraction fails or the provider returns an error, confidence is strictly clamped to `0.0`. It cannot fall through to heuristic scoring.
* **Gated Delivery Flow**:
  * **Usable Extraction ($\ge 0.70$)**: Generates an implementation checklist bound to verified requirements.
  * **Unusable Extraction ($< 0.70$)**: Blocks implementation task generation. Automatically diverts to [`generate_clarification_checklist()`](app/services/checklist.py#L185-L265) and flags the intake for human review (`requires_manual_review = True`).

---

## 7. Team Recommendation Architecture

Unlike early exploratory prototypes, team allocation is **100% deterministic** and executed by [`app/services/recommendation.py`](app/services/recommendation.py). The prompt placeholder `app/prompts/recommendation.txt` is intentionally empty.

### Scoring Mechanism
1. **Word-Boundary Signal Matching**: Evaluates requirements and brief text against [`DEFAULT_TEAM_SIGNALS`](app/config.py#L9-L120) using `\b` regex boundaries (e.g., preventing `"ai"` from matching `"email"` or `"chair"`).
2. **Taxonomy & Weights**:
   * **Web Development**: `frontend` (+5), `react` (+5), `ecommerce` (+5), `shopping cart` (+5), `stripe` (+5), `fastapi` (+4), `dashboard` (+4).
   * **Mobile Development**: `mobile` (+5), `ios` (+5), `android` (+5), `swift` (+5), `flutter` (+5), `react native` (+5).
   * **AI / ML**: `machine learning` (+5), `model training` (+5), `recommendation engine` (+5), `personalized` (+4), `classification` (+4), `nlp` (+4).
   * **Automation / Data**: `automation` (+5), `invoice` (+5), `ocr` (+5), `csv` (+5), `data cleaning` (+4), `anomaly` (+4), `accounting` (+4).
   * **Data Engineering**: `data warehouse` (+5), `snowflake` (+5), `bigquery` (+5), `spark` (+5), `kafka` (+5).
   * **DevOps / Infrastructure**: `kubernetes` (+5), `docker` (+5), `aws` (+5), `ci/cd` (+5), `terraform` (+5).
3. **Enterprise Precedence Rules**:
   * If enterprise warehouse/streaming platforms (Snowflake, Spark, Kafka) are detected alongside automation terms, `Data Engineering` is assigned as primary lead, and `Automation / Data` is retained as supporting.
4. **Multi-Team & Supporting Team Allocation**:
   * Secondary teams qualify as supporting teams if they score $\ge 3$ points and their score is at least $20\%$ of the primary team's score.
   * If multiple strong teams qualify (or if the expected allocation is cross-functional), the primary team is supplemented with explicit `supporting_teams`.

---

## 8. Checklist Architecture

Delivery planning is handled by [`app/services/checklist.py`](app/services/checklist.py) with strict evidence-binding rules:

### TaskEvidence Data Contract
Every checklist item is stamped with a [`TaskEvidence`](app/models.py) model:
* `type`: `"requirement"` or `"missing_information"`.
* `source_quote`: Direct text excerpt justifying why the task exists.
* `confirmed`: Boolean flag indicating whether the requirement was explicitly verified.

### Anti-Hallucination Filtering
The checklist engine enforces two deterministic exclusion filters:
1. **`UNSUPPORTED_TECH_TERMS`**: Bans unrequested technologies (`vector database`, `rag`, `redis`, `celery`, `rabbitmq`, `kafka`, `docker`, `kubernetes`, `ci/cd`, `aws`, `gcp`, `azure`) unless the term appears explicitly in the source evidence corpus.
2. **`ERROR_CONTAMINATION_TERMS`**: When generating clarification checklists during provider degradation, terms like `connection refused`, `500`, `timeout`, `ollama`, or `traceback` are scrubbed to prevent system error messages from leaking into client tasks.

---

## 9. Security Architecture

The pipeline enforces **Policy (b): Sanitized-Only** pre-ingestion security via [`app/services/security.py`](app/services/security.py):

```text
Client Brief Text
        ↓
In-Memory Sanitizer (scan_and_sanitize_brief)
        ├── Check Known Test Secrets (P@ssw0rd123, sk-123456789abcdef)
        ├── Regex API Key Matcher (\bsk-[a-zA-Z0-9]{10,}\b)
        ├── Regex Password Matcher (password\s*(?:is|:|=)\s*)
        └── Injection Pattern Matcher (SQL DROP/DELETE, prompt instruction overrides)
        ↓
Output: (Sanitized Text, sensitive_detected, injection_detected)
        ├── Replace all credentials with '[REDACTED]'
        ├── Set sensitive_data_detected = True / injection_attempt_detected = True
        └── Escalate requires_manual_review = True
        ↓
SQLite Persistence & Logging (Zero Plaintext Secrets Touch Storage)
```

**Security Boundary Guarantee**: Security controls run in pure Python *before* database insertion, logging, or LLM invocation. Even if an LLM is compromised or hallucinations occur, plaintext credentials cannot reach SQLite storage.

---

## 10. Persistence Architecture

Data is stored locally in SQLite (`data/intake.db`) managed by [`app/storage/db.py`](app/storage/db.py):

* **`requests` Table**: Audit trail of brief submissions. Stores `id`, `sanitized raw_text`, `source`, `status` (`processing`, `pending_review`, `approved`, `rejected`), and timestamps.
* **`intakes` Table**: Active intake packages. Stores `request_id`, `extracted_json` (sanitized requirements, constraints, missing info), `recommended_team`, `team_confidence`, `checklist_json`, `requires_manual_review`, and `review_notes`.
* **`approved_intakes` Table**: Permanent record of intakes approved by human coordinators. Stores `id`, `intake_id`, `final_data`, and `approved_at`.

---

## 11. Human Review & Approval Workflow

Human review is an architectural safety net, not an optional convenience:

```text
                      Pending Intake Generated
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
     Requires Manual Review?          Clean / High Confidence?
     - Confidence < 0.70              - Confidence >= 0.70
     - Sensitive data flagged         - No security flags
     - Injection attempt flagged      - All requirements confirmed
     - Contradictory brief            - Unambiguous single/multi team
                 │                               │
                 ▼                               ▼
      Mandatory Human Review             Immediate Review
                 │                               │
                 └───────────────┬───────────────┘
                                 ▼
                     Human Coordinator Action
                     ├── POST /briefs/{id}/approve
                     │     → Status: 'approved' → Inserted into approved_intakes
                     └── POST /briefs/{id}/mark-issues
                           → Status: 'flagged' → Retained in pending_review
```

---

## 12. Evaluation Architecture

The repository enforces a dual testing and evaluation model:

```text
               EVALUATION HARNESS vs. AUTOMATED TEST SUITE
               
   Automated Tests (pytest)            Golden Evaluation (eval_intake.py)
   ────────────────────────            ──────────────────────────────────
   - 207 tests passing                 - 20 golden test cases
   - Offline, fast (~15s)              - Live LLM inference (eval_runner.py)
   - Mocks LLM providers               - Measures semantic output quality
   - Verifies code contracts,          - Evaluates accuracy, precision,
     gating, schemas & storage           recall, and latency percentiles
```

### Evaluation Pipeline Flow
1. **Golden Dataset (`evaluation/dataset.json`)**: 20 cases with human ground truth.
2. **Live Execution Runner (`evaluation/eval_runner.py`)**: Executes live unmocked inference via `IntakeOrchestrator`, writing predictions to `post_fix_predictions.json`.
3. **Deterministic Scoring Engine (`evaluation/eval_intake.py`)**: Computes bipartite greedy string matching (threshold $0.55$) and outputs sanitized evaluation metrics to `post_fix_results.json`.
4. **Regression Suite (`tests/test_regression_eval.py`)**: 8 deterministic pytest cases that continuously verify routing fixes and secret sanitization without invoking live LLMs.

---

## 13. Key Engineering Decisions

1. **Human-in-the-Loop Governance**: AI prepares structured data; humans retain final decision authority. Automatic team commitment is prohibited.
2. **Deterministic Recommendation Engine**: Replaced non-deterministic LLM routing prompts with rule-based keyword scoring, ensuring 100% reproducible routing.
3. **Policy (b) Pre-Ingestion Sanitization**: Shifted credential scrubbing upstream of SQLite persistence, eliminating database secret leaks.
4. **Extraction Usability Circuit Breaker**: Hardcoded confidence threshold ($0.70$) that blocks broken or vague extractions from generating implementation work.
5. **Evidence-Bound Delivery Checklists**: Implemented `TaskEvidence` models and unrequested architecture pruning (`UNSUPPORTED_TECH_TERMS`).
6. **Multi-Provider Abstraction**: Decoupled Groq Cloud and local Ollama behind `BaseLLMProvider`.
7. **Empirical Evaluation Over Intuition**: Measured pipeline quality against a 20-case golden benchmark, publishing baseline vs. post-fix comparisons.

---

## 14. Known Engineering Trade-Offs

* **Deterministic vs. Semantic Routing**: Keyword signal scoring provides 100% reproducibility and zero hallucination, but requires ongoing taxonomy maintenance when new tech domains emerge.
* **Strict Evidence Gating vs. Task Completeness**: Pruning unrequested technologies prevents hallucinated architectures (unsupported inference dropped to $2.3\%$), but results in conservative checklists that omit common default tooling unless mentioned by the client.
* **Micro Requirement Precision ($41.4\%$) vs. Recall ($51.4\%$)**: The extraction prompt decomposes compound requests into granular atomic requirements (Rule 2b), improving recall but occasionally generating more items than human ground-truth labels anticipate.
* **Cloud Latency vs. Local Autonomy**: Groq Cloud delivers high quality in ~3.5 seconds; local Ollama enables offline execution with sub-40ms outage fallback, but requires local GPU compute for live extraction.