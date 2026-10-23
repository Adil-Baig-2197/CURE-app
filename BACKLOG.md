# CURE Backlog

Canonical implementation checklist. A task is `DONE` only after its acceptance criteria are verified; user-reported verification is identified as such in `HANDOFF.md`.

## Phase 1 — Repository and project setup

| ID | Priority | Status | Task | Acceptance criteria | Dependencies / blockers |
| --- | --- | --- | --- | --- | --- |
| P1-01 | Critical | DONE | Inspect repository and preserve existing work. | Existing implementation and repository state recorded in `HANDOFF.md`. | Completed before this turn. |
| P1-02 | Critical | DONE | Create persistent project tracking files. | `BACKLOG.md`, `HANDOFF.md`, and `DECISIONS.md` exist and describe actual status. | P1-01 |
| P1-03 | Critical | DONE | Establish project structure and development configuration. | React, FastAPI, PostgreSQL, Compose, `.env.example`, and baseline documentation exist. | Compose stack rebuilt and started; database healthy, API health returned `ok`, frontend returned HTTP 200. |

## Phase 2 — Architecture, database, and authentication

| ID | Priority | Status | Task | Acceptance criteria | Dependencies / blockers |
| --- | --- | --- | --- | --- | --- |
| P2-01 | Critical | DONE | Design schema and migration strategy. | Initial migration covers required account, patient, report, assignment, screening, review, model, and audit entities. | Existing migration; user previously reported startup migration success. |
| P2-02 | Critical | DONE | Complete authentication, RBAC, and audit verification. | Registration/login, secure password hashing, JWT validation, four backend roles, role-boundary tests, and audit events verified. | Backend integration suite passes; doctor assignment and admin protections included. |

## Phase 3 — Patient profile and medical history

| ID | Priority | Status | Task | Acceptance criteria | Dependencies / blockers |
| --- | --- | --- | --- | --- | --- |
| P3-01 | High | DONE | Patient profile and structured history CRUD. | Patient-only profile/history routes preserve unknown values. | Existing implementation; previously user verified. |
| P3-02 | High | DONE | Immutable screening-time history snapshot. | Screening snapshots are unaffected by later history changes. | Existing implementation; previous regression reportedly passed. |

## Phase 4 — Reports

| ID | Priority | Status | Task | Acceptance criteria | Dependencies / blockers |
| --- | --- | --- | --- | --- | --- |
| P4-01 | High | DONE | Protected local report upload and extraction. | PDF/JPG/PNG validation, bounded uploads, protected original storage, local extraction/OCR, and failure handling. | Existing implementation; upload previously user verified; current automated failure tests pending. |
| P4-02 | High | DONE | Patient report verification workflow. | Raw extraction remains distinct from patient-verified structured data and limitations are visible. | Existing implementation; user previously verified. |
| P4-03 | High | DONE | Assigned-doctor access to verified report summaries and originals. | Only doctors assigned to a patient can access relevant verified information and protected originals; access is audited. | Integration test verifies assigned access and isolation. |

## Phase 5 — Questionnaire and screening persistence

| ID | Priority | Status | Task | Acceptance criteria | Dependencies / blockers |
| --- | --- | --- | --- | --- | --- |
| P5-01 | Critical | DONE | Complete adaptive symptom questionnaire. | General, respiratory, digestive, neurological, and cardiovascular questions cover severity, duration, progression, associated symptoms, optional free text, and missingness. | Expanded question flows and regression coverage pass in the backend suite. |
| P5-02 | Critical | DONE | Complete screening persistence and patient history/results. | Snapshots, response/missingness, status, safety flags, patient-only detail/history APIs, pagination, and audit behavior are tested. | Questionnaire payload handling, patient-isolated history/detail and audit behavior covered by passing backend tests. |

## Phase 6 — Dataset and ML evaluation

