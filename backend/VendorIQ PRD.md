# VendorIQ - Product Requirements Document

**AI-Powered Supplier Qualification & Batch Intelligence Platform** Version 1.0 | Hackathon MVP | 4-developer team

## 1. Executive Summary

VendorIQ is a B2B SaaS platform for skincare and cosmetics manufacturers. When a supplier ships a raw-material batch (for example L-Ascorbic Acid for a Vitamin C serum), VendorIQ ingests the supplier documents (COA, SDS, GMP certificate, test reports), extracts the key data, validates it against the company's own material specification, compares it to the supplier's history, predicts risk with a RandomForest model, has Kimi K3 explain the analysis in plain language, and a deterministic decision engine returns **APPROVED, REJECTED or NEEDS\_REVIEW**. The result is emailed and shown on a dashboard with a full audit trail.

Design principles: simple monolith (one FastAPI service), working end-to-end demo over enterprise complexity, deterministic rules decide, AI only explains.

## 2. Problem Statement

QA and procurement teams check supplier batches manually: reading PDFs, comparing values to specs, recalling past supplier problems, and emailing results. This is slow, inconsistent, and easy to get wrong. Missed deviations become production waste, recalls or compliance findings. Supplier history lives in spreadsheets and people's heads, so it is rarely used at the moment of the decision.

## 3. Product Vision

Every incoming batch gets a fast, consistent, explainable qualification result that combines hard checks (spec, documents, expiry) with supplier-history risk, so issues are caught before material enters production. Long term: a supplier-quality system of record for any regulated-ingredient manufacturer.

## 4. Target Users

| Role | Needs |
| --- | --- |
| QA / Quality Manager | Spec validation results, review queue, audit trail |
| Procurement Manager | Vendor performance, vendor-material approval status |
| Supply Chain / Operations Manager | Delivery reliability, batch status, trends |
| Manufacturing / Plant Manager | Quick go/no-go and risk overview |

## 5. User Stories

- As a user, I register a company and log in so my data is private to my company.
- As procurement, I add vendors and link them to materials, marking which are approved for which material.
- As QA, I configure a material specification (for example purity >= 99%) as JSON.
- As a receiving user, I create an incoming batch and upload COA, SDS and GMP files.
- As QA, I see extracted COA values, with MISSING or NEEDS\_REVIEW where data was unavailable.
- As QA, I see per-check validation results (PASS / FAIL / MISSING).
- As QA, I see the supplier's history compared to the current batch.
- As QA, I see a risk score, level and top risk factors, plus an AI explanation.
- As a manager, I receive an email with the decision and can retry failed sends.
- As QA, I resolve NEEDS\_REVIEW batches manually with a recorded reason.
- As a manager, I view dashboard analytics and the audit trail.

## 6. End-to-End Workflow

1. Register/login -> company created (tenant).
2. Vendors and raw materials created; vendor-material links created.
3. Batch created (status RECEIVED); documents uploaded (metadata + file stored).
4. User clicks Analyze (or upload triggers it). Batch -> PROCESSING.
5. Dev 2 pipeline: extract documents -> validate -> vendor history -> ML risk -> Kimi explanation. Batch -> VALIDATED -> PREDICTED.
6. Pipeline calls Dev 3 decision engine -> APPROVED / REJECTED / NEEDS\_REVIEW.
7. Dev 3 sends email, records email\_events, writes audit logs.
8. Dashboard and batch detail show everything. Any step failure -> FAILED with error, retryable.

The pipeline runs in a FastAPI BackgroundTask (no queue, no Celery); the frontend polls `GET /api/batches/{id}` for status.

## 7. Functional Requirements

