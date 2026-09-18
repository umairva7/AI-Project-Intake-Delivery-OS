# AI Project Intake & Delivery OS

> **Automated, reliable AI-assisted decision preparation for project intake.**  
> *"AI recommends. Humans decide."*

The **AI Project Intake & Delivery OS** converts messy, unstructured client briefs (emails, meeting notes, intake forms) into structured, review-ready project packages. It extracts functional and technical requirements, detects missing details, recommends delivery teams using deterministic scoring, and compiles evidence-bound delivery checklists for human validation and sign-off.

The system does **not** make irreversible operational decisions or automatically assign teams. It standardizes decision preparation so project managers and delivery leads can review, correct, and approve project intakes in seconds rather than minutes.

---

## 1. Problem

Client project requests routinely arrive as vague, contradictory, or unstructured text:
* Key technical constraints and timelines are buried across informal paragraphs.
* Critical delivery questions (e.g., scale, data formats, compliance, hosting) are omitted.
* Preliminary scoping and routing require manual triage, consuming 15–25 minutes per brief.
* Naive LLM extraction introduces hallucinations—inventing databases, frameworks, or cloud architectures never requested by the client.
* Unchecked inputs risk persisting sensitive credentials or malicious prompt injections directly into internal databases.

The **AI Project Intake & Delivery OS** automates this repetitive preparation work while enforcing strict validation, pre-ingestion security sanitization, and deterministic governance.

---

## 2. What the System Does

The end-to-end request processing flow is strictly partitioned into AI-driven, deterministic, and human-controlled stages:

```text
               Unstructured Client Brief (Web UI / REST API)
                                    ↓
        [Deterministic] Pre-Ingestion Security Scanner & Sanitizer
                        - Secret redaction to [REDACTED]
                        - Prompt / SQL injection detection
                                    ↓
        [AI-Driven] Requirement & Context Extraction (Groq / Ollama)
                    - Atomic functional decomposition (Rule 2b)
                    - Source-quote requirement grounding
                    - Scope constraints & missing information
                                    ↓
        [Deterministic] Extraction Usability & Confidence Gating
                        - Clamps failed extractions to 0.0
                        - Threshold: CONFIDENCE_THRESHOLD = 0.70
                        - Blocks unusable extractions from task generation
                                    ↓
        [Deterministic] Team Recommendation Engine
                        - Weighted keyword signal scoring across taxonomy
                        - Enterprise precedence rules & supporting teams
                                    ↓
        [AI + Deterministic] Evidence-Bound Delivery Checklist
                             - Task-to-evidence validation (TaskEvidence)
                             - Prunes unrequested frameworks & architectures
                             - Generates clarification checklist if extraction is gated
                                    ↓
        [Human-Controlled] Human Review & Governance
                           - Review flags, confidence metrics, and detected issues
                           - Approve intake (POST /briefs/{id}/approve)
                           - Mark issues / Request clarification (POST /briefs/{id}/mark-issues)
                                    ↓
        [Persistence] SQLite Database (requests, intakes, approved_intakes)
```

### Stage Responsibilities

| Stage | Mechanism | Responsibility |
| :--- | :--- | :--- |
| **Security Scanning** | Deterministic | In-memory regex scrubbing of credentials (`[REDACTED]`) and injection defense before SQLite persistence. |
| **Requirement Extraction** | AI-Driven (LLM) | Parses unstructured prose into structured JSON with atomic requirements and exact source quotes. |
| **Usability Gating** | Deterministic | Circuit breaker evaluating confidence ($\ge 0.70$), schema validity, and input length. |
| **Team Recommendation** | Deterministic | Config-driven weighted keyword scoring across predefined engineering taxonomy (not an LLM prompt). |
| **Checklist Generation** | Hybrid | LLM drafts delivery tasks; deterministic filter strips unrequested technical assumptions (`UNSUPPORTED_TECH_TERMS`). |
| **Approval & Sign-off** | Human-Controlled | Human coordinator inspects flags, edits outputs, and gives final sign-off. |

---

## 3. Key Design Principle

> ### **AI recommends. Humans decide.**

