"""Receive supplier PDF replies from a configured Gmail inbox."""

from __future__ import annotations

import hashlib
import imaplib
import logging
import re
import threading
from datetime import datetime, timedelta, timezone
from email import message_from_bytes
from email.header import decode_header
from email.policy import default
from email.utils import parseaddr
from pathlib import Path
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal, get_engine
from app.models.batch import Batch
from app.models.decision import AuditEvent, EmailEvent
from app.models.document import Document
from app.services.audit_service import record_audit_event
from app.services.document_service import document_service
from app.schemas.document import DocumentType

logger = logging.getLogger(__name__)

_stop_event = threading.Event()
_worker: Optional[threading.Thread] = None


def _decoded_header(value: Optional[str]) -> str:
    if not value:
        return ""
    parts = []
    for content, charset in decode_header(value):
        if isinstance(content, bytes):
            parts.append(content.decode(charset or "utf-8", errors="replace"))
        else:
            parts.append(content)
    return "".join(parts)


def _document_type(filename: str) -> DocumentType:
    normalized = filename.upper()
    if "COA" in normalized or "CERTIFICATE_OF_ANALYSIS" in normalized:
        return DocumentType.COA
    if "SDS" in normalized or "SAFETY_DATA" in normalized:
        return DocumentType.SDS
    if "GMP" in normalized:
        return DocumentType.GMP
    return DocumentType.OTHER


def _sent_batch_requests(db: Session):
    return (
        db.query(EmailEvent, Batch)
        .join(Batch, Batch.id == EmailEvent.batch_id)
        .filter(
            EmailEvent.email_type == "DOCUMENT_REQUEST",
            EmailEvent.status == "SENT",
            Batch.company_id == EmailEvent.company_id,
            EmailEvent.created_at
            >= datetime.now(timezone.utc) - timedelta(days=settings.IMAP_LOOKBACK_DAYS),
        )
        .order_by(EmailEvent.created_at.desc())
        .all()
    )


def _matching_batch_id(sender: str, subject: str, sent_requests) -> Optional[str]:
    matching = []
    for request, batch in sent_requests:
        if request.recipient_email.strip().casefold() != sender.casefold():
            continue
        token = re.compile(
            rf"(?<![A-Za-z0-9]){re.escape(batch.batch_number)}(?![A-Za-z0-9])",
            re.IGNORECASE,
        )
        if token.search(subject):
            matching.append((len(batch.batch_number), request.created_at, str(batch.id)))
    if not matching:
        return None
    matching.sort(key=lambda item: (item[0], item[1]), reverse=True)
    if len(matching) > 1 and matching[0][:2] == matching[1][:2]:
        logger.warning("Inbound email subject matched multiple document requests from %s", sender)
        return None
    return matching[0][2]


def _find_batch_for_reply(db: Session, sender: str, subject: str) -> Optional[Batch]:
    """Only accept replies to a sent document request, addressed to that sender."""
    batch_id = _matching_batch_id(sender, subject, _sent_batch_requests(db))
    if not batch_id:
        return None
    return db.query(Batch).filter(Batch.id == UUID(batch_id)).first()


def _mailbox_key(username: str, folder: str) -> str:
    return hashlib.sha256(f"{username.casefold()}:{folder}".encode("utf-8")).hexdigest()[:20]


def _request_search_terms(sent_requests) -> list[tuple[str, str]]:
    return sorted({
        (request.recipient_email.strip().casefold(), batch.batch_number)
        for request, batch in sent_requests
        if re.fullmatch(
            r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+",
            request.recipient_email.strip(),
        )
        and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,99}", batch.batch_number)
    })


def _last_scanned_uid(db: Session, mailbox_key: str) -> int:
    checkpoints = (
        db.query(AuditEvent)
        .filter(AuditEvent.event_type == "IMAP Inbox Checkpoint")
        .order_by(AuditEvent.created_at.desc())
        .limit(100)
        .all()
    )
    for checkpoint in checkpoints:
        if checkpoint.details.get("mailbox_key") == mailbox_key:
            return int(checkpoint.details.get("uid", 0))
    return 0


def _save_checkpoint(db: Session, mailbox_key: str, uid: int) -> None:
    db.add(AuditEvent(
        event_type="IMAP Inbox Checkpoint",
        details={"mailbox_key": mailbox_key, "uid": uid},
    ))
    db.commit()


