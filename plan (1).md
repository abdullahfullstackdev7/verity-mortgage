# Mortgage/Loan Underwriting Document Automation - Development Plan

## Project Overview

This project is a full-stack underwriting automation platform that ingests a loan applicant's document packet (pay stub, bank statement, W-2, ID), extracts structured financial data from those documents, cross-verifies the extracted numbers against the applicant's stated application data, flags discrepancies with tolerance-based rules, and produces an underwriter-ready summary with a routing recommendation, all backed by an auditable decision trail. The system is built on real, publicly available HMDA (Home Mortgage Disclosure Act) loan application data for ground-truth realism, paired with synthetically generated but visually authentic supporting documents, since real applicant financial documents are private and cannot legally be used for a demo or training pipeline. The result is a working reference implementation of the intake-to-decision workflow used by real mortgage technology platforms, built entirely on free and open-source tooling with a professional, production-grade web interface.

## Problem Statement

Mortgage underwriting today is slow and error-prone because loan officers and underwriters must manually read pay stubs, bank statements, and W-2s, mentally cross-check every number against what the applicant declared on the application, and write up a narrative justification before a decision can move forward, a process that does not scale, is inconsistent across reviewers, and leaves discrepancies (understated income, mismatched employer details, inconsistent deposit patterns) to be caught late or missed entirely. This project solves that by automating the document intake, extraction, and cross-verification steps with a rules-based and AI-assisted pipeline, producing a structured, evidence-backed underwriter summary and an auditable routing decision (auto-approve, refer to underwriter, or flag for manual review) in place of a manual, opaque review process, while keeping the design deliberately frugal on paid AI usage so it remains fully runnable on free-tier infrastructure.

---

## Tech Stack Summary

| Layer | Technology |
|---|---|
| Backend language | Python 3.11+ |
| Backend framework | FastAPI |
| Database | PostgreSQL 16 with the pgvector extension |
| ORM / migrations | SQLAlchemy 2.0 + Alembic |
| Auth | JWT (access + refresh tokens), bcrypt password hashing, role-based access control |
| Document generation | Jinja2, WeasyPrint, Faker |
| OCR / extraction | Tesseract OCR / PaddleOCR (open source), Pydantic for schema validation |
| Embeddings | Open-source HuggingFace sentence-transformers model (e.g. `BAAI/bge-small-en-v1.5` or `sentence-transformers/all-MiniLM-L6-v2`), run locally, no paid API |
| LLM providers | Groq (`openai/gpt-oss-20b`) as primary, Google Gemini (`gemini-2.5-flash` or `gemini-2.0-flash`) as fallback, both on free tiers |
| Frontend | React 18 + TypeScript, Tailwind CSS, shadcn/ui component library |
| State machine | `python-statemachine` or a hand-rolled enum-based transition table |
| Testing | Pytest (backend), Vitest + React Testing Library (frontend) |
| Containerization | Docker + Docker Compose |
| Deployment (free tier) | Render / Railway / Fly.io for backend, Vercel / Netlify for frontend, Supabase or Neon (free Postgres with pgvector support) for database |

---

## Dataset Section

### Source

Use the official HMDA Modified Loan Application Register (LAR) data published by the Consumer Financial Protection Bureau through the Federal Financial Institutions Examination Council (FFIEC) HMDA Platform.

- HMDA Data Browser and CSV export tool: `https://ffiec.cfpb.gov/data-browser/`
- Modified LAR data publication page (institution-level and combined files): `https://ffiec.cfpb.gov/data-publication/modified-lar`
- Beginner's Guide to Accessing and Using HMDA Data (CFPB reference document, useful for field definitions)

### How to obtain a usable subset

1. Go to the HMDA Data Browser.
2. Filter by a recent filing year (most recent full year available) and by one or two states to keep the file size manageable for a demo (a national file can run into millions of rows).
3. Use the "Create export" or "Download data" option and export as CSV.
4. Confirm the export includes at minimum: loan amount, applicant income, debt-to-income ratio (if present), property value, loan purpose, action taken (the approval/denial outcome field), and a derived applicant identifier fields.
5. Keep the raw export untouched in the data folder for traceability, and do all cleaning in a separate processing script.

### Fields to use

- `income` (reported annual income, in thousands in the raw file, convert to full dollars)
- `loan_amount`
- `property_value`
- `debt_to_income_ratio` (may be a banded string in some years, normalize to a numeric midpoint)
- `action_taken` (map codes to approved / denied / other for the ground-truth outcome label)
- `derived_loan_product_type`, `loan_purpose`, `occupancy_type` for realism in generated documents