The system never autonomously assigns client projects to teams or commits engineering resources.
1. **AI extracts and structures**: The LLM handles the fuzzy linguistic translation of messy prose into structured data models.
2. **Deterministic governance constrains output**: Rule-based scoring handles team recommendations; code-level circuit breakers block hallucinated architectures.
3. **Escalation over false confidence**: When an input is ambiguous, incomplete, or adversarial, the system flags the intake for manual human review rather than guessing.
4. **Human accountability**: The project manager or delivery lead retains complete authority to modify requirements, adjust team allocations, or request client clarification.

---

## 4. Architecture Overview

The system is built as a modular FastAPI service with strict separation between API handling, service orchestration, provider abstractions, and data storage.

```text
┌─────────────────────────────────────────────────────────┐
│              Browser UI / REST API Clients              │
└────────────────────────────┬────────────────────────────┘
                             │ HTTP JSON
                             ▼
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Application                   │
│         app/main.py — Endpoints, CORS, Error Handlers   │
└────────────────────────────┬────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│                   Intake Orchestrator                   │
│         app/orchestrator.py — Workflow Coordination     │
└──────┬─────────────────────┬─────────────────────┬──────┘
       │                     │                     │
       ▼                     ▼                     ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   Security   │      │  LLM Engine  │      │ Team Routing │
│  Sanitizer   │      │  Extraction  │      │ Deterministic│
│ (security.py)│      │(extraction.py│      │ (recom.py)   │
└──────────────┘      └──────┬───────┘      └──────────────┘
                             │
                             ▼
                      ┌──────────────┐
                      │ Usability    │
                      │ Gating       │
                      │ (models.py)  │
                      └──────┬───────┘
                             │
                             ▼
                      ┌──────────────┐
                      │ Checklist    │
                      │ Evidence     │
                      │ (checklist.py│
                      └──────────────┘
```

For complete implementation diagrams, data flow specifications, and component contracts, see [`ARCHITECTURE.md`](ARCHITECTURE.md).

---

## 5. Core Components

* **FastAPI Web Service (`app/main.py`)**: Exposes REST endpoints (`/briefs`, `/briefs/{id}`, `/approve`, `/mark-issues`, `/health`), mounts static frontend assets, and provides error handling that prevents stack trace leaks.
* **Intake Orchestrator (`app/orchestrator.py`)**: Coordinates the end-to-end lifecycle—sanitizing input, calling extraction, running confidence gating, invoking recommendation and checklist engines, and updating SQLite records.
* **Extraction Service (`app/services/extraction.py`)**: Manages requirement extraction prompts, parses structured JSON, calculates heuristic confidence scores, and validates source-quote grounding.
* **LLM Provider Abstraction (`app/providers/`)**:
  * [`BaseLLMProvider`](app/providers/base.py): Abstract base class specifying the provider interface.
  * [`GroqProvider`](app/providers/groq.py): Primary cloud provider utilizing `openai/gpt-oss-120b` with deterministic sampling ($T=0.20$), JSON mode, and retry resilience.
  * [`OllamaProvider`](app/providers/ollama.py): Local provider running local models (e.g., `llama3:8b`) for offline development or privacy-constrained operations.
* **Deterministic Recommendation Service (`app/services/recommendation.py`)**: Rule-based team allocation using word-boundary signal matching and configurable weights defined in [`app/config.py`](app/config.py).
* **Evidence-Bound Checklist Service (`app/services/checklist.py`)**: Transforms validated requirements into actionable tasks bound to source quotes via `TaskEvidence`. Filters out unrequested architectures (`UNSUPPORTED_TECH_TERMS`).
* **Pre-Ingestion Security Scanner (`app/services/security.py`)**: Policy (b) in-memory scrubber that sanitizes credentials to `[REDACTED]` and detects SQL/prompt injections before database persistence.
* **Data Models & Gating (`app/models.py`)**: Pydantic v2 data models defining contracts for `RawBrief`, `ProjectExtraction`, `TeamRecommendation`, `Checklist`, and the `extraction_is_usable()` gating check.
* **Storage Layer (`app/storage/db.py`)**: SQLite storage managing tables for `requests`, `intakes`, and `approved_intakes`.
* **Evaluation Harness (`evaluation/`)**: Deterministic evaluation suite ([`eval_intake.py`](evaluation/eval_intake.py)) and unmocked live execution runner ([`eval_runner.py`](evaluation/eval_runner.py)).