def ingest_message(db: Session, raw_message: bytes, message_uid: str) -> tuple[int, bool]:
    """Store/extract PDF attachments; return (new document count, handled)."""
    message = message_from_bytes(raw_message, policy=default)
    sender = parseaddr(str(message.get("From", "")))[1].strip().casefold()
    subject = _decoded_header(message.get("Subject"))
    if not sender or not subject:
        logger.info("Skipping inbound email without sender or subject (UID %s)", message_uid)
        return 0, False

    batch = _find_batch_for_reply(db, sender, subject)
    if not batch:
        logger.info("No sent batch document request matches inbound email UID %s", message_uid)
        return 0, False

    message_id = str(message.get("Message-ID", "")).strip()
    dedupe_id = hashlib.sha256(
        (message_id or message_uid).encode("utf-8")
    ).hexdigest()[:20]
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    saved_documents = []
    saved_paths = []
    existing_documents = 0
    total_bytes = 0
    try:
        for part_index, part in enumerate(message.iter_attachments()):
            original_name = part.get_filename() or ""
            if not original_name.lower().endswith(".pdf"):
                continue
            content = part.get_payload(decode=True)
            if not content:
                logger.warning("Skipping empty PDF attachment in email UID %s", message_uid)
                continue
            if len(content) > max_bytes:
                logger.warning("Skipping oversized PDF attachment in email UID %s", message_uid)
                continue
            total_bytes += len(content)
            if total_bytes > max_bytes:
                logger.warning("Skipping PDFs exceeding total upload limit in email UID %s", message_uid)
                break
            if not content.startswith(b"%PDF-"):
                logger.warning("Skipping attachment without a PDF signature in email UID %s", message_uid)
                continue

            safe_name = Path(original_name).name.replace("\x00", "")
            if not safe_name:
                safe_name = "attachment.pdf"
            stored_name = f"{batch.id}_{dedupe_id}_{part_index}_{safe_name}"
            file_path = upload_dir / stored_name
            existing = db.query(Document).filter(
                Document.batch_id == batch.id,
                Document.file_path == str(file_path),
            ).first()
            if existing:
                existing_documents += 1
                continue

            file_path.write_bytes(content)
            saved_paths.append(file_path)
            doc_type = _document_type(safe_name)
            doc = Document(
                company_id=batch.company_id,
                batch_id=batch.id,
                vendor_id=batch.vendor_id,
                document_type=doc_type.value,
                file_name=safe_name,
                file_path=str(file_path),
                mime_type="application/pdf",
                file_size=len(content),
                processing_status="UPLOADED",
            )
            db.add(doc)
            db.flush()

            result = document_service.process_document(
                file_source=str(file_path),
                filename=safe_name,
                document_type=doc_type,
                document_id=doc.id,
            )
            doc.extracted_data = result.extracted_data
            doc.processing_status = result.status.value
            doc.extraction_error = result.error
            doc.processed_at = datetime.now(timezone.utc)
            if doc_type == DocumentType.COA and batch.purity_reported is None:
                purity = result.extracted_data.get("purity")
                if purity is not None:
                    batch.purity_reported = purity
            saved_documents.append({
                "document_id": str(doc.id),
                "filename": safe_name,
                "document_type": doc_type.value,
                "extraction_status": result.status.value,
            })

        if not saved_documents:
            db.rollback()
            for path in saved_paths:
                path.unlink(missing_ok=True)
            return 0, existing_documents > 0

        details = {
            "sender": sender,
            "subject": subject,
            "message_id": message_id or None,
            "message_uid": message_uid,
            "attachments": saved_documents,
        }
        db.add(AuditEvent(
            event_type="Email Received",
            company_id=batch.company_id,
            vendor_id=batch.vendor_id,
            batch_id=batch.id,
            details=details,
        ))
        record_audit_event(
            db,
            "Documents Processed",
            company_id=batch.company_id,
            vendor_id=batch.vendor_id,
            batch_id=batch.id,
            details={"source": "email", "documents_count": len(saved_documents)},
            commit=False,
        )
        db.commit()

        # Update vendor contact email if empty
        try:
            from app.models.vendor import Vendor
            vendor = db.query(Vendor).filter(Vendor.id == batch.vendor_id).first()
            if vendor and sender and not vendor.email:
                vendor.email = sender
                db.add(vendor)
                db.commit()
        except Exception:
            pass

        # Trigger complete automated qualification pipeline & update genuine analytics
        try:
            from app.services.pipeline_service import run_full_batch_pipeline
            run_full_batch_pipeline(db, batch)
            logger.info("Automatically executed batch qualification pipeline for batch %s", batch.batch_number)
        except Exception as exc:
            logger.warning("Pipeline execution after email ingestion failed for batch %s: %s", batch.batch_number, exc)

        logger.info(
            "Ingested %s PDF attachment(s) from inbound email UID %s for batch %s",
            len(saved_documents),
            message_uid,
            batch.batch_number,
        )
        return len(saved_documents), True
    except Exception:
        db.rollback()
        for path in saved_paths:
            path.unlink(missing_ok=True)
        raise


