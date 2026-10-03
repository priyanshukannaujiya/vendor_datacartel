# VendorIQ Decision and Email Module

This module is integrated into the shared FastAPI backend; it is not a separate
service. The decision route consumes the validation, ML prediction, and Kimi
assessment persisted by the existing batch pipeline.

## Decision rules

`POST /api/batches/{batch_id}/decision` loads the batch intelligence produced by
`POST /api/batches/{batch_id}/process` and
`POST /api/batches/{batch_id}/predict-risk`. It requires those pipeline results
to exist. It derives validation outcomes, specification checks, and document
completeness from the stored assessment, applies company thresholds from the
request, persists the decision, updates the batch status, and then creates an
email event.

Optional JSON request properties:

- `company_id`: nullable company reference until the host application has a
  company model.
- `company_thresholds.mandatory_validation_checks`: validation check names
  that must pass.
- `company_thresholds.material_specification_checks`: names identifying
  configured material specification checks. Defaults match the checks emitted
  by the current validation service.
- `company_thresholds.critical_document_types`: missing document types that
  require manual review.
- `company_thresholds.minimum_document_completeness`: company-configured ratio
  from `0` to `1` (example default `1.0`).
- `company_thresholds.max_approval_risk_score`: company-configured score from
  `0` to `100` (example default `25`).
- `company_thresholds.approval_risk_levels`: labels eligible for automatic
  approval (example default `["LOW"]`).

These are configurable company policies, not universal regulatory requirements.
A failed material specification or configured mandatory validation check is
rejected. Missing documents, uncertain checks, incomplete validation, or risk
outside company thresholds require review. Automatic approval requires
validation and configured thresholds to pass.

## Google SMTP setup

Set these variables in the combined backend's Render environment. Never commit
`.env` or expose SMTP secrets to the frontend. The root `.env.example` lists
the names without real credentials.

| Variable | Value |
| --- | --- |
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USERNAME` | Authenticated Google account address |
| `SMTP_PASSWORD` | Google App Password, not the account password |
| `SMTP_FROM` | Verified sender address |
| `SMTP_FROM_NAME` | `VendorIQ` |

Enable Google's 2-Step Verification and create a Google App Password for the
mail account. The backend sends over STARTTLS and includes both plain text and
HTML alternatives. Credentials are not logged.

## Receiving supplier PDF replies

The backend can optionally poll the same Google mailbox over IMAP. Enable IMAP
for the Google account, then set these variables in the Render backend
environment (or local backend `.env`):

| Variable | Value |
| --- | --- |
| `IMAP_ENABLED` | `true` |
| `IMAP_HOST` | `imap.gmail.com` |
| `IMAP_PORT` | `993` |
| `IMAP_USERNAME` | Inbox address; defaults to `SMTP_USERNAME` |
| `IMAP_PASSWORD` | Google App Password; defaults to `SMTP_PASSWORD` |
| `IMAP_FOLDER` | `INBOX` |
| `IMAP_POLL_INTERVAL_SECONDS` | Poll interval, default `120` (minimum `30`) |
| `IMAP_LOOKBACK_DAYS` | How far back a sent request may be replied to; default `30` |

The receiver accepts PDF attachments only from the recipient of a previously
sent `DOCUMENT_REQUEST` email within the lookback window, and requires the
original batch number in the reply subject. It searches only those known sender
addresses and does not crawl the whole inbox. It stores the attachment against that batch, records an
`Email Received` audit event, and extracts embedded PDF text using the existing
document parser. COA/SDS/GMP document types are inferred from the attachment
filename. Duplicate messages are idempotent. Attachments larger than
`MAX_UPLOAD_MB` are rejected; if a reply has only rejected or unsupported
attachments it remains unread for operator follow-up. Unrelated unread messages
are not opened or marked read, and a mailbox UID checkpoint prevents rescanning
the same messages on every poll.

This is text extraction, not OCR: image-only scanned PDFs are stored as
`NEEDS_REVIEW` because no OCR engine is configured. The background receiver
runs in the FastAPI process; keep a single backend instance polling a given
mailbox to avoid concurrent pollers.

## Templates, storage, and retry

Gmail-compatible inline-CSS templates are in `app/templates/emails/`:
`approved.html`, `rejected.html`, and `needs_review.html`.

- `POST /api/batches/{batch_id}/decision` returns the decision, risk score,
  reason, recommended actions, reference ID, and delivery status.
- `POST /api/email-events/{event_id}/retry` retries only `FAILED` messages.

`batch_decisions`, `email_events`, and `audit_events` are SQLAlchemy models
registered with the shared application's `Base.metadata`. Email event records
retain their rendered message for retries and store provider `GOOGLE_SMTP`,
status, timestamps, and any delivery error. The current host project creates
tables from metadata for local development; production schema changes should be
captured in the team's migration workflow before deployment.

The decision is committed before attempting SMTP delivery. A send failure
sets the event to `FAILED` and leaves the decision and batch status intact.
Retry atomically claims a failed event before sending, preventing concurrent
retry requests from sending the same event twice.

## Audit events

The inbound email receiver records `Email Received` and `Documents Processed`.
The existing batch process route records `Documents Processed` and
`Validation Completed`. The prediction route records `Risk Predicted` and,
when Kimi succeeds, `Kimi Assessment Generated`. The decision route records
`Decision Made` and successful email delivery records `Email Sent`.
The inbox receiver is opt-in and must be enabled using the IMAP environment
variables before it will receive email attachments.

## Tests

Run `pytest`. Tests cover all decision outcomes, SMTP STARTTLS and failure,
decision persistence when sending fails, email event storage, inbound sender
matching, PDF extraction, duplicate handling, and retry.
