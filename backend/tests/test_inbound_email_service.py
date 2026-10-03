from email.message import EmailMessage

from sqlalchemy.orm import sessionmaker
from app.models.decision import AuditEvent, EmailEvent
from app.models.document import Document
from app.schemas.document import DocumentExtractionStatus, DocumentType, DocumentProcessResult
from app.services import inbound_email_service


def _supplier_reply(sender, subject, filename="COA.pdf"):
    message = EmailMessage()
    message["From"] = sender
    message["To"] = "vendoriq@example.com"
    message["Subject"] = subject
    message["Message-ID"] = "<supplier-reply-1@example.com>"
    message.set_content("Please find the requested document attached.")
    message.add_attachment(
        b"%PDF-1.4\nexample test PDF bytes",
        maintype="application",
        subtype="pdf",
        filename=filename,
    )
    return message.as_bytes()


def _sent_request(db_session, sample_batch, recipient="qa@example.com"):
    request = EmailEvent(
        company_id=sample_batch.company_id,
        vendor_id=sample_batch.vendor_id,
        batch_id=sample_batch.id,
        recipient_email=recipient,
        subject=f"VendorIQ — Documentation Request: Batch {sample_batch.batch_number}",
        email_type="DOCUMENT_REQUEST",
        status="SENT",
        provider="GOOGLE_SMTP",
        html_content="<p>Request</p>",
    )
    db_session.add(request)
    db_session.commit()
    return request


def test_ingest_supplier_reply_saves_pdf_extracts_text_and_audits(
    db_session, sample_batch, monkeypatch, tmp_path
):
    sample_batch.purity_reported = None
    _sent_request(db_session, sample_batch)
    monkeypatch.setattr(inbound_email_service.settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(
        inbound_email_service.document_service,
        "process_document",
        lambda **kwargs: DocumentProcessResult(
            filename=kwargs["filename"],
            document_type=kwargs["document_type"],
            status=DocumentExtractionStatus.PROCESSED,
            extracted_data={"batch_number": sample_batch.batch_number, "purity": 99.7},
        ),
    )

    count, handled = inbound_email_service.ingest_message(
        db_session,
        _supplier_reply(
            "qa@example.com",
            f"Re: VendorIQ — Documentation Request: Batch {sample_batch.batch_number}",
        ),
        "13",
    )

    document = db_session.query(Document).filter(
        Document.batch_id == sample_batch.id
    ).one()
    event = db_session.query(AuditEvent).filter(
        AuditEvent.event_type == "Email Received",
        AuditEvent.batch_id == sample_batch.id,
    ).one()
    assert (count, handled) == (1, True)
    assert document.document_type == "COA"
    assert document.processing_status == "PROCESSED"
    assert document.extracted_data["purity"] == 99.7
    assert sample_batch.purity_reported == 99.7
    assert event.details["sender"] == "qa@example.com"
    assert event.details["attachments"][0]["filename"] == "COA.pdf"


def test_ingest_supplier_reply_rejects_unmatched_sender(db_session, sample_batch, tmp_path, monkeypatch):
    _sent_request(db_session, sample_batch)
    monkeypatch.setattr(inbound_email_service.settings, "UPLOAD_DIR", str(tmp_path))

    result = inbound_email_service.ingest_message(
        db_session,
        _supplier_reply(
            "unrelated@example.com",
            f"Re: Batch {sample_batch.batch_number}",
        ),
        "14",
    )

    assert result == (0, False)
    assert db_session.query(Document).filter(Document.batch_id == sample_batch.id).count() == 0


def test_ingest_supplier_reply_is_idempotent_for_duplicate_message(
    db_session, sample_batch, monkeypatch, tmp_path
):
    _sent_request(db_session, sample_batch)
    monkeypatch.setattr(inbound_email_service.settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(
        inbound_email_service.document_service,
        "process_document",
        lambda **kwargs: DocumentProcessResult(
            filename=kwargs["filename"],
            document_type=DocumentType.COA,
            status=DocumentExtractionStatus.PROCESSED,
            extracted_data={},
        ),
    )
    raw_message = _supplier_reply(
        "qa@example.com",
        f"Re: Batch {sample_batch.batch_number}",
    )

    first = inbound_email_service.ingest_message(db_session, raw_message, "15")
    second = inbound_email_service.ingest_message(db_session, raw_message, "16")

    assert first == (1, True)
    assert second == (0, True)
    assert db_session.query(Document).filter(Document.batch_id == sample_batch.id).count() == 1


def test_inbox_poll_uses_uid_checkpoint_and_marks_matched_reply_seen(
    db_session, sample_batch, monkeypatch, tmp_path
):
    _sent_request(db_session, sample_batch)
    monkeypatch.setattr(inbound_email_service.settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(inbound_email_service.settings, "IMAP_USERNAME", "inbox@example.com")
    monkeypatch.setattr(inbound_email_service.settings, "IMAP_PASSWORD", "app-password")
    monkeypatch.setattr(
        inbound_email_service,
        "SessionLocal",
        sessionmaker(bind=db_session.get_bind()),
    )
    monkeypatch.setattr(
        inbound_email_service.document_service,
        "process_document",
        lambda **kwargs: DocumentProcessResult(
            filename=kwargs["filename"],
            document_type=DocumentType.COA,
            status=DocumentExtractionStatus.PROCESSED,
            extracted_data={"purity": 99.4},
        ),
    )
    raw_message = _supplier_reply(
        "qa@example.com",
        f"Re: Batch {sample_batch.batch_number}",
    )
    headers = raw_message.split(b"\r\n\r\n", 1)[0] + b"\r\n\r\n"

    class FakeIMAP:
        def __init__(self):
            self.fetch_count = 0
            self.seen = []
            self.searches = []
            self.sock = type("FakeSocket", (), {"settimeout": lambda *_args: None})()

        def login(self, *_args):
            return "OK", [b"logged in"]

        def select(self, *_args):
            return "OK", [b"1"]

        def uid(self, command, *args):
            if command == "search":
                self.searches.append(args)
                return "OK", [b"101"]
            if command == "fetch":
                self.fetch_count += 1
                content = headers if "HEADER" in str(args[1]) else raw_message
                return "OK", [(b"101 FETCH", content), b")"]
            if command == "store":
                self.seen.append(args[0])
                return "OK", [b"stored"]
            raise AssertionError(f"Unexpected IMAP command: {command}")

        def logout(self):
            return "BYE", [b"logout"]

    fake_imap = FakeIMAP()
    monkeypatch.setattr(
        inbound_email_service.imaplib,
        "IMAP4_SSL",
        lambda *_args, **_kwargs: fake_imap,
    )

    assert inbound_email_service.poll_inbox_once() == 1
    assert inbound_email_service.poll_inbox_once() == 0
    assert len(fake_imap.searches) == 2
    assert all("SUBJECT" in args and sample_batch.batch_number in args for args in fake_imap.searches)
    assert fake_imap.fetch_count == 2
    assert fake_imap.seen == [b"101"]
    assert db_session.query(Document).filter(Document.batch_id == sample_batch.id).count() == 1