| ID | Requirement | Owner | Priority |
| --- | --- | --- | --- |
| FR-1 | Register, login, me; JWT; inactive users rejected | Dev 1 | P0 |
| FR-2 | Vendor CRUD, search, pagination, soft delete | Dev 1 | P0 |
| FR-3 | Raw material CRUD with JSON specification | Dev 1 | P0 |
| FR-4 | Vendor-material relationship with approval flag | Dev 1 | P0 |
| FR-5 | Batch create/list/get with filters | Dev 1 | P0 |
| FR-6 | Document upload and metadata (PDF/PNG/JPG) | Dev 1 | P1 |
| FR-7 | Extraction of COA/SDS/GMP/spec data, no hallucination | Dev 2 | P1 |
| FR-8 | Validation engine with structured results | Dev 2 | P1 |
| FR-9 | Vendor history metrics | Dev 2 | P1 |
| FR-10 | RandomForest risk prediction | Dev 2 | P1 |
| FR-11 | Kimi K3 structured explanation | Dev 2 | P1 |
| FR-12 | Configurable deterministic decision engine | Dev 3 | P2 |
| FR-13 | Google SMTP emails, tracking, retry | Dev 3 | P2 |
| FR-14 | Audit trail (all major events) | Dev 1 helper, Dev 3 decision/email events | P2 |
| FR-15 | Analytics APIs from DB data | Dev 1 | P2 |
| FR-16 | React dashboard and all screens | Dev 4 | P2 |
| FR-17 | Deployment (Vercel, Render, Neon) | Dev 4 | P1 |

## 8. Non-Functional Requirements

- **Performance:** CRUD responses under 500 ms; full analysis of a 3-document batch under 60 s (Kimi call timeout 30 s).
- **Reliability:** pipeline errors set batch to FAILED with a message; Kimi or SMTP failure never blocks a decision.
- **Security:** see section 26. **Isolation:** every query filtered by company\_id.
- **Maintainability:** modular services, Pydantic schemas, Alembic migrations, OpenAPI docs.
- **Simplicity:** one backend service, one database, local disk or Render disk for files (hackathon scope).
- **Honesty:** synthetic data always labelled; configured specs never presented as regulations.

## 9. System Architecture

```
React (Vercel) --HTTPS/JWT--> FastAPI monolith (Render) --SQLAlchemy--> Neon PostgreSQL
                                  |-- services/extraction, validation, history   (Dev 2)
                                  |-- ml/ RandomForest (joblib model file)        (Dev 2)
                                  |-- services/kimi_service -> Kimi K3 API        (Dev 2)
                                  |-- services/decision, email -> Google SMTP     (Dev 3)
                                  |-- file storage: ./uploads/{company_id}/...
```

Routers call services; services use SQLAlchemy sessions. Kimi receives a plain Python dict (built by a mapper) and never touches the database. The ML model is loaded once at startup from a versioned joblib file.

## 10. Developer Responsibilities

| Developer | Owns | Does NOT own |
| --- | --- | --- |
| **Dev 1** | FastAPI skeleton, config, DB, SQLAlchemy models, Alembic, auth, tenant isolation, vendors, materials, vendor-materials, batches, document upload/metadata, analytics APIs, audit-log helper, error handler, seed data | Extraction, ML, Kimi, decisions, email, UI |
| **Dev 2** | Text extraction, COA/SDS/GMP/spec parsing, validation engine, vendor history, ML training and inference, Kimi integration, analyze pipeline | Auth, CRUD, decision, email |
| **Dev 3** | Decision engine and rules, threshold settings, Google SMTP, templates, email events, retry, decision/email audit events, NEEDS\_REVIEW resolution | Extraction, ML, CRUD, UI |
| **Dev 4** | React app, all screens, API client, auth handling, integration testing, Vercel/Render/Neon deployment, demo script | Backend business logic |

Dev 1 delivers the foundation first (hours 0-6) because everyone depends on models and auth.

## 11. Database Schema

All PKs are UUID (`gen_random_uuid()` / uuid4). Tenant tables carry `company_id` (FK companies.id, indexed). `created_at` and `updated_at` (timestamptz) on every table unless noted.

