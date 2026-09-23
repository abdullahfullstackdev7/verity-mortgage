from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user, get_db, require_roles
from backend.app.db.models.enums import DocumentType, UserRole
from backend.app.db.models.extracted_field import ExtractedField
from backend.app.db.models.user import User
from backend.app.schemas.document import DocumentRead
from backend.app.schemas.extracted_field import ExtractedFieldRead
from backend.app.services import case_service, document_service
from backend.app.services.extraction.pipeline import ExtractionError, extract_document

router = APIRouter(prefix="/cases/{case_id}/documents", tags=["documents"])


def _get_document_or_404(db: Session, case_id: uuid.UUID, document_id: uuid.UUID):
    case = case_service.get_case(db, case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    document = document_service.get_document_in_case(db, case, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


@router.post(
    "",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(UserRole.LOAN_OFFICER, UserRole.ADMIN))],
)
async def upload_document(
    case_id: uuid.UUID,
    doc_type: DocumentType = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DocumentRead:
    case = case_service.get_case(db, case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    content = await file.read()
    try:
        document = document_service.save_document(db, case, doc_type, file.filename or "", content)
    except document_service.InvalidFileError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)
        ) from exc
    except document_service.FileTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=str(exc)
        ) from exc

    return document


@router.get("", response_model=list[DocumentRead])
def list_documents(
    case_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[DocumentRead]:
    case = case_service.get_case(db, case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return document_service.list_documents(db, case)


@router.post(
    "/{document_id}/extract",
    response_model=list[ExtractedFieldRead],
    dependencies=[Depends(require_roles(UserRole.LOAN_OFFICER, UserRole.UNDERWRITER, UserRole.ADMIN))],
)
def extract_document_fields(
    case_id: uuid.UUID,
    document_id: uuid.UUID,
    force: bool = False,
    db: Session = Depends(get_db),
) -> list[ExtractedFieldRead]:
    document = _get_document_or_404(db, case_id, document_id)
    try:
        return extract_document(db, document, force=force)
    except ExtractionError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get("/{document_id}/file")
def download_document_file(
    case_id: uuid.UUID,
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> FileResponse:
    document = _get_document_or_404(db, case_id, document_id)
    file_path = Path(document.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk")
    return FileResponse(file_path, media_type="application/pdf", filename=file_path.name)


@router.get("/{document_id}/fields", response_model=list[ExtractedFieldRead])
def list_extracted_fields(
    case_id: uuid.UUID,
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[ExtractedFieldRead]:
    document = _get_document_or_404(db, case_id, document_id)
    return (
        db.query(ExtractedField).filter(ExtractedField.document_id == document.id).all()
    )