---

## 6. AI vs. Deterministic Logic

| Responsibility | Type | Implementation | Why Deterministic or AI? |
| :--- | :---: | :--- | :--- |
| **Brief Structuring** | **AI** | `GroqProvider` / `OllamaProvider` via `extraction.txt` | Linguistic variance in messy user briefs requires semantic extraction. |
| **Missing Information Discovery** | **AI** | `GroqProvider` / `OllamaProvider` | Identifying unstated project ambiguities requires domain reasoning. |
| **Initial Task Drafting** | **AI** | `GroqProvider` via `checklist.txt` | Drafting technical tasks benefits from LLM planning capability. |
| **Credential & Secret Redaction** | **Deterministic** | Regex scanner in `security.py` | Security guarantees must be 100% reliable; LLMs can overlook secrets. |
| **Injection Attempt Detection** | **Deterministic** | Pattern matching in `security.py` | Defends against malicious SQL and instruction-override payloads. |
| **Team Recommendation** | **Deterministic** | Signal scoring in `recommendation.py` | Eliminates hallucinated routing; ensures auditable, reproducible allocation. |
| **Extraction Usability Gating** | **Deterministic** | `extraction_is_usable()` in `models.py` | Enforces hard cutoff ($0.70$) to block garbage inputs from generating work. |
| **Hallucination Pruning** | **Deterministic** | `UNSUPPORTED_TECH_TERMS` filter in `checklist.py` | Prevents models from inventing Docker, K8s, Redis, or RAG without evidence. |
| **Schema Validation** | **Deterministic** | Pydantic v2 models | Strict data typing prevents malformed payloads from propagating. |

---

## 7. Human-in-the-Loop

The system intentionally escalates low-confidence or uncertain cases rather than feigning certainty:

* **Automatic Escalation Triggers**:
  * Extraction confidence below threshold (`< 0.70`).
  * Extraction status marked as `failed` or provider connection errors.
  * Ambiguous, contradictory, or placeholder briefs (e.g., Lorem Ipsum).
  * Detection of sensitive credentials or prompt injection strings.
  * Requirement descriptions lacking confirmed source quotes.
  * Competing team routing scores resulting in low recommendation confidence.
* **Reviewer Interface (`frontend/` or REST API)**:
  * Coordinators view extracted requirements alongside direct source quotes.
  * Unconfirmed inferences are highlighted for manual verification.
  * Missing information items are presented as ready-to-send client clarification questions.
  * Reviewers can approve directly (`POST /briefs/{id}/approve`) or flag specific issues (`POST /briefs/{id}/mark-issues`).

---

## 8. Security

During initial evaluation, an empirical audit on test case `TC-017` revealed that raw brief text containing plaintext credentials was being persisted directly to SQLite audit tables prior to any extraction or review.

### Implemented Security Controls: Policy (b) Sanitized-Only
1. **Pre-Ingestion In-Memory Sanitization (`app/services/security.py`)**: All briefs pass through `scan_and_sanitize_brief()` before database insertion or logging.
2. **Credential Redaction**: Passwords (`password is [REDACTED]`) and API keys (`sk-[a-zA-Z0-9]{10,}`) are permanently scrubbed to `[REDACTED]`.
3. **Injection Detection**: SQL injection payloads (`'; DROP TABLE ...`) and prompt injection overrides (`ignore previous instructions`) are flagged.
4. **Automatic Escalation**: Any detected security risk immediately sets `requires_manual_review = True` and appends an audit notice to `review_notes`.
5. **Regression Coverage**: Verified by [`tests/test_regression_eval.py::test_regression_tc017_secret_free_sqlite`](tests/test_regression_eval.py), confirming zero plaintext secrets exist in SQLite storage.

---

## 9. Evaluation