| Table | Key columns | Constraints / indexes |
| --- | --- | --- |
| companies | name, industry, settings (JSONB: decision thresholds, risk bands) | unique(name) |
| users | company\_id, email, password\_hash, full\_name, role, is\_active | unique(email); idx company\_id |
| vendors | company\_id, vendor\_name, company\_registration\_id, country, contact\_name, email, phone, address, industry, supplier\_category, is\_active, deleted\_at | unique(company\_id, vendor\_name) where not deleted; idx(company\_id, is\_active) |
| vendor\_contacts | company\_id, vendor\_id, name, email, phone, role, is\_primary | idx vendor\_id |
| raw\_materials | company\_id, name, code, category, description, specification (JSONB), required\_documents (JSONB list), active | unique(company\_id, code) |
| vendor\_materials | company\_id, vendor\_id, raw\_material\_id, is\_approved, approved\_at, approved\_by, notes | unique(vendor\_id, raw\_material\_id) |
| batches | company\_id, vendor\_id, raw\_material\_id, batch\_number, manufacturing\_date, expiry\_date, quantity, unit, price, expected\_delivery\_date, actual\_delivery\_date, status, failure\_reason, created\_by | unique(company\_id, vendor\_id, batch\_number); idx(company\_id, status), vendor\_id, raw\_material\_id |
| documents | company\_id, batch\_id, vendor\_id, document\_type, file\_name, file\_path, mime\_type, file\_size, uploaded\_by, processing\_status (PENDING/PROCESSING/PROCESSED/FAILED), extracted\_data (JSONB) | idx batch\_id |
| coa\_results | company\_id, batch\_id, document\_id, batch\_number, material, purity, moisture, heavy\_metals (JSONB), microbial\_parameters (JSONB), test\_date, manufacturing\_date, expiry\_date, laboratory, field\_status (JSONB: per-field OK/MISSING/NEEDS\_REVIEW) | idx batch\_id |
| certifications | company\_id, vendor\_id, document\_id, cert\_type (GMP/ISO/OTHER), certificate\_number, issued\_by, issue\_date, expiry\_date, status | idx(vendor\_id, cert\_type) |
| vendor\_performance | company\_id, vendor\_id, period\_start, period\_end, on\_time\_delivery\_rate, average\_lead\_time, price\_variance, capacity, incident\_count | idx vendor\_id |
| vendor\_quality\_history | company\_id, vendor\_id, batch\_id, outcome, purity, documentation\_completeness, incident\_flag, recorded\_at, is\_synthetic | idx vendor\_id |
| risk\_predictions | company\_id, batch\_id, risk\_score (0-100), risk\_probability (0-1), risk\_level, risk\_factors (JSONB), features (JSONB), model\_version, training\_data\_source, ai\_assessment (JSONB, Kimi output), ai\_status | idx batch\_id |
| validation\_results | company\_id, batch\_id, check\_name, category, mandatory, status (PASS/FAIL/MISSING/NEEDS\_REVIEW), expected, actual, message | idx batch\_id |
| approval\_decisions | company\_id, batch\_id, decision, decision\_source (RULES/MANUAL), reasons (JSONB), rule\_snapshot (JSONB), decided\_by, resolved\_reason | idx batch\_id |
| email\_events | company\_id, batch\_id, decision\_id, recipient, subject, email\_type, status (PENDING/SENT/FAILED), attempts, sent\_at, error\_message | idx(batch\_id), idx status |
| audit\_logs | company\_id, user\_id, action, entity\_type, entity\_id, metadata (JSONB), created\_at (no updated\_at) | idx(company\_id, created\_at), idx(entity\_type, entity\_id) |

**Relationships:** company 1-N users, vendors, raw\_materials, batches. Vendor N-M raw\_material via vendor\_materials. Batch N-1 vendor, N-1 raw\_material, 1-N documents, 1-N validation\_results, 1-1 current risk\_prediction, 1-N approval\_decisions (latest is current), 1-N email\_events. Document 0-1 coa\_results. Vendor 1-N certifications, performance and quality history.

**Material specification example (JSON):** parameters list with name, operator, value, unit, mandatory; plus max limits for moisture and heavy metals, storage requirements, and required document types. Example for L-Ascorbic Acid: purity >= 99 (mandatory), required documents COA, SDS, GMP. This is a company-configured internal specification, not a universal regulatory requirement. Other materials (Niacinamide, Hyaluronic Acid, Vitamin E, Retinol) use the same schema with no code change.

## 12. API Specification

Base path `/api`. All endpoints except register/login require `Authorization: Bearer <JWT>`. Lists accept `page` (default 1) and `page_size` (default 20, max 100) and return items, total, page, page\_size. Errors follow section 27.