### Data folder structure

```
/data
  /raw
    /hmda
      hmda_lar_<year>_<state>.csv        (untouched original export)
  /processed
    applicants.parquet                   (cleaned, deduplicated, typed HMDA sample)
    applicants_sample_demo.parquet       (small curated subset, ~500-1000 rows, used to seed the live demo)
  /documents
    /generated
      /<applicant_id>
        paystub.pdf
        bank_statement.pdf
        w2.pdf
        id_card.pdf
    /degraded
      /<applicant_id>                    (scan-degraded copies for OCR stress testing)
  /policy_guidelines
    underwriting_guidelines.md           (short reference corpus used for the RAG-based narrative step, see Phase 7)
  /templates
    paystub_template.html
    bank_statement_template.html
    w2_template.html
```

Keep `/data/raw` read-only after the initial download. All downstream generation scripts read from `/data/processed` and write into `/data/documents`. The `applicants_sample_demo.parquet` subset is what powers the seeded, browsable demo cases in the deployed application so the product looks like it is serving real users rather than an empty database.

### Licensing note for the README

State clearly that HMDA data is public domain government data, and that all pay stubs, bank statements, and W-2s in the repository are synthetically generated from that data using Faker and template rendering, not real documents belonging to any person.

---

## Phase-Wise Development Plan

### Phase 0: Environment and Repository Setup

- Initialize a monorepo with `/backend` and `/frontend` directories, plus the `/data` structure above.
- Set up Python virtual environment, `pyproject.toml` with dependencies pinned (FastAPI, SQLAlchemy, Alembic, Pydantic v2, python-jose or pyjwt, passlib[bcrypt], sentence-transformers, pgvector, weasyprint, jinja2, faker, pytesseract or paddleocr, httpx, python-statemachine).
- Set up Docker Compose with three services: `postgres` (using the `pgvector/pgvector:pg16` image), `backend`, `frontend`.
- Create `.env.example` covering `DATABASE_URL`, `JWT_SECRET_KEY`, `GROQ_API_KEY`, `GEMINI_API_KEY`, `ENV`, `CORS_ORIGINS`. Never commit real keys.
- Set up pre-commit hooks: black, ruff, mypy for backend; eslint, prettier for frontend.
- Deliverable: a running `docker-compose up` that boots an empty backend, empty frontend, and a Postgres instance with the pgvector extension enabled via a bootstrap SQL script (`CREATE EXTENSION IF NOT EXISTS vector;`).

### Phase 1: Dataset Acquisition and Preparation

- Write `scripts/download_hmda.py` with instructions (manual download link plus a note that FFIEC requires the browser export, not a direct API pull) and a loader that reads the raw CSV.
- Write `scripts/clean_hmda.py` to:
  - Parse and type-cast income, loan amount, property value, DTI.
  - Drop rows with nulls in required fields.
  - Map `action_taken` codes to a simplified outcome label.
  - Generate a synthetic but stable `applicant_id` (UUID) per row.
  - Output `applicants.parquet` and a smaller `applicants_sample_demo.parquet` (random stratified sample across approved/denied/refer outcomes).
- Write unit tests validating schema, ranges, and no PII leakage (the HMDA file itself contains no names or account numbers, confirm this holds after processing).
- Deliverable: reproducible, versioned processed dataset files checked into `/data/processed` (or regenerated by a single script on setup).

### Phase 2: Synthetic Document Generation

- Build three Jinja2 HTML templates styled after public reference layouts (IRS blank W-2 layout, a generic ADP-style pay stub layout, a generic bank statement layout). Do not copy any copyrighted proprietary template, build original layouts inspired by the public structure and field names.
- Write `generators/paystub_generator.py`, `generators/bank_statement_generator.py`, `generators/w2_generator.py`, each taking one HMDA-derived applicant record plus Faker-generated identity fields (name, address, employer name, SSN-format placeholder, dates) and rendering the HTML template with real derived numbers.
- Use WeasyPrint to render each HTML template to PDF.
- Discrepancy injection logic: for roughly 15-20 percent of applicants, deterministically alter one document-side figure (for example, annualized pay stub income set to be 15-30 percent below or above the stated HMDA income) so the mismatch is reproducible and traceable. Store the "ground truth" injected discrepancy in a separate `discrepancy_ground_truth.parquet` file so the extraction and verification pipeline can later be scored against it.
- Optional scan realism pass: use Pillow/OpenCV to apply slight rotation, noise, and JPEG re-compression to a subset of generated PDFs (render to image, degrade, save back to `/data/documents/degraded`).
- Optional OCR robustness validation: separately test the extraction pipeline against a small sample from a public scanned-document dataset (RVL-CDIP or FUNSD/SROIE) to confirm the OCR and field-parsing logic is not overfit to the custom templates. This is a validation step, not part of the main demo data.
- Deliverable: a document generation CLI (`python -m generators.build_all --count 1000`) that populates `/data/documents/generated` and `/data/documents/degraded` from the processed HMDA sample.

