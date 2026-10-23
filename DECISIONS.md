# CURE Decisions

## 2026-10-23 — Start with a modular monolith

**Decision:** Use the required React frontend, FastAPI backend, PostgreSQL database, local protected report storage, and Docker Compose as one modular monolith.

**Reason:** This is the requested stack and keeps the academic prototype understandable while supporting strict server-side authorization boundaries.

## 2026-10-23 — Do not make clinical or ML claims during setup

**Decision:** No dataset, label mapping, model, calibration claim, performance metric, report-extraction accuracy claim, or emergency rule is selected or represented as implemented during initial setup.

**Reason:** The workspace contains no implementation or evidence yet. The project brief expressly prohibits fabricated datasets, results, and clinical validity claims.

## 2026-10-23 — Preserve resumability from the first phase

**Decision:** `BACKLOG.md`, `HANDOFF.md`, and `DECISIONS.md` are the source of truth for project status and are updated at every meaningful task transition.

**Reason:** The project brief requires an accurate handoff if work is interrupted or continued by another agent.

## 2026-10-23 — Do not train before authorized dataset access and label review

**Decision:** MIMIC-IV-ED is the preferred research candidate because it includes ED triage and vital-sign data, but CURE will not download, train on, or claim results from it until a credentialed authorized investigator obtains dataset access and the urgency-label mapping is reviewed.

**Reason:** The dataset is restricted by credentialing, training, and a data-use agreement. A public NHAMCS alternative still requires feature/target inspection before selection.

## 2026-10-23 — Privileged roles cannot self-register

**Decision:** The public registration endpoint creates only patient accounts. Doctors, triage staff, and administrators must be created or assigned through a future administrator workflow.

**Reason:** Allowing self-selected privileged roles would defeat role-based access control.