| Method | URL | Owner | Notes |
| --- | --- | --- | --- |
| POST | /auth/register | Dev 1 | Body: company\_name, full\_name, email, password. Creates company and first user. 201 |
| POST | /auth/login | Dev 1 | Body: email, password. Returns access\_token, token\_type |
| GET | /auth/me | Dev 1 | Current user and company |
| GET/POST | /vendors | Dev 1 | Query: search, is\_active, page, page\_size |
| GET/PUT/DELETE | /vendors/{id} | Dev 1 | DELETE is soft delete |
| GET | /vendors/{id}/history | Dev 2 | Vendor history metrics |
| GET/POST | /raw-materials | Dev 1 | Query: search, active |
| GET | /raw-materials/{id} | Dev 1 | Includes specification |
| PUT | /raw-materials/{id} | Dev 1 | Update spec (small addition needed for configurable specs) |
| GET/POST | /vendor-materials | Dev 1 | Filter by vendor\_id, raw\_material\_id; POST links and sets is\_approved |
| PUT | /vendor-materials/{id} | Dev 1 | Toggle approval |
| GET/POST | /batches | Dev 1 | Filters: status, vendor\_id, raw\_material\_id, page |
| GET | /batches/{id} | Dev 1 | Batch plus latest summary fields (risk, decision) |
| POST | /documents/upload | Dev 1 | multipart: file, batch\_id, document\_type. 413 if too large |
| GET | /documents | Dev 1 | Filters: batch\_id, vendor\_id, document\_type |
| GET | /batches/{id}/documents | Dev 1 | Documents with processing\_status |
| POST | /batches/{id}/analyze | Dev 2 | Starts pipeline, returns 202 |
| GET | /batches/{id}/extraction | Dev 2 | coa\_results and certifications |
| GET | /batches/{id}/validation | Dev 2 | List of validation\_results |
| GET | /batches/{id}/risk | Dev 2 | Risk prediction and ai\_assessment |
| GET | /batches/{id}/decision | Dev 3 | Current decision, reasons, rule snapshot |
| POST | /batches/{id}/decision/resolve | Dev 3 | Body: decision (APPROVED/REJECTED), reason. Only from NEEDS\_REVIEW |
| GET/PUT | /settings/decision-rules | Dev 3 | Company thresholds |
| GET | /batches/{id}/emails | Dev 3 | Email events |
| POST | /emails/{id}/retry | Dev 3 | Retry FAILED email |
| GET | /audit-logs | Dev 1 | Filters: entity\_type, entity\_id, action, page |
| GET | /analytics/overview | Dev 1 | total\_vendors, total\_batches, approved, rejected, needs\_review, average\_risk\_score |
| GET | /analytics/risk-distribution | Dev 1 | Counts per risk level |
| GET | /analytics/risk-trend | Dev 1 | Query: days, interval; average risk per period |
| GET | /analytics/approval-trend | Dev 1 | Decisions per period by outcome |

Full request/response examples for each endpoint live in `API_CONTRACT.md`, generated from the OpenAPI spec, and owners update it with any change. Common error responses for every protected endpoint: 401, 422, 500; resource endpoints add 404; creates add 409.

## 13. Authentication

- Passwords hashed with bcrypt (passlib) or argon2; minimum 8 characters.
- JWT (HS256) signed with `JWT_SECRET`; claims: sub (user id), company\_id, exp (default 60 min).
- Dependency `get_current_user` validates the token, loads the user, rejects inactive users (401) and returns company\_id used by every query.
- Register creates company and user in one transaction; email must be unique (409).
- Responses never include password\_hash. Login and register write audit logs.

## 14. Vendor Management

Fields: vendor\_name, company\_registration\_id, country, contact\_name, email, phone, address, industry, supplier\_category, is\_active. Search matches name, country and category (case-insensitive). Soft delete sets deleted\_at and is\_active false; deleted vendors are hidden from lists but kept for history. Vendor detail shows supplier history summary from `/vendors/{id}/history`. Audit: created, updated, deleted.

## 15. Raw Material Management

Fields: name, code, category, description, specification (JSON), required\_documents, active. Seeded with L-Ascorbic Acid (code LAA-001, purity >= 99 mandatory, required documents COA, SDS, GMP). Specification is validated on write against a Pydantic schema so the validation engine can interpret any material generically. UI labels it 'Company specification'.

## 16. Batch Management

Batch belongs to one company, vendor and material; vendor must be active and (configurable warning) approved for that material. batch\_number unique per vendor. Status flow: RECEIVED -> PROCESSING -> VALIDATED -> PREDICTED -> APPROVED / REJECTED / NEEDS\_REVIEW; FAILED from any processing step. Dev 2 sets PROCESSING, VALIDATED, PREDICTED, FAILED; Dev 3 sets the three final statuses. Dev 1 provides `update_batch_status(db, batch_id, status, reason=None)` that all use.