### Phase 3: Database Design

Design the PostgreSQL schema (with pgvector enabled) around these core tables:

- `users` (id, email, hashed_password, role [loan_officer, underwriter, admin], created_at)
- `applicants` (id, name, address, employer_name, hmda_source_id, stated_income, stated_loan_amount, stated_property_value, stated_dti, created_at)
- `cases` (id, applicant_id, status [submitted, documents_pending, under_review, approved, referred, denied], assigned_underwriter_id, created_at, updated_at)
- `documents` (id, case_id, doc_type [paystub, bank_statement, w2, id], file_path, uploaded_at, ocr_status)
- `extracted_fields` (id, document_id, field_name, extracted_value, confidence_score, raw_text_snippet)
- `discrepancies` (id, case_id, field_name, stated_value, document_value, variance_pct, severity, source_document_id)
- `case_summaries` (id, case_id, narrative_text, recommendation, generated_by_model, token_count, created_at)
- `audit_log` (id, case_id, actor, action, rule_or_evidence, created_at)
- `policy_chunks` (id, source_doc, chunk_text, embedding vector(384)) for the RAG-based narrative step
- `document_embeddings` (id, document_id, field_name, value_text, embedding vector(384)) for fuzzy semantic matching of noisy OCR text (for example matching "ACME CORP" to "ACME Corporation")

Use pgvector's `vector` column type with an IVFFlat or HNSW index for the two embedding tables. Choose 384 dimensions to match the chosen small HuggingFace embedding model.

- Write Alembic migrations for all tables.
- Deliverable: a fully migrated schema with seed data loaded from the processed HMDA sample so the application has realistic cases on first run.

### Phase 4: Backend API Foundation (FastAPI)

- Project layout: `app/api/routes`, `app/core` (config, security), `app/models`, `app/schemas`, `app/services`, `app/db`.
- Implement authentication: registration (admin-created accounts only, no public signup, since this mirrors an internal underwriting tool), login issuing JWT access and refresh tokens, password hashing with bcrypt, refresh token rotation.
- Implement role-based access control middleware/dependency: loan officers can create cases and upload documents; underwriters can view assigned cases, override recommendations, approve/deny; admins manage users.
- Implement case CRUD endpoints: create case, list cases (with filters by status), get case detail, update case status.
- Implement document upload endpoint: validate file type (PDF only), validate file size limit, store to disk or object storage, create a `documents` row with status `pending_ocr`.
- Implement pagination, consistent error schema, and structured logging (JSON logs) across all routes.
- Deliverable: OpenAPI docs auto-generated at `/docs`, full test coverage on auth and case CRUD with Pytest.

### Phase 5: Extraction Pipeline

- Primary extraction path (no LLM tokens spent): run Tesseract or PaddleOCR on each uploaded PDF page, then apply deterministic regex and layout-anchor parsing per document type (pay stub: gross pay, pay period, employer name; bank statement: account balances, deposit lines; W-2: box 1 wages, employer EIN/name) to populate `extracted_fields`.
- Fallback extraction path (LLM-assisted, used only when OCR confidence is below a threshold or a required field is missing after regex parsing): send only the OCR text (not the raw image, to save tokens) to the LLM with a strict instruction to return JSON matching a Pydantic schema for that document type. Validate the LLM response against the Pydantic model, reject and log if it fails validation.
- Use the chosen HuggingFace sentence-transformers model to embed key extracted text values and store them in `document_embeddings`, enabling fuzzy matching (for example employer name spelled slightly differently between the application and the pay stub) via cosine similarity instead of exact string comparison.
- Deliverable: an extraction service callable per document, idempotent (re-running on an already-processed document is a no-op unless forced), with confidence scores stored per field.

### Phase 6: Cross-Verification and Rules Engine

- Pure Python, deterministic, no LLM calls in this phase.
- Compare each extracted field against the corresponding stated application value using field-specific tolerance rules (for example income within 10 percent, employer name similarity above a cosine-similarity threshold using the embeddings from Phase 5, bank deposit total within a percentage band of stated income annualized over the statement period).
- Compute the debt-to-income ratio from extracted and stated figures and compare against the HMDA-stated DTI.
- Any field outside tolerance is written to the `discrepancies` table with the two conflicting values, the variance percentage, a severity level (minor, major), and the source document reference.
- Deliverable: a rules engine module with unit tests covering clean cases, minor-flag cases, and major-mismatch cases, matching the ground-truth discrepancy labels generated in Phase 2.

