"""Knowledge base: document ingestion, facts, and semantic search."""
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select

from app.config import settings
from app.core import audit
from app.core.deps import CurrentCompany, CurrentUser, DbSession, RequireMember
from app.models import (
    Document,
    DocumentChunk,
    DocumentStatus,
    Fact,
    FactClassification,
)
from app.schemas import DocumentOut, FactCreate, FactOut, SearchHit, SearchResponse
from app.services import rag

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


# --------------------------------------------------------------------------- #
# Documents
# --------------------------------------------------------------------------- #
@router.get("/documents", response_model=list[DocumentOut])
def list_documents(company: CurrentCompany, user: CurrentUser, db: DbSession) -> list[DocumentOut]:
    docs = db.execute(
        select(Document).where(Document.company_id == company.id).order_by(Document.created_at.desc())
    ).scalars().all()
    return [DocumentOut.model_validate(_doc_out(d)) for d in docs]


@router.post("/documents", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    company: CurrentCompany,
    user: RequireMember,
    db: DbSession,
    file: UploadFile = File(...),
) -> DocumentOut:
    """Parse, chunk, and index an uploaded document into the company knowledge base."""
    raw = await file.read()
    if not raw:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Uploaded file is empty")
    if len(raw) > settings.max_upload_bytes:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"File exceeds the {settings.max_upload_bytes // (1024 * 1024)}MB limit",
        )

    filename = Path(file.filename or "document.txt").name
    document = Document(
        company_id=company.id,
        uploaded_by_id=user.id,
        filename=filename,
        content_type=file.content_type,
        size_bytes=len(raw),
        status=DocumentStatus.PROCESSING,
    )
    db.add(document)
    db.flush()

    try:
        text = rag.extract_text(filename, file.content_type, raw)
    except rag.UnsupportedDocument as exc:
        document.status = DocumentStatus.FAILED
        document.error = str(exc)
        db.flush()
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, str(exc)) from exc

    if not text.strip():
        document.status = DocumentStatus.FAILED
        document.error = "No extractable text found in this file"
        db.flush()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, document.error)

    # Persist the original alongside its index, so re-indexing is possible later.
    company_dir = settings.storage_dir / company.id
    company_dir.mkdir(parents=True, exist_ok=True)
    stored = company_dir / f"{document.id}_{filename}"
    stored.write_bytes(raw)

    document.storage_path = str(stored)
    document.word_count = len(text.split())
    document.classification = rag.classify(filename, text)
    document.summary = rag.summarise(text)
    document.chunk_count = rag.index_document(db, document, text)
    document.status = DocumentStatus.INDEXED

    # Record the ingestion itself as a derived fact so it shows up in context.
    db.add(
        Fact(
            company_id=company.id,
            document_id=document.id,
            category="Ingested document",
            title=filename,
            statement=f"'{filename}' ({document.word_count:,} words) was indexed into the knowledge base. "
                      f"Summary: {document.summary}",
            classification=FactClassification.DERIVED,
            source=filename,
            confidence=100.0,
        )
    )

    audit.record(
        db, action="document.indexed", company_id=company.id, actor=user,
        entity_type="document", entity_id=document.id,
        detail={"filename": filename, "chunks": document.chunk_count, "words": document.word_count},
    )
    db.flush()
    return DocumentOut.model_validate(_doc_out(document))


@router.get("/documents/{document_id}")
def get_document(document_id: str, company: CurrentCompany, user: CurrentUser, db: DbSession):
    document = _lookup_doc(db, company.id, document_id)
    chunks = db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document.id)
        .order_by(DocumentChunk.position)
    ).scalars().all()

    return {
        **_doc_out(document),
        "chunks": [
            {"id": c.id, "position": c.position, "content": c.content, "tokens": c.token_estimate}
            for c in chunks
        ],
    }


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str, company: CurrentCompany, user: RequireMember, db: DbSession) -> None:
    document = _lookup_doc(db, company.id, document_id)

    if document.storage_path:
        Path(document.storage_path).unlink(missing_ok=True)

    audit.record(
        db, action="document.deleted", company_id=company.id, actor=user,
        entity_type="document", entity_id=document.id, detail={"filename": document.filename},
    )
    db.delete(document)  # chunks cascade
    db.flush()


# --------------------------------------------------------------------------- #
# Search
# --------------------------------------------------------------------------- #
@router.get("/search", response_model=SearchResponse)
def search(
    company: CurrentCompany,
    user: CurrentUser,
    db: DbSession,
    q: str = Query(min_length=2, description="Free-text query over indexed documents"),
    top_k: int = Query(default=8, ge=1, le=25),
) -> SearchResponse:
    hits = rag.search(db, company.id, q, top_k=top_k)
    return SearchResponse(
        query=q,
        hits=[
            SearchHit(
                chunk_id=h.chunk_id,
                document_id=h.document_id,
                filename=h.filename,
                position=h.position,
                score=h.score,
                excerpt=h.excerpt,
            )
            for h in hits
        ],
    )


# --------------------------------------------------------------------------- #
# Facts
# --------------------------------------------------------------------------- #
@router.get("/facts", response_model=list[FactOut])
def list_facts(company: CurrentCompany, user: CurrentUser, db: DbSession) -> list[FactOut]:
    facts = db.execute(
        select(Fact).where(Fact.company_id == company.id).order_by(Fact.created_at.desc())
    ).scalars().all()
    return [FactOut.model_validate(_fact_out(f)) for f in facts]


@router.post("/facts", response_model=FactOut, status_code=status.HTTP_201_CREATED)
def create_fact(
    payload: FactCreate, company: CurrentCompany, user: RequireMember, db: DbSession
) -> FactOut:
    fact = Fact(
        company_id=company.id,
        category=payload.category,
        title=payload.title,
        statement=payload.statement,
        value=payload.value,
        classification=FactClassification(payload.classification),
        source=payload.source,
        confidence=payload.confidence,
    )
    db.add(fact)
    audit.record(
        db, action="fact.created", company_id=company.id, actor=user,
        entity_type="fact", entity_id=fact.id, detail={"title": fact.title},
    )
    db.flush()
    return FactOut.model_validate(_fact_out(fact))


@router.delete("/facts/{fact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_fact(fact_id: str, company: CurrentCompany, user: RequireMember, db: DbSession) -> None:
    fact = db.execute(
        select(Fact).where(Fact.company_id == company.id, Fact.id == fact_id)
    ).scalar_one_or_none()
    if fact is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fact not found")

    audit.record(
        db, action="fact.deleted", company_id=company.id, actor=user,
        entity_type="fact", entity_id=fact.id,
    )
    db.delete(fact)
    db.flush()


# --------------------------------------------------------------------------- #
def _lookup_doc(db, company_id: str, document_id: str) -> Document:
    document = db.execute(
        select(Document).where(Document.company_id == company_id, Document.id == document_id)
    ).scalar_one_or_none()
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return document


def _doc_out(d: Document) -> dict:
    return {
        "id": d.id, "filename": d.filename, "content_type": d.content_type,
        "size_bytes": d.size_bytes, "status": d.status.value, "classification": d.classification,
        "chunk_count": d.chunk_count, "word_count": d.word_count, "summary": d.summary,
        "error": d.error, "created_at": d.created_at,
    }


def _fact_out(f: Fact) -> dict:
    return {
        "id": f.id, "category": f.category, "title": f.title, "statement": f.statement,
        "value": f.value, "classification": f.classification.value, "source": f.source,
        "confidence": f.confidence, "document_id": f.document_id, "created_at": f.created_at,
    }