## 17. Document Management

Dev 1 owns upload and metadata only. Accepted: PDF, PNG, JPG (MIME and magic-byte check). Max 10 MB. Filenames sanitized and stored as `uploads/{company_id}/{batch_id}/{uuid}_{safe_name}`. Types: COA, SDS, GMP, SPECIFICATION, TEST\_REPORT, COMPLIANCE, OTHER. New documents start with processing\_status PENDING. Dev 2 reads files via `document.file_path` and updates processing\_status and extracted\_data. Download endpoint is out of MVP scope.

## 18. AI/ML Pipeline

**Extraction (Dev 2).** PDF text via pdfplumber/pypdf; scanned PDFs and images get best-effort OCR (pytesseract, optional, P3), otherwise flagged NEEDS\_REVIEW. CSV/XLSX/DOCX read through pandas/openpyxl/python-docx where supplied. COA fields: batch\_number, material, purity, moisture, heavy\_metals, microbial\_parameters, test\_date, manufacturing\_date, expiry\_date, laboratory. Parsing is rule/regex based first; every extracted value must be traceable to the source text. Any field not found is stored as MISSING; unclear values as NEEDS\_REVIEW. Never guess.

**Vendor history (Dev 2).** Computed from batches, decisions, vendor\_quality\_history and vendor\_performance: previous\_batches, approval\_rate, rejection\_rate, average\_purity, purity\_variance, documentation\_completeness, delivery\_reliability, incident\_count, average\_lead\_time, price\_variance, capacity. The current batch's purity and price are compared to history (deviation in standard deviations when 3+ prior batches exist, else 'insufficient history').

**ML risk (Dev 2).** scikit-learn RandomForestClassifier (class\_weight balanced). Features: quality\_score, purity, purity\_variance, document\_completeness, certification\_status, delivery\_reliability, rejection\_rate, incident\_count, lead\_time, capacity, price\_variance, historical\_approval\_rate. Target: batch had a bad outcome (rejected or incident). Output: risk\_probability (predict\_proba), risk\_score = round(probability x 100), risk\_level by configurable bands (default LOW < 25, MEDIUM 25-50, HIGH 50-75, CRITICAL >= 75), and risk\_factors = top contributing features (feature importance times deviation from a healthy baseline) with readable text. Missing features use documented defaults and are listed in risk\_factors as data gaps. New vendors with no history are flagged 'insufficient history'.

**Synthetic data.** No real history exists at the hackathon, so `ml/synthetic_data.py` generates training data, the model is saved with `training_data_source = SYNTHETIC_DEV`, seeded vendor history rows have `is_synthetic = true`, and the UI shows a visible 'Model trained on synthetic development data' badge. Synthetic data is never described as real or production data.

## 19. Kimi K3 Integration

`services/kimi_service.py` exposes `explain(analysis: dict) -> dict`. Input is a plain dict built by a mapper: vendor, material, batch, validation results, vendor history, ML prediction and risk factors. Output keys: summary, key\_findings, risk\_factors, business\_impact, recommended\_actions, decision\_explanation.

Rules in the system prompt and enforced in code: explain only the provided facts; do not change the ML score or level; do not override validation results or decision rules; state 'not provided' for unknowns; no regulatory claims; return JSON only. The response is parsed and schema-validated; invalid output is retried once. On timeout or failure, a deterministic template explanation is stored with ai\_status = FALLBACK. Kimi never reads the database; its output is stored in risk\_predictions.ai\_assessment. The decision engine ignores Kimi output entirely. Key from `KIMI_API_KEY`.

## 20. Validation

Owner: Dev 2. Each check produces a row in validation\_results with check\_name, category, mandatory flag, status, expected, actual, message.

| Check | Rule |
| --- | --- |
| Specification parameters | Compare each configured parameter (for example purity >= 99): 99.3 PASS, 98.2 FAIL, missing = MISSING |
| Contaminant limits | Heavy metals and microbial values against configured limits only |
| COA consistency | COA batch\_number and material match the batch record |
| Document completeness | Each required\_documents type uploaded and processed |
| Certificate expiry | GMP/other certificates not expired at receipt date |
| GMP / SDS / test reports | Present, readable, issuer and dates identified |
| Batch information | Manufacturing and expiry dates present, expiry after manufacturing, not expired |
| Traceability | batch\_number, vendor, laboratory and test date present |
| Storage requirements | Configured storage requirement present in SDS or spec, else NEEDS\_REVIEW |