### Phase 7: LLM-Assisted Underwriter Summary (Token-Minimized)

- Design goal: exactly one LLM call per case for the full narrative and recommendation, never one call per field or per document.
- Build a provider abstraction layer (`llm/provider.py`) with a common interface `generate_summary(prompt) -> text`, implemented by a Groq adapter (`openai/gpt-oss-20b`) and a Gemini adapter (`gemini-2.5-flash`).
- Routing logic: attempt Groq first; on a 429 rate-limit response or provider error, automatically fall back to Gemini, and vice versa; log which provider served each request in `case_summaries.generated_by_model` for transparency.
- Prompt construction: never send full document text or full application data. Send only the applicant's key figures, the list of flagged discrepancies (field, stated value, document value, variance), and the DTI, in a compact structured format.
- Retrieval-augmented context: embed a short internal underwriting guidelines corpus (`/data/policy_guidelines/underwriting_guidelines.md`) once at startup into `policy_chunks` using the HuggingFace embedding model, then at request time retrieve only the top 1-2 most relevant guideline chunks by cosine similarity against the case's discrepancy summary, and include only those chunks in the prompt instead of the full guideline document. This keeps prompt size small while giving the narrative a grounded policy citation.
- Cache the generated narrative in `case_summaries` so reloading a case in the UI never triggers a repeat LLM call; only regenerate if the underlying discrepancies change.
- Output format: require the model to return the narrative plus a recommendation label (approve, refer, deny) as structured JSON, validated with Pydantic before saving.
- Deliverable: a summary generation service with automatic provider failover, a single deterministic prompt template, and full token accounting logged per case.

### Phase 8: Decision Routing and Audit Trail

- Implement the case state machine: `submitted -> documents_pending -> under_review -> approved | referred | denied`, using `python-statemachine` or an equivalent explicit transition table with guarded transitions (a case cannot move to `under_review` until all required documents are present).
- Routing rules: no discrepancies and no major flags auto-transitions to `approved` with the recommendation logged; minor flags route to `referred` with the summary pre-filled for a human underwriter; any major mismatch forces `under_review` with a mandatory manual decision, blocking auto-approval.
- Every transition writes an entry to `audit_log` capturing the actor (system or user id), the action, and the specific rule or evidence (discrepancy id, threshold breached) that triggered it.
- Deliverable: an endpoint for underwriters to accept or override the system recommendation, with the override reason mandatory and stored in the audit log.

### Phase 9: Frontend - Public Marketing Site

Build a professional, Fortune 100-style public-facing site as the entry point, with authenticated functionality behind login.

- Pages: Home, Solutions/Product, How It Works, Security and Compliance, About, Contact.
- Home page structure: a strong hero section with a clear value proposition headline and subheadline, a primary call-to-action, a secondary "Login" button/hyperlink in the top navigation bar leading to the authentication screen, a section showcasing the intake-to-decision workflow as a visual step sequence, a metrics/trust-bar section (for example "Documents processed", "Average review time reduced"), a security and compliance callout section, and a footer with standard corporate sections (Company, Product, Legal, Contact).
- Visual design: use a restrained, professional palette (navy/charcoal primary with a single accent color), a serif or high-quality sans display font for headings paired with a clean sans body font, generous white space, consistent 8px spacing scale, subtle shadows and rounded corners on cards, no default browser styling left unstyled.
- Imagery: use professional, license-free stock photography (Unsplash or Pexels, both free for commercial use) for hero and section imagery, plus custom-built SVG/icon illustrations for the workflow diagram rather than screenshots, since screenshots of a not-yet-built product would look unpolished.
- Copywriting: write real, benefit-driven marketing copy (not lorem ipsum) for every section, in the tone of an enterprise fintech vendor.
- Login access: a persistent "Login" link/button in the header on every public page, routing to `/login`, which is the gateway to the authenticated underwriter application described in Phase 10.
- Deliverable: a fully responsive, production-quality marketing site built with React, TypeScript, Tailwind CSS, and shadcn/ui components, deployable as a static build.

### Phase 10: Frontend - Authenticated Underwriting Application