The pipeline was evaluated against a **Golden Dataset of 20 test cases** across six operational categories:
1. `clear_requests` (4 cases): Well-specified web, mobile, and CMS projects.
2. `ai_ml_requests` (2 cases): Machine learning classification and recommendation pipelines.
3. `automation_requests` (2 cases): CSV cleaning and invoice document OCR pipelines.
4. `ambiguous_requests` (3 cases): Dangerously vague or misdiagnosed briefs.
5. `multi_team_requests` (3 cases): Complex cross-functional enterprise workflows.
6. `edge_cases` (6 cases): Empty briefs, minimal inputs, SQL/prompt injections, contradictory goals, buzzwords, and Latin placeholder text.

### Baseline vs. Post-Fix Performance

The table below contrasts initial baseline pipeline measurements against final post-fix measurements, demonstrating the impact of taxonomy expansion, prompt iteration, and security hardening:

| Metric | Baseline (Initial Run) | Post-Fix (Final Evaluation) | Delta | Status |
| :--- | :---: | :---: | :---: | :---: |
| **Team Decision Accuracy** | **75.0%** (15/20) | **100.0%** (20/20) | **+25.0%** | **Target Met ($\ge 85\%$)** |
| **Requirement Precision (Micro)** | **42.9%** (42/98) | **41.4%** (36/87) | -1.5% | Trade-off (Tighter Scope) |
| **Requirement Recall (Micro)** | **47.1%** (41/87) | **51.4%** (36/70) | **+4.3%** | Improved Coverage |
| **Unsupported Inference Rate** | **7.8%** (8/102) | **2.3%** (2/87) | **-5.5%** | **70.5% Hallucination Drop** |
| **Missing Info Recall (Micro)** | **20.7%** (17/82) | **28.7%** (25/87) | **+8.0%** | Improved Discovery |
| **Human Review Rate (Clear Briefs)** | **75.0%** (3/4 flagged) | **0.0%** (0/4 flagged) | **-75.0%** | Zero False Escalations |
| **Human Review Rate (Ambiguous/Edge)**| **100.0%** (9/9 flagged) | **100.0%** (9/9 flagged) | 0.0% | 100% Safety Retention |
| **Overall Human Review Escalation** | **90.0%** (18/20) | **70.0%** (14/20) | -20.0% | Optimized Manual Overhead |
| **Sensitive Data Detection Rate** | **0.0%** (0/1) | **100.0%** (1/1) | **+100.0%** | **Vulnerability Resolved** |
| **Prompt Injection Detection Rate** | **0.0%** (0/1) | **100.0%** (1/1) | **+100.0%** | **Vulnerability Resolved** |
| **Mean Pipeline Latency** | **2,865.6 ms** | **3,521.9 ms** | +656.3 ms | Within SLA ($< 5,000\text{ ms}$) |
| **P95 Pipeline Latency** | **5,077.0 ms** | **5,026.0 ms** | -51.0 ms | Near Target ($5,000\text{ ms}$) |
| **Unhandled Exception Rate** | **0.0%** (0/20) | **0.0%** (0/20) | 0.0% | Zero Runtime Crashes |

*Note: Baseline and post-fix metrics are recorded in [`evaluation/post_fix_results.json`](evaluation/post_fix_results.json), [`evaluation/baseline_results.json`](evaluation/baseline_results.json), and [`evaluation/eval_report.md`](evaluation/eval_report.md).*

---

## 10. Automated Tests

The repository maintains an automated test suite of **207 passing tests** providing full regression protection:

```bash
$ pytest
======================= 207 passed, 1 warning in 15.11s =======================
```

### Test Suite Breakdown

