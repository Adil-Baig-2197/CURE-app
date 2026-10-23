# CURE Backlog

Canonical project checklist. Status reflects verified work only.

## Phase 1 — Repository and project setup

| ID | Priority | Status | Task | Acceptance criteria | Dependencies / blockers |
| --- | --- | --- | --- | --- | --- |
| P1-01 | Critical | DONE | Inspect repository and preserve existing work. | Workspace inspected; existing implementation and repository state recorded in `HANDOFF.md`. | Initially empty and not a Git repository; Git was initialized during setup. |
| P1-02 | Critical | DONE | Create persistent project tracking files. | `BACKLOG.md`, `HANDOFF.md`, and `DECISIONS.md` exist and accurately describe current state. | P1-01 |
| P1-03 | Critical | DONE | Initialize modular-monolith project structure and development configuration. | React frontend, FastAPI backend, PostgreSQL/Docker Compose configuration, `.env.example`, `.gitignore`, and baseline README exist without secrets; Python syntax and Compose configuration validate; user verified the services start. | Docker API is inaccessible from the coding session, but user completed local runtime verification. |

## Phase 2 — Architecture, database, and authentication

| ID | Priority | Status | Task | Acceptance criteria | Dependencies / blockers |
| --- | --- | --- | --- | --- | --- |
| P2-01 | Critical | DONE | Design normalized PostgreSQL schema and migration strategy. | Initial migration covers users/roles, profiles/history, reports, assignments, screenings, reviews, intake, model metadata, and audit events; user verified it applies during backend startup. | P1-03 complete. |
| P2-02 | Critical | IN PROGRESS | Implement JWT authentication and backend RBAC. | Patient registration/login, secure password hashing, validated JWTs, four roles, authorization tests, and audit events for relevant actions. | Role workflows are implemented; full role integration tests remain. |

## Phase 3 — Patient profiles and medical history

| ID | Priority | Status | Task | Acceptance criteria | Dependencies / blockers |
| --- | --- | --- | --- | --- | --- |
| P3-01 | High | DONE | Implement patient profile and structured medical-history CRUD. | Patients can manage only their own records; unknown/missing data is not treated as normal; user confirmed endpoint verification and automated checks. | P2-02 authentication implementation is present; final test transcript is not retained in this chat. |
| P3-02 | High | DONE | Implement immutable screening-time medical snapshots. | Later profile/history edits cannot change historical screening inputs; user confirmed the automated regression test passes. | P3-01 complete. |

## Phase 4 — Reports

| ID | Priority | Status | Task | Acceptance criteria | Dependencies / blockers |
| --- | --- | --- | --- | --- | --- |
| P4-01 | High | DONE | Implement protected upload and local PDF/image extraction. | Type/size validation, protected local storage, local PDF/OCR extraction, and unverified output are implemented; user verified an upload succeeds. | Automated failure-case tests remain part of Phase 10 quality work. |
| P4-02 | High | DONE | Implement patient verification of extracted report data. | Raw and verified data remain separate; no-report declaration and uncertainty/limitations are visible; user verified the workflow. | P4-01 complete. |

## Phase 5 — Questionnaire and screening persistence

| ID | Priority | Status | Task | Acceptance criteria | Dependencies / blockers |
| --- | --- | --- | --- | --- | --- |
| P5-01 | Critical | IN PROGRESS | Build adaptive symptom questionnaire. | General, respiratory, digestive, neurological, and cardiovascular questions capture severity, duration, progression, associated symptoms, optional free text, and missingness. | P3-02 complete. |
| P5-02 | Critical | IN PROGRESS | Persist screening workflow and patient history. | Screens retain required snapshots, responses, missingness, status, and access constraints. | Questionnaire submission and snapshots exist; complete tests remain. |

## Phase 6 — Dataset discovery and ML experimentation

| ID | Critical | TODO | Discover and document candidate public datasets. | Features, labels, licensing/access, quality, class balance, relevance, and limitations are documented without fabricated claims. | P5-01 |
| P6-02 | Critical | TODO | Build reproducible two-model evaluation pipeline. | Leakage-safe preprocessing, stratified split where appropriate, class-imbalance analysis, per-class metrics, confusion matrix, explainability, and model-selection rationale are reproducible. | P6-01 |

## Phase 7 — Safety, prediction, and explainability

| ID | Critical | TODO | Implement independently evaluated emergency-warning rules. | Documented clinical-guidance sources, urgent display/routing, and precedence over ML are tested. | P5-02 |
| P7-02 | Critical | TODO | Integrate versioned prediction and explanation. | Saved model/pipeline, versioned inputs/outputs, honest scores, contributing factors, failure handling, and limitations display work. | P6-02, P7-01 |

## Phase 8 — Doctor workflow and intake queue

| ID | High | TODO | Implement assignments, prioritized queue, routing, and reviews. | Doctors see assigned patients only; triage routes/updates intake; emergency cases are highlighted; confirmations/corrections require reason and are auditable. | P2-02, P5-02, P7-02 |

## Phase 9 — Administration and analytics

| ID | Medium | TODO | Implement account/role management and aggregate operational/ML analytics. | Admin capabilities respect non-routine clinical-document access; aggregate metrics are functional. | P2-02, P8-01 |

## Phase 10 — UI, privacy, security, and tests

| ID | High | TODO | Complete responsive React screens and accessible states. | All mandatory screens and controls work with loading, empty, validation, success, and error states. | P3-01 through P9-01 |
| P10-02 | Critical | IN PROGRESS | Implement privacy, retention/deletion behavior, and complete essential tests. | Protected resources, safe logging, documented retention exceptions, verified deletion behavior, and required automated tests are verified. | Eligible deletion and retention-block behavior implemented; broader tests remain. |

## Phase 11 — Delivery

| ID | High | TODO | Finalize Docker Compose, README, and end-to-end verification. | Reproducible setup/documentation, dataset/model disclosures, demo setup guidance, and actual test results are recorded. | P10-01, P10-02 |
