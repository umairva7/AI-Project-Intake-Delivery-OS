# AI Project Intake & Delivery OS

> **MUST 5-Day Remote AI OS Sprint — Day 1: Discover, Map & Baseline**

## 1. Problem Overview

### The recurring workflow

When a new client starts a project, the initial project brief can arrive through different channels such as email, forms, documents, or free-form text.

These briefs are often inconsistent in structure and may contain incomplete, ambiguous, or conflicting information.

A delivery or project manager then has to manually:

1. Read and understand the client brief.
2. Extract the project's requirements.
3. Identify deliverables and constraints.
4. Detect missing or unclear information.
5. Determine which team or capability is most suitable.
6. Turn the requirements into an initial delivery checklist.
7. Clarify issues with the client or internal team before work begins.

This creates unnecessary manual work and increases the risk of miscommunication, missed requirements, and scope creep.

---

## 2. Target User

### Primary user

**Project Manager / Delivery Manager**

The system is designed for the person responsible for turning an incoming client request into a structured, actionable project intake.

### Secondary users

- Delivery teams
- Technical leads
- Account/project coordinators

The initial version focuses on the **Project Manager / Delivery Manager** workflow.

---

## 3. Job to Be Done

> When a new client project brief arrives, help the project manager quickly turn the unstructured request into a reliable project intake by extracting requirements, identifying missing or conflicting information, recommending an appropriate team, and generating an initial delivery checklist.

The system should reduce the amount of manual interpretation and formatting required before a project can move into delivery.

---

## 4. Current Workflow

### Existing manual process

```text
Client submits project brief
          ↓
PM reads email/document/form
          ↓
PM interprets requirements
          ↓
PM extracts important information
          ↓
PM identifies missing/ambiguous details
          ↓
PM decides which team/capability fits
          ↓
PM creates project notes
          ↓
PM creates initial checklist/tasks
          ↓
PM follows up for clarification
          ↓
Project moves toward delivery
```

---

## 5. Competitive Landscape & Research

The project intake problem is already addressed by several commercial tools. This validates that the workflow represents a real operational problem rather than an artificial AI use case.

### Examples:
- **Sensra**: AI-assisted client intake, structured briefs, scopes, delivery plans and task generation.
- **TaskMender**: Converts client emails/files/forms into project briefs, missing-information checklists and internal tasks.
- **anybrief**: Converts client notes/emails into structured briefs, requirements, deliverables and checklists.
- **ReqBrief**: Conducts AI-led client interviews and generates structured project briefs and open questions.
- **monday.com Project Intake Agent**: Collects project information, evaluates viability and provides recommendations.
- **Asana Project Intake**: Standardizes project requests and automates intake workflows.

### Positioning

This project is not intended to compete with these platforms as a complete project-management product.

The V1 focuses on demonstrating a specific AI workflow:

```text
Unstructured client input
        ↓
Requirement extraction
        ↓
Missing/conflict detection
        ↓
Scope-risk analysis
        ↓
Team recommendation
        ↓
Delivery checklist
        ↓
Human approval
```

The primary learning objective is to demonstrate reliable AI-assisted decision preparation, structured outputs, validation, human-in-the-loop controls, and measurable evaluation.