Output also includes a summary: counts of PASS/FAIL/MISSING, `mandatory_failed`, `critical_missing`, and `document_completeness` (0-1).

## 21. Decision Engine

Owner: Dev 3. `decide(db, batch_id) -> Decision` evaluated in this order (first match wins):

1. Any mandatory validation check FAIL -> **REJECTED**.
2. Any critical document or mandatory value MISSING (or ML prediction unavailable) -> **NEEDS\_REVIEW**.
3. Risk level LOW, all mandatory checks PASS and completeness >= threshold -> **APPROVED**.
4. Otherwise -> **NEEDS\_REVIEW**.

Configurable per company in `companies.settings` (defaults provided): risk bands, max risk level for auto-approval (default LOW), minimum document completeness (default 1.0), critical document types. The applied rule and settings are stored in `rule_snapshot` and `reasons` for explainability. Kimi is not an input. Decision rules and thresholds are company-configured business rules, never presented as regulatory requirements. NEEDS\_REVIEW items can be resolved manually (APPROVED or REJECTED) with a mandatory reason, stored as decision\_source MANUAL and audit-logged.

## 22. Email System

Owner: Dev 3. Google SMTP via smtplib with STARTTLS (host/port/user/password from env; Gmail app password). An email is sent after every decision to the batch creator and configured company QA recipients. Types: APPROVED, REJECTED, NEEDS\_REVIEW (Jinja2 templates in `templates/`). Content: vendor, material, batch number, risk score and level, validation summary, AI assessment (or fallback note), recommended actions, reference ID, timestamp. Every attempt creates/updates an email\_events row (recipient, subject, email\_type, status, sent\_at, error\_message, created\_at, attempts). Failures never affect the decision. Retry: 2 automatic retries with short backoff inside the background task, plus manual `POST /emails/{id}/retry`.

## 23. Audit Trail

Dev 1 provides `audit.log(db, company_id, user_id, action, entity_type, entity_id, metadata)`; all developers call it. Standard action names: USER\_REGISTERED, LOGIN, VENDOR\_CREATED/UPDATED/DELETED, BATCH\_CREATED, DOCUMENT\_UPLOADED, DOCUMENTS\_PROCESSED, VALIDATION\_COMPLETED, RISK\_PREDICTED, AI\_ASSESSMENT\_GENERATED, DECISION\_MADE, DECISION\_RESOLVED, EMAIL\_SENT, EMAIL\_FAILED. Records are append-only and company-scoped; metadata must not contain secrets or file contents.

## 24. Analytics

Dev 1 implements SQL aggregate queries (SQLAlchemy, no string-built SQL), always company-scoped; no hardcoded values. Overview: total vendors (active, not deleted), total batches, counts by final status, average risk score. Risk distribution: counts per risk level from the latest prediction per batch. Risk trend: average risk by day/week over a period. Approval trend: counts of APPROVED/REJECTED/NEEDS\_REVIEW per period. Empty data returns zeros and empty arrays.

## 25. Frontend Requirements

React (Vite) with React Router, a small API client with JWT handling, and Recharts for charts. Clean B2B dashboard layout with a sidebar.

| Screen | Content |
| --- | --- |
| Login/Register | Forms, validation, error display |
| Dashboard | KPI cards, risk distribution, risk trend, approval trend, recent batches, workflow stepper |
| Vendors | Table, search, pagination, add/edit modal |
| Vendor Details | Profile, linked materials and approval, history summary, recent batches |
| Raw Materials | List, create, specification viewer/editor |
| Batches | Table with filters (status, vendor, material), create batch |
| Batch Details | Info, documents with upload, extraction, validation table, risk, AI explanation, decision, emails, audit timeline, Analyze button |
| Documents | Cross-batch list with filters |
| Risk Assessment | Score gauge, level, factors, synthetic-data badge |
| Decision Result | Status badge, reasons, rule snapshot, resolve action for NEEDS\_REVIEW |
| Analytics | Charts for all four analytics endpoints |

Status colours: APPROVED green, REJECTED red, NEEDS\_REVIEW amber; risk levels LOW green to CRITICAL dark red. Batch Details polls every 3 s while status is PROCESSING. Show loading, empty and error states, and show MISSING/NEEDS\_REVIEW fields explicitly.