- Login/auth screens: email/password login form with validation and error states, calling the backend JWT endpoints, storing tokens securely (httpOnly cookie preferred over localStorage for the access token where the deployment target allows it).
- Underwriter queue view: a data-table-style dashboard listing all cases with status badges, applicant name, loan amount, flag count, and assigned underwriter, with filtering and sorting, styled to resemble a real loan origination system (LOS) dashboard.
- Case detail view: a two-pane layout showing document previews (rendered PDFs) side by side with the corresponding extracted and flagged fields, a dedicated "Why this was flagged" panel listing each discrepancy with the stated value, the document value, the variance, and the source document, and the LLM-generated narrative summary with its recommendation clearly displayed.
- Decision panel: buttons to approve, refer, or deny, with a mandatory override-reason field when the underwriter disagrees with the system recommendation, and a visible audit trail of prior actions on the case.
- Role-aware UI: loan officers see case creation and document upload screens; underwriters see the review queue and decision tools; admins see user management.
- Deliverable: a fully functional authenticated application connected to the backend API, covering the entire submitted-to-decision workflow end to end.

### Phase 11: Data Security, Authentication, and Authorization

- Enforce HTTPS in all non-local environments; set `Secure`, `HttpOnly`, `SameSite=Strict` on auth cookies.
- Password policy: minimum length and complexity enforced server-side, bcrypt hashing with an appropriate work factor.
- JWT access tokens short-lived (15-30 minutes), refresh tokens longer-lived and rotated on use, with a revocation list table for logout/compromise handling.
- Role-based authorization enforced at the API layer on every protected route, not just hidden in the UI.
- Input validation on every endpoint via Pydantic schemas; strict file-type and file-size validation on document uploads; reject any file that is not a valid PDF by content inspection, not just extension.
- Rate limiting on the login endpoint to slow brute-force attempts.
- Sensitive fields (stated income, account-derived figures) stored with field-level encryption at rest using PostgreSQL's `pgcrypto` extension where practical, since this data mirrors real PII even though it is synthetic in this project.
- CORS locked down to the known frontend origin(s) only.
- Secrets management: all API keys and the JWT signing secret loaded from environment variables, never committed, with `.env` in `.gitignore`.
- Full audit logging of every state-changing action, as defined in Phase 8.
- Deliverable: a documented security checklist in the README, and automated tests confirming unauthorized and cross-role requests are rejected.

### Phase 12: Testing and Quality Assurance

- Backend: Pytest unit tests for the rules engine, extraction schema validation, state machine transitions, and auth/authorization; integration tests hitting a test database via Docker Compose.
- Frontend: Vitest and React Testing Library for component tests, plus a small set of end-to-end tests (Playwright, free and open source) covering login, case review, and decision submission.
- Load a full demo dataset (the `applicants_sample_demo.parquet` set plus its generated documents) into a staging environment and manually verify the clean/minor/major discrepancy distribution matches the ~80/15-20 split defined in Phase 2.
- Deliverable: a CI workflow (GitHub Actions, free for public and limited private use) running lint, type-check, and the full test suite on every pull request.

### Phase 13: Deployment

- Backend: containerize with Docker, deploy to a free-tier host such as Render or Railway.
- Database: use a free-tier managed Postgres with pgvector support, such as Supabase or Neon.
- Frontend: deploy the static build to Vercel or Netlify free tier.
- Environment configuration per environment (local, staging) with separate `.env` files and separate database instances.
- Seed the deployed database with the demo dataset on first deploy so the live application looks fully populated for a demo audience rather than empty.
- Deliverable: a live, publicly reachable demo URL with seeded data, a working login flow, and a fully functional case review workflow.

### Phase 14: Documentation

- Write a comprehensive `README.md` at the repository root covering:
  - Project overview and problem statement (concise, professional language).
  - Architecture diagram (can be a simple Mermaid diagram rendered in the README) showing the intake-to-decision flow.
  - Full tech stack list with versions.
  - Setup instructions: prerequisites, environment variable configuration, `docker-compose up` instructions, database migration commands, dataset download and generation steps.
  - A clear, upfront explanation that the underlying loan application figures come from the public HMDA dataset and that the supporting documents are synthetically generated and linked to that data, with the reasoning that real applicant financial documents cannot legally be used, stated plainly rather than defensively.
  - API documentation reference (link to the auto-generated `/docs` endpoint).
  - Screenshots of the marketing site and the underwriter application.
  - A section on the token-minimization design and the dual-provider (Groq and Gemini) failover strategy.
  - A security overview summarizing the measures from Phase 11.
  - License section and contribution guidelines.
- Keep the README language precise, factual, and professional throughout, avoiding casual or informal phrasing.
- Deliverable: a README that lets a new developer clone the repository, follow the steps in order, and have a fully working local instance with seeded demo data, without needing to ask a follow-up question.