def poll_inbox_once() -> int:
    """Fetch unread messages and ingest matching PDF replies."""
    username = settings.IMAP_USERNAME or settings.SMTP_USERNAME
    password = settings.IMAP_PASSWORD or settings.SMTP_PASSWORD
    if not username or not password:
        raise RuntimeError("IMAP_USERNAME/IMAP_PASSWORD or SMTP credentials must be configured.")
    if SessionLocal is None:
        get_engine()
    mailbox_key = _mailbox_key(username, settings.IMAP_FOLDER)
    checkpoint_db = SessionLocal()
    try:
        last_uid = _last_scanned_uid(checkpoint_db, mailbox_key)
        sent_requests = _sent_batch_requests(checkpoint_db)
    finally:
        checkpoint_db.close()

    client = imaplib.IMAP4_SSL(settings.IMAP_HOST, settings.IMAP_PORT, timeout=30)
    client.sock.settimeout(30)
    total_documents = 0
    highest_scanned_uid = last_uid
    try:
        client.login(username, password)
        logger.info("Authenticated to Gmail IMAP; checking unread mailbox headers.")
        status, _ = client.select(settings.IMAP_FOLDER)
        if status != "OK":
            raise RuntimeError(f"Unable to select IMAP folder {settings.IMAP_FOLDER!r}.")
        logger.info("Selected Gmail IMAP folder; searching for replies to known recipients.")
        candidate_uids = set()
        since_date = (
            datetime.now(timezone.utc) - timedelta(days=settings.IMAP_LOOKBACK_DAYS)
        ).strftime("%d-%b-%Y")
        for address, batch_number in _request_search_terms(sent_requests):
            status, data = client.uid(
                "search",
                None,
                "UNSEEN",
                "FROM",
                address,
                "SUBJECT",
                batch_number,
                "SINCE",
                since_date,
            )
            if status != "OK":
                raise RuntimeError("Unable to search Gmail for unread supplier replies.")
            candidate_uids.update((data[0] or b"").split())
        logger.info(
            "Gmail IMAP returned %s unread message(s) from configured request contacts.",
            len(candidate_uids),
        )

        for message_uid in sorted(candidate_uids, key=int):
            uid = int(message_uid)
            if uid <= last_uid:
                continue
            status, fetched = client.uid("fetch", message_uid, "(BODY.PEEK[HEADER])")
            if status != "OK" or not fetched or not isinstance(fetched[0], tuple):
                logger.warning("Could not fetch headers for unread IMAP UID %s", uid)
                break
            headers = message_from_bytes(fetched[0][1], policy=default)
            sender = parseaddr(str(headers.get("From", "")))[1].strip().casefold()
            subject = _decoded_header(headers.get("Subject"))
            batch_id = _matching_batch_id(sender, subject, sent_requests) if sender and subject else None

            stored_count = 0
            handled = False
            if batch_id:
                status, full_message = client.uid(
                    "fetch", message_uid, "(BODY.PEEK[])"
                )
                if status != "OK" or not full_message or not isinstance(full_message[0], tuple):
                    logger.warning("Could not fetch matched supplier reply UID %s", uid)
                    break
                db = SessionLocal()
                try:
                    stored_count, handled = ingest_message(db, full_message[0][1], str(uid))
                except Exception:
                    logger.exception("Failed processing inbound IMAP UID %s", uid)
                    break
                finally:
                    db.close()
                if handled:
                    client.uid("store", message_uid, "+FLAGS", "\\Seen")

            highest_scanned_uid = uid
            if stored_count:
                total_documents += stored_count

        if highest_scanned_uid > last_uid:
            checkpoint_db = SessionLocal()
            try:
                _save_checkpoint(checkpoint_db, mailbox_key, highest_scanned_uid)
            finally:
                checkpoint_db.close()
        if highest_scanned_uid > last_uid:
            logger.info(
                "Gmail inbox poll scanned new UIDs through %s and stored %s PDF attachment(s).",
                highest_scanned_uid,
                total_documents,
            )
        return total_documents
    finally:
        try:
            client.logout()
        except imaplib.IMAP4.error:
            logger.debug("IMAP logout failed after inbox poll", exc_info=True)


def _polling_loop() -> None:
    logger.info("Gmail IMAP attachment receiver started.")
    while not _stop_event.is_set():
        try:
            count = poll_inbox_once()
            if count:
                logger.info("Gmail inbox poll stored %s PDF attachment(s).", count)
        except Exception:
            logger.exception("Gmail inbox poll failed; will retry.")
        _stop_event.wait(settings.IMAP_POLL_INTERVAL_SECONDS)
    logger.info("Gmail IMAP attachment receiver stopped.")


def start_inbound_email_worker() -> None:
    """Start the opt-in inbox poller once per application process."""
    global _worker
    if not settings.IMAP_ENABLED:
        logger.info("Gmail IMAP attachment receiver is disabled.")
        return
    if _worker and _worker.is_alive():
        return
    _stop_event.clear()
    _worker = threading.Thread(
        target=_polling_loop,
        name="vendoriq-gmail-imap",
        daemon=True,
    )
    _worker.start()


def stop_inbound_email_worker() -> None:
    """Stop the inbox poller during graceful application shutdown."""
    _stop_event.set()
    if _worker and _worker.is_alive():
        _worker.join(timeout=5)