## 26. Security

- Secrets only from environment variables; none in source; `.env` git-ignored.
- bcrypt/argon2 hashing; JWT with expiry; inactive users blocked; hashes never returned.
- Tenant isolation: every query filters by company\_id from the token, never from the request body; cross-tenant access returns 404.
- File validation: allowed MIME + magic bytes, 10 MB limit, sanitized names, stored outside the web root.
- CORS restricted to `CORS_ORIGINS` / `FRONTEND_URL`.
- Pydantic validation on all inputs; SQLAlchemy ORM only (no string-built SQL).
- Audit logging of important operations; no PII or secrets in logs.
- Kimi prompts contain only the data needed for the explanation.

## 27. Error Handling

All errors return a JSON object with a single `error` key containing `code`, `message` and `details` (null when none). Global exception handlers convert HTTPException, validation errors and unhandled exceptions to this shape.

| HTTP | code |
| --- | --- |
| 400 | BAD\_REQUEST |
| 401 | UNAUTHORIZED |
| 404 | NOT\_FOUND |
| 409 | CONFLICT |
| 413 | FILE\_TOO\_LARGE |
| 422 | VALIDATION\_ERROR (details lists field errors) |
| 500 | INTERNAL\_ERROR (no stack trace to client) |

## 28. Environment Variables

`.env.example`: DATABASE\_URL, JWT\_SECRET, FRONTEND\_URL, CORS\_ORIGINS, KIMI\_API\_KEY, SMTP\_HOST, SMTP\_PORT, SMTP\_USERNAME, SMTP\_PASSWORD, SMTP\_FROM, SMTP\_FROM\_NAME (all empty values). Frontend: `VITE_API_URL`. Optional: JWT\_EXPIRE\_MINUTES, MAX\_UPLOAD\_MB, UPLOAD\_DIR. Real credentials are never committed.

## 29. Project Structure

```
backend/
  app/
    main.py
    core/        config.py, database.py, security.py, errors.py
    models/      one file per table group
    schemas/     Pydantic v2
    routers/     auth, vendors, raw_materials, vendor_materials, batches,
                 documents, analysis, decisions, emails, analytics, audit
    services/    extraction, validation, history, kimi_service,
                 decision_service, email_service, audit
    ml/          synthetic_data.py, train.py, predict.py, model.joblib
    templates/   approved.html, rejected.html, needs_review.html
    tests/
  alembic/
  requirements.txt  .env.example  README.md  API_CONTRACT.md
frontend/
  src/ components/ pages/ services/ hooks/ layouts/
```

Branching: one feature branch per developer, merged to main via PR. Dev 1 owns `models/` and migrations to avoid conflicts; others request schema changes through Dev 1.

## 30. Deployment