* **Models & Schema Boundary Tests (`tests/test_models.py` — 73 tests)**: Boundary values for confidence ($[0.0, 1.0]$), input string length minimums/maximums, timezone handling, mutable default isolation, and status transition assertions.
* **Groq Cloud Provider Tests (`tests/test_groq_provider.py` — 24 tests)**: REST communication, API key authentication checks, rate limit backoff (HTTP 429), server error handling (HTTP 500), and API key log masking.
* **Ollama Local Provider Tests (`tests/test_ollama_provider.py` — 18 tests)**: Markdown fence extraction, raw JSON parsing, retries on missing schema fields, offline connection-refused handling, and health probes.
* **Team Recommendation Tests (`tests/test_recommendation.py` — 17 tests)**: Regex word-boundary signal matching, score tie-breaking, penalty logic for competing domains, and fallback for empty extractions.
* **Extraction Service Tests (`tests/test_extraction.py` — 16 tests)**: Prompt composition, heuristic scoring, source-quote verification, and confidence clamping.
* **Delivery Checklist Tests (`tests/test_checklist.py` — 13 tests)**: Critical vs. minor missing detail filtering, effort estimation defaults, task deduplication, and dependency resolution.
* **FastAPI Endpoint Tests (`tests/test_api.py` — 12 tests)**: Brief submission (`POST /briefs`), intake retrieval (`GET /briefs/{id}`), approval (`POST /briefs/{id}/approve`), issue flagging (`POST /briefs/{id}/mark-issues`), health probe (`GET /health`), and CORS validation.
* **Orchestration Workflow Tests (`tests/test_orchestrator.py` — 9 tests)**: End-to-end orchestration, provider failure fallbacks, logging emission across lifecycle events, and intake state transitions.
* **Regression Evaluation Tests (`tests/test_regression_eval.py` — 8 tests)**: Locks in routing fixes for failure cases TC-004, TC-006, TC-007, TC-008, TC-012, Spark/Kafka enterprise rules, and TC-017 SQLite secret sanitation.
* **Extraction Gating Tests (`tests/test_extraction_gating.py` — 8 tests)**: Usability circuit breaker verification, zero-confidence enforcement, and error contamination prevention.
* **Evidence-Bound Checklist Tests (`tests/test_evidence_bound_checklist.py` — 5 tests)**: Enforces `TaskEvidence` attachment and prunes unsupported technical buzzwords.
* **Database & Storage Tests (`tests/test_storage.py` — 4 tests)**: SQLite schema creation, foreign key enforcement, record insertion, and approval state updates.

---

## 11. Quickstart & Reviewer Workflow

### 1. Installation

Clone the repository and install dependencies in a Python virtual environment (Python 3.10+ supported; Python 3.12 recommended):

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy the sample environment file:

```bash
cp .env.example .env
```

Edit `.env` to configure your preferred provider:
```ini
# Primary cloud provider (recommended)
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-120b

# Or local provider
# LLM_PROVIDER=ollama
# OLLAMA_BASE_URL=http://localhost:11434
# OLLAMA_MODEL=llama3:8b

DATABASE_URL=sqlite:///./data/intake.db
CONFIDENCE_THRESHOLD=0.70
```

### 3. Run Automated Tests

Execute the 207 unit, integration, and regression tests:

```bash
pytest
```

### 4. Run Offline Evaluation (No API Key Required)

Reproduce the exact reported metrics deterministically using pre-recorded pipeline predictions:

```bash
# Score post-fix predictions against the golden dataset
python3 evaluation/eval_intake.py \
  evaluation/dataset.json \
  evaluation/post_fix_predictions.json \
  evaluation/post_fix_results.json

# Score baseline predictions to observe the failure patterns
python3 evaluation/eval_intake.py \
  evaluation/dataset.json \
  evaluation/baseline_predictions.json \
  evaluation/baseline_results.json
```

### 5. Run Live Pipeline Evaluation (Live LLM Inference)

Execute all 20 golden test cases through live Groq Cloud inference (requires `GROQ_API_KEY` in `.env`):

```bash
python3 evaluation/eval_runner.py evaluation/dataset.json evaluation/eval_predictions_live.json
```

### 6. Run Application & Web UI

Start the FastAPI application using Uvicorn:

```bash
uvicorn app.main:app --reload --port 8000
```