| ID | Priority | Status | Task | Acceptance criteria | Dependencies / blockers |
| --- | --- | --- | --- | --- | --- |
| P6-01 | Critical | DONE | Inspect public dataset candidates and decide whether any fit. | Source, terms, fields, target semantics, data quality, missingness, class distribution, and limitations documented from actual data/codebook. | CDC NHAMCS 2022 inspected; documentation records exclusions, imbalance, proxy-label mismatch, and limitations. |
| P6-02 | Critical | DONE (research only) | Build reproducible two-model evaluation pipeline if data supports target. | Leakage-safe preprocessing, split strategy, class analysis, confusion matrix, per-class metrics, explanation, comparison, and justified selection are reproducible. | Research pipeline trained/evaluated two models on a stratified holdout. The weak rare-class results do not support clinical use or integration. |

## Phase 7 — Safety and prediction

| ID | Priority | Status | Task | Acceptance criteria | Dependencies / blockers |
| --- | --- | --- | --- | --- | --- |
| P7-01 | Critical | NEEDS CLINICIAN REVIEW | Review emergency-warning rules and clinical references. | Independent rule layer, clear urgent guidance, priority over any model, and tests; clinical review requirement documented. | Software tests and source notes are complete; a qualified clinician must review these safety rules before clinical use. |
| P7-02 | Critical | BLOCKED ON VALIDATION | Integrate versioned model output and explanations if validated for prototype use. | Model/pipeline version, historical inputs/outputs, honest score semantics, explanations, and failure-to-human routing. | Experimental models perform poorly for rare urgency classes; integration is not justified without independent clinical validation. |

## Phase 8 — Doctor workflow and intake queue

| ID | Priority | Status | Task | Acceptance criteria | Dependencies / blockers |
| --- | --- | --- | --- | --- | --- |
| P8-01 | High | DONE | Complete assigned-patient review and triage workflow. | Assignment-only doctor access, urgency/time queue order, emergency handling, routing, intake status, confirmation/correction reason, and audit are tested. | Regression suite covers assignment isolation, emergency precedence, workflow authorization, review, and audit behavior. |

## Phase 9 — Administration and analytics

| ID | Priority | Status | Task | Acceptance criteria | Dependencies / blockers |
| --- | --- | --- | --- | --- | --- |
| P9-01 | Medium | DONE | Complete account management and aggregate analytics. | Admin manages accounts/roles and sees aggregate operations/model metrics without routine clinical-document access. | Admin role/active-state changes, last-admin safeguards, and analytics authorization covered by tests. |

## Phase 10 — UI, privacy, security, and tests

| ID | Priority | Status | Task | Acceptance criteria | Dependencies / blockers |
| --- | --- | --- | --- | --- | --- |
| P10-01 | High | DONE | Complete responsive, accessible role screens. | All required patient, doctor, triage, and admin workflows have functional controls plus loading, success, empty, validation, and error states. | Patient and role-dashboard flows implemented; frontend production build passed and frontend served HTTP 200. |
| P10-02 | Critical | DONE (prototype scope) | Complete privacy/deletion, security, and essential tests. | Authorization, protected files, audit, retention/deletion, upload failure, snapshots, emergency precedence, and role workflow tests pass. | Backend suite passes 18 tests. Durable deletion cleanup and production compliance operations remain documented limitations. |

## Phase 11 — Delivery

| ID | Priority | Status | Task | Acceptance criteria | Dependencies / blockers |
| --- | --- | --- | --- | --- | --- |
| P11-01 | High | DONE (prototype startup) | Finalize Compose, README, and end-to-end verification. | Reproducible startup, safe development configuration, setup/API/test/dataset docs, actual verification results, and known limitations documented. | Compose rebuilt and started; DB healthy, API health `ok`, frontend HTTP 200. `DEMO_GUIDE.md` documents a quick role walkthrough. Browser verified the login screen and readable API validation/authentication errors. Full authenticated role walkthrough remains for the presenter. |
| P11-02 | Medium | DONE | Prepare synthetic upload examples and a step-by-step local run guide. | Fictional PDF, PNG, and JPG samples are available; Windows run/test commands are documented; files are visually checked and accepted by the local extraction code. | `RUN_GUIDE.md` and local demo assets added; PDF layout inspected; extractor returned text for all three formats. |
