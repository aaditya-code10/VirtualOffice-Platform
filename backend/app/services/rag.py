"""Document ingestion and retrieval.

Deliberately dependency-light: text is extracted, chunked, and indexed as sparse
term-frequency maps stored in the database. Retrieval uses BM25, which needs no
embedding model, no vector database, and no network call - so knowledge search
works identically offline, in CI, and in production.

Swapping in embeddings later means replacing ``score_chunks`` and adding a vector
column; the ingestion pipeline and the API contract stay the same.
"""
from __future__ import annotations

import io
import math
import re
from collections import Counter
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Document, DocumentChunk

# --------------------------------------------------------------------------- #
# Tokenisation
# --------------------------------------------------------------------------- #
_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9'&.\-]*")

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "then", "than", "so", "of", "to",
    "in", "on", "at", "by", "for", "with", "from", "as", "is", "are", "was", "were",
    "be", "been", "being", "it", "its", "this", "that", "these", "those", "we", "our",
    "you", "your", "they", "their", "he", "she", "his", "her", "i", "me", "my", "us",
    "do", "does", "did", "have", "has", "had", "will", "would", "can", "could",
    "should", "may", "might", "must", "not", "no", "there", "here", "what", "which",
    "who", "when", "where", "how", "why", "all", "any", "each", "more", "most",
    "other", "some", "such", "only", "own", "same", "also", "into", "about", "over",
    "up", "down", "out", "off", "again", "further", "s", "t",
}


# A deliberately light stemmer. The goal is not linguistically correct roots but
# *agreement*: "price", "prices" and "pricing" must all collapse to the same key
# so a question about pricing matches a document about price. Stems are never
# shown to users - excerpts and evidence labels use the original text.
_SUFFIXES: tuple[tuple[str, str], ...] = (
    ("ies", "y"),
    ("ing", ""),
    ("ed", ""),
    ("es", ""),
    ("s", ""),
)

# Words ending this way are not plurals: analysis, basis, business, status.
_NOT_PLURAL = ("ss", "is", "us")


def _normalise(root: str) -> str:
    """Final shaping applied to EVERY word, inflected or not.

    Running this on both paths is what makes stems agree: "fall" and "falling"
    must land on the same key, which only happens if the base form gets the same
    treatment as the stripped one.
    """
    # "runn" -> "run", "fall" -> "fal". The vowel guard protects "engineer";
    # "s" is excluded because collapsing it would undo the _NOT_PLURAL guard and
    # make "business" drift on a second pass ("busines" -> "busin").
    if len(root) > 3 and root[-1] == root[-2] and root[-1] not in "aeious":
        root = root[:-1]
    # "price" -> "pric", so it meets "prices" -> "pric".
    if len(root) > 3 and root.endswith("e"):
        root = root[:-1]
    return root


def stem(token: str) -> str:
    """Collapse inflections so related words share a key. Idempotent."""
    if len(token) <= 3:
        return token

    for suffix, replacement in _SUFFIXES:
        if not token.endswith(suffix):
            continue
        if suffix in ("s", "es") and token.endswith(_NOT_PLURAL):
            continue
        candidate = token[: -len(suffix)] + replacement
        if len(candidate) >= 3:
            return _normalise(candidate)

    return _normalise(token)


def tokenize(text: str) -> list[str]:
    """Lowercase, strip stopwords, and stem - used for both indexing and querying.

    Indexing and querying MUST share this function; changing it invalidates
    stored term frequencies, which is why `app.cli reindex` exists.
    """
    return [
        stem(tok)
        for tok in _TOKEN_RE.findall(text.lower())
        if tok not in STOPWORDS and len(tok) > 1
    ]


# --------------------------------------------------------------------------- #
# Text extraction
# --------------------------------------------------------------------------- #
class UnsupportedDocument(Exception):
    pass