- **Backend (Render):** start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`; build runs `pip install -r requirements.txt` and `alembic upgrade head`; env vars set in Render. Uploaded files on Render's ephemeral disk are acceptable for the demo (lost on redeploy; add a persistent disk if needed). Health endpoint `GET /health`.
- **Database (Neon):** pooled connection string with `sslmode=require`.
- **Frontend (Vercel):** Vite build, `VITE_API_URL` points to Render.
- Render free-tier cold starts: hit /health before the demo.
- Kimi and SMTP are external services configured by env vars.

## 31. Testing Strategy

- **Dev 1:** pytest with a test DB: auth, tenant isolation (company A cannot read company B), CRUD, soft delete, upload validation.
- **Dev 2:** unit tests for COA parsing on sample documents, validation edge cases (99.3 PASS, 98.2 FAIL, missing), history metrics, ML smoke test, Kimi with mocked responses including malformed JSON.
- **Dev 3:** table-driven decision tests for every rule branch; SMTP mocked (success, failure, retry).
- **Dev 4:** manual end-to-end demo checklist and basic component checks.
- **Integration:** full demo scenario run on the deployed stack before submission.

## 32. Hackathon MVP Priorities

| Priority | Scope |
| --- | --- |
| P0 | FastAPI setup, database, auth, vendors, raw materials, batches |
| P1 | Document upload, extraction, validation, ML risk, Kimi, deployment |
| P2 | Decision engine, email, dashboard, analytics, audit trail |
| P3 | Extra tests, UI polish, more analytics, OCR, future integrations |

Fallbacks if time runs short: pre-seeded demo documents and vendor history; Kimi fallback template; email shown as a preview if SMTP fails; analytics limited to overview and risk distribution.

## 33. Demo Scenario

Company: a Vitamin C skincare manufacturer. Vendor: ABC Chemicals. Material: L-Ascorbic Acid with the company specification purity >= 99%. Batch: VC-001 with COA, SDS and GMP documents.

1. Log in; show seeded vendor ABC Chemicals and L-Ascorbic Acid (approved link).
2. Create batch VC-001 and upload the three documents.
3. Click Analyze; watch status move PROCESSING -> VALIDATED -> PREDICTED.
4. Show extracted COA values (purity 99.3%, other fields, any MISSING flagged).
5. Show validation results (purity PASS) and ABC Chemicals history.
6. Show risk score and level with the synthetic-data badge, then the Kimi explanation.
7. Show the decision (expected APPROVED for the clean batch) and the received email.
8. Upload a second batch VC-002 with purity 98.2% to show REJECTED, and one with a missing GMP certificate to show NEEDS\_REVIEW.
9. Show the dashboard charts and the audit trail.

Seed data and sample documents are prepared by Dev 1 and Dev 2 and clearly marked as demo data.

## 34. Future Scope

OCR for scanned COAs with human confirmation, supplier portal for document submission, object storage (S3) for files, vendor scorecards and audits, certificate expiry reminders, model retraining on real outcomes, role-based permissions, ERP integrations, multi-language documents.

## 35. Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| No real historical data | Synthetic data, clearly labelled; design allows retraining |
| Extraction errors on varied COA formats | Rule-based parsing, MISSING/NEEDS\_REVIEW instead of guessing, sample-document tests |
| Kimi unavailable or malformed output | Schema validation, retry, template fallback; decision unaffected |
| Kimi hallucination | Strict prompt, structured input only, not used in decisions |
| SMTP blocked / Gmail limits | App password, retry, failure tracking, demo preview |
| Render cold start and ephemeral disk | Warm-up before demo, seeded files, optional persistent disk |
| Integration conflicts between 4 developers | Contracts in section 36, early skeleton, daily merges |
| Tenant data leak | company\_id from token only, isolation tests |
| Time overrun | Priority levels and fallbacks in section 32 |

## 36. Developer-to-Developer Integration Contracts

**Dev 1 provides to all:** SQLAlchemy models (merged first), `get_current_user` and `get_db` dependencies, `update_batch_status(db, batch_id, status, reason=None)`, `audit.log(...)`, the standard error classes (NotFoundError, ConflictError, etc.), and seed data. Schema changes only via Dev 1 Alembic migrations.

**Dev 1 -> Dev 2:** documents rows with PENDING status and readable `file_path`; batch, vendor and material records; the `raw_materials.specification` JSON schema (agreed on day 1).

**Dev 2 -> Dev 3:** after the pipeline writes `validation_results` and `risk_predictions` it calls `decision_service.decide(db, batch_id)`. Dev 3 reads validation\_results (status, mandatory), the validation summary (`mandatory_failed`, `critical_missing`, `document_completeness`), and risk\_predictions (risk\_score, risk\_level; ai\_assessment only for email text). Contract: risk\_level is one of LOW/MEDIUM/HIGH/CRITICAL; check status is PASS/FAIL/MISSING/NEEDS\_REVIEW.

**Dev 2 pipeline order:** set PROCESSING -> extract -> save coa\_results/certifications -> validate -> set VALIDATED -> history -> predict -> Kimi -> set PREDICTED -> call decide. On exception set FAILED with failure\_reason.

**Dev 3 -> Dev 1/4:** sets final batch status via `update_batch_status`; writes approval\_decisions and email\_events; exposes the decision and email endpoints in section 12. Email send failure never changes the decision.

**Dev 4 consumes:** only documented endpoints in `API_CONTRACT.md`; batch status polling via `GET /api/batches/{id}`; enum values (statuses, risk levels, document types, check statuses) fixed in a shared ENUMS section of the contract. Any contract change is announced to all developers and updated in `API_CONTRACT.md` in the same PR.

**Day-1 agreements (before coding):** enum values, specification JSON schema, validation\_results and risk\_predictions column definitions, ai\_assessment JSON keys, error format, and the `/analyze` and `decide` function signatures.