Open your browser to:
* **Interactive Web Interface**: [`http://localhost:8000/frontend/index.html`](http://localhost:8000/frontend/index.html)
* **API Documentation (Swagger UI)**: [`http://localhost:8000/docs`](http://localhost:8000/docs)
* **Health Check**: [`http://localhost:8000/health`](http://localhost:8000/health)

---

## 12. Repository Structure

```text
AI Project Intake/
├── app/
│   ├── config.py                 # Application settings and team taxonomy signals
│   ├── main.py                   # FastAPI app, REST routes, static file mounting
│   ├── models.py                 # Pydantic v2 data models and extraction usability gate
│   ├── orchestrator.py           # IntakeOrchestrator pipeline coordinator
│   ├── prompts/
│   │   ├── checklist.txt         # Evidence-bound checklist prompt
│   │   └── extraction.txt        # Structured requirement extraction prompt (Rules 1-15)
│   ├── providers/
│   │   ├── base.py               # BaseLLMProvider abstract interface
│   │   ├── groq.py               # Groq Cloud API provider (openai/gpt-oss-120b)
│   │   └── ollama.py             # Local Ollama HTTP API provider
│   ├── services/
│   │   ├── checklist.py          # Evidence-bound checklist generator & term filter
│   │   ├── extraction.py         # Requirement extraction & heuristic scoring
│   │   ├── recommendation.py     # Deterministic weighted keyword team recommender
│   │   └── security.py           # Policy (b) in-memory sanitizer & injection scanner
│   └── storage/
│       └── db.py                 # SQLite database schema and connection manager
│
├── evaluation/
│   ├── dataset.json              # 20 golden test cases with manual ground truth
│   ├── eval_intake.py            # Deterministic scoring engine & markdown table reporter
│   ├── eval_runner.py            # Unmocked live pipeline evaluation runner
│   ├── eval_report.md            # In-depth evaluation report and case failure audit
│   ├── baseline_predictions.json # Raw predictions from initial baseline run
│   ├── baseline_results.json     # Baseline metrics JSON (75.0% accuracy, 0% security)
│   ├── post_fix_predictions.json # Raw predictions from final post-fix run
│   └── post_fix_results.json    # Final post-fix metrics JSON (100.0% accuracy, 100% security)
│
├── frontend/                     # Lightweight HTML5 / CSS3 / Vanilla JS review interface
│   ├── app.js
│   ├── index.html
│   └── styles.css
│
├── tests/                        # 207 automated tests across 12 modules
│   ├── test_api.py
│   ├── test_checklist.py
│   ├── test_evidence_bound_checklist.py
│   ├── test_extraction.py
│   ├── test_extraction_gating.py
│   ├── test_groq_provider.py
│   ├── test_models.py
│   ├── test_ollama_provider.py
│   ├── test_orchestrator.py
│   ├── test_recommendation.py
│   ├── test_regression_eval.py   # Failure case regressions (TC-004, 006, 007, 008, 012, 017)
│   └── test_storage.py
│
├── ARCHITECTURE.md               # Detailed technical architecture and data flow
├── AI_COLLABORATION_NOTES.md     # Engineering decision records and AI review evidence
├── requirements.txt              # Production and test dependencies
└── vercel.json                   # Serverless deployment configuration
```

---

## 13. Limitations

* **Golden Dataset Size ($N = 20$)**: The evaluation set provides representative coverage across 6 core project typologies, but does not provide statistical confidence intervals across hundreds of enterprise domain variants.
* **Probabilistic LLM Extraction**: While inference is run at low temperature ($T = 0.20$), wording in extracted JSON requirements can vary across runs, affecting exact token-level overlap.
* **Requirement Precision / Recall Trade-off**: Post-fix requirement precision is 41.4% and recall is 51.4%. When extracting requirements from complex multi-sentence requests, models often create granular breakdowns that do not perfectly align with human ground-truth groupings.
* **Advisory Team Recommendation**: The deterministic team recommendation is strictly advisory based on keyword signals. Complex edge cases with contradictory goals require human coordinator routing.
* **Network & Provider Dependency**: Cloud inference via Groq requires outbound internet access and has a mean latency of ~3.5 seconds ($p95 = 5.0\text{s}$). Offline execution via Ollama requires local GPU/CPU compute.

---https://ai-project-intake-delivery-os.vercel.app/

## 14. Documentation Links

* Technical Architecture: [`ARCHITECTURE.md`](ARCHITECTURE.md)
* AI Review, Rejections & Engineering Decisions: [`AI_COLLABORATION_NOTES.md`](AI_COLLABORATION_NOTES.md)
* Comprehensive Evaluation & Empirical Failure Audit: [`evaluation/eval_report.md`](evaluation/eval_report.md)