def extract_text(filename: str, content_type: str | None, raw: bytes) -> str:
    """Pull plain text out of an uploaded file.

    Supports txt/md/csv/json/html natively; PDF and DOCX when the optional
    ``pypdf`` / ``python-docx`` packages are installed (they are in
    requirements.txt, but the code degrades gracefully without them).
    """
    name = filename.lower()

    if name.endswith(".pdf") or (content_type or "").endswith("pdf"):
        try:
            from pypdf import PdfReader
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise UnsupportedDocument(
                "PDF support requires the 'pypdf' package"
            ) from exc
        reader = PdfReader(io.BytesIO(raw))
        return "\n\n".join((page.extract_text() or "") for page in reader.pages)

    if name.endswith((".docx",)):
        try:
            import docx  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise UnsupportedDocument(
                "DOCX support requires the 'python-docx' package"
            ) from exc
        document = docx.Document(io.BytesIO(raw))
        return "\n".join(p.text for p in document.paragraphs)

    if name.endswith((".doc", ".xls", ".ppt", ".zip", ".png", ".jpg", ".jpeg", ".gif")):
        raise UnsupportedDocument(
            f"'{filename}' is a binary format this build cannot parse. "
            "Convert to PDF, DOCX, TXT, MD, CSV or JSON."
        )

    # Everything else: decode as text, replacing undecodable bytes.
    text = raw.decode("utf-8", errors="replace")
    if name.endswith((".html", ".htm")):
        text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", text, flags=re.S | re.I)
        text = re.sub(r"<[^>]+>", " ", text)
    return text


def classify(filename: str, text: str) -> str:
    """Cheap heuristic labelling so the knowledge base is browsable."""
    name = filename.lower()
    sample = text[:4000].lower()

    buckets = {
        "financial_statement": ["profit and loss", "p&l", "balance sheet", "cash flow", "ebitda", "gross margin"],
        "sales_report": ["pipeline", "quota", "win rate", "opportunit", "closed won"],
        "customer_feedback": ["review", "csat", "nps", "complaint", "survey", "feedback"],
        "hr_document": ["headcount", "payroll", "attrition", "offer letter", "employee handbook"],
        "marketing_report": ["campaign", "impressions", "click-through", "cac", "conversion rate"],
        "operations_report": ["capacity", "throughput", "sla", "downtime", "utilisation", "utilization"],
        "contract": ["agreement", "hereby", "party of the first part", "terms and conditions"],
    }
    for label, needles in buckets.items():
        if any(n in sample or n in name for n in needles):
            return label
    return "business_document"


def summarise(text: str, limit: int = 400) -> str:
    """First meaningful paragraph, trimmed - a cheap stand-in for an abstract."""
    for block in re.split(r"\n\s*\n", text):
        cleaned = " ".join(block.split())
        if len(cleaned) > 80:
            return cleaned[:limit] + ("…" if len(cleaned) > limit else "")
    cleaned = " ".join(text.split())
    return cleaned[:limit] + ("…" if len(cleaned) > limit else "")


# --------------------------------------------------------------------------- #
# Chunking
# --------------------------------------------------------------------------- #
def chunk_text(
    text: str,
    size: int | None = None,
    overlap: int | None = None,
) -> list[str]:
    """Split on paragraph boundaries, packing up to ``size`` characters.

    Overlap carries the tail of the previous chunk forward so a fact split across
    a boundary is still retrievable.
    """
    size = size or settings.chunk_size
    overlap = overlap or settings.chunk_overlap

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        # A single oversized paragraph is hard-split on sentence boundaries.
        if len(para) > size:
            if current:
                chunks.append(current.strip())
                current = ""
            sentences = re.split(r"(?<=[.!?])\s+", para)
            buf = ""
            for sentence in sentences:
                if len(buf) + len(sentence) + 1 > size and buf:
                    chunks.append(buf.strip())
                    buf = buf[-overlap:] if overlap else ""
                buf += (" " if buf else "") + sentence
            if buf.strip():
                current = buf.strip()
            continue

        if len(current) + len(para) + 2 > size and current:
            chunks.append(current.strip())
            current = current[-overlap:] if overlap else ""

        current += ("\n\n" if current else "") + para

    if current.strip():
        chunks.append(current.strip())

    return [c for c in chunks if len(c) > 20]


