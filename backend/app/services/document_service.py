from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.db.models.case import Case
from backend.app.db.models.document import Document
from backend.app.db.models.enums import DocumentType, OcrStatus

PDF_MAGIC_BYTES = b"%PDF-"


class InvalidFileError(Exception):
    pass


class FileTooLargeError(Exception):
    pass


def save_document(
    db: Session,
    case: Case,
    doc_type: DocumentType,
    filename: str,
    content: bytes,
) -> Document:
    if len(content) > settings.max_upload_size_bytes:
        raise FileTooLargeError(f"File exceeds the {settings.max_upload_size_bytes} byte upload limit")

    # Validate by content, not just the filename extension or client-sent
    # content-type, since either can be spoofed.
    if not content.startswith(PDF_MAGIC_BYTES):
        raise InvalidFileError("Only PDF files are accepted")

    storage_dir = Path(settings.document_storage_dir) / str(case.id)
    storage_dir.mkdir(parents=True, exist_ok=True)

    safe_name = f"{doc_type.value}_{uuid.uuid4().hex}.pdf"
    file_path = storage_dir / safe_name
    file_path.write_bytes(content)

    document = Document(
        case_id=case.id,
        doc_type=doc_type,
        file_path=str(file_path),
        ocr_status=OcrStatus.PENDING_OCR,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def get_document_in_case(db: Session, case: Case, document_id: uuid.UUID) -> Document | None:
    return db.query(Document).filter(Document.id == document_id, Document.case_id == case.id).one_or_none()


def list_documents(db: Session, case: Case) -> list[Document]:
    return db.query(Document).filter(Document.case_id == case.id).order_by(Document.uploaded_at).all()