def index_document(db: Session, document: Document, text: str) -> int:
    """Chunk and persist a document's searchable representation."""
    db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()

    pieces = chunk_text(text)
    for position, piece in enumerate(pieces):
        counts = Counter(tokenize(piece))
        db.add(
            DocumentChunk(
                company_id=document.company_id,
                document_id=document.id,
                position=position,
                content=piece,
                token_estimate=max(1, len(piece) // 4),
                term_frequencies=dict(counts),
            )
        )
    return len(pieces)


# --------------------------------------------------------------------------- #
# Retrieval (BM25)
# --------------------------------------------------------------------------- #
@dataclass
class Retrieved:
    chunk_id: str
    document_id: str
    filename: str
    position: int
    score: float
    content: str
    # Query terms that hit this chunk, used to centre the excerpt on the match.
    matched_terms: list[str] = field(default_factory=list)

    @property
    def excerpt(self) -> str:
        return make_excerpt(self.content, self.matched_terms)


def make_excerpt(content: str, terms: list[str], width: int = 320) -> str:
    """A window of the chunk centred on the first query term that appears.

    Showing the passage that actually matched is far more useful than the head
    of the chunk, which is often a title.
    """
    cleaned = " ".join(content.split())
    if len(cleaned) <= width:
        return cleaned

    lowered = cleaned.lower()
    position = -1
    for term in terms:
        found = lowered.find(term)
        if found != -1 and (position == -1 or found < position):
            position = found

    if position == -1:
        return cleaned[:width] + "…"

    start = max(0, position - width // 3)
    # Snap to a word boundary so the excerpt does not begin mid-word.
    if start > 0:
        space = cleaned.find(" ", start)
        start = space + 1 if space != -1 and space - start < 25 else start

    end = min(len(cleaned), start + width)
    snippet = cleaned[start:end]
    return ("…" if start > 0 else "") + snippet + ("…" if end < len(cleaned) else "")


_K1 = 1.5
_B = 0.75


def search(
    db: Session,
    company_id: str,
    query: str,
    top_k: int | None = None,
) -> list[Retrieved]:
    """BM25 ranking over the company's indexed chunks."""
    top_k = top_k or settings.retrieval_top_k
    terms = tokenize(query)
    if not terms:
        return []

    rows = db.execute(
        select(DocumentChunk, Document.filename)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(DocumentChunk.company_id == company_id)
    ).all()

    if not rows:
        return []

    total_docs = len(rows)
    lengths = [sum((r[0].term_frequencies or {}).values()) or 1 for r in rows]
    avg_len = sum(lengths) / total_docs

    # Document frequency per query term.
    df: Counter[str] = Counter()
    for chunk, _ in rows:
        tf = chunk.term_frequencies or {}
        for term in set(terms):
            if term in tf:
                df[term] += 1

    results: list[Retrieved] = []
    for (chunk, filename), length in zip(rows, lengths, strict=True):
        tf = chunk.term_frequencies or {}
        score = 0.0
        matched: list[str] = []
        for term in terms:
            freq = tf.get(term, 0)
            if not freq:
                continue
            matched.append(term)
            idf = math.log(1 + (total_docs - df[term] + 0.5) / (df[term] + 0.5))
            denom = freq + _K1 * (1 - _B + _B * length / avg_len)
            score += idf * (freq * (_K1 + 1)) / denom

        if score > 0:
            results.append(
                Retrieved(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    filename=filename,
                    position=chunk.position,
                    score=round(score, 4),
                    content=chunk.content,
                    matched_terms=matched,
                )
            )

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:top_k]


def build_context_block(hits: list[Retrieved], char_budget: int = 6000) -> str:
    """Render retrieved chunks as a citable context block for the LLM."""
    if not hits:
        return "(No indexed company documents matched this request.)"

    parts: list[str] = []
    used = 0
    for index, hit in enumerate(hits, start=1):
        body = hit.content.strip()
        entry = f"[S{index}] {hit.filename} (chunk {hit.position}):\n{body}"
        if used + len(entry) > char_budget:
            break
        parts.append(entry)
        used += len(entry)
    return "\n\n".join(parts)
