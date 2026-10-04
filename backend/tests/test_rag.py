"""Document parsing, chunking and BM25 retrieval."""
import pytest

from app.services import rag


def test_tokenize_drops_stopwords_and_stems():
    assert rag.tokenize("The margin is falling and the cost is rising") == [
        "margin", "fal", "cost", "ris"
    ]


def test_stemming_makes_inflections_agree():
    """Indexing and querying share one tokenizer, so related words must collide."""
    for group in (
        ("price", "prices", "pricing", "priced"),
        ("hire", "hires", "hiring"),
        ("cost", "costs"),
        ("company", "companies"),
        ("fall", "falls", "falling"),
        ("business", "businesses"),
    ):
        assert len({rag.stem(word) for word in group}) == 1, group


def test_stemmer_does_not_mangle_non_plurals():
    for word in ("analysis", "business", "status"):
        assert rag.stem(word) == word


def test_stemmer_is_idempotent():
    for word in ("pricing", "companies", "running", "engineers", "capacity"):
        assert rag.stem(rag.stem(word)) == rag.stem(word)


def test_chunk_text_respects_size_and_drops_noise():
    text = "\n\n".join(f"Paragraph {i} " + ("word " * 60) for i in range(6))
    chunks = rag.chunk_text(text, size=500, overlap=50)

    assert len(chunks) > 1
    assert all(len(c) <= 700 for c in chunks)  # size + overlap slack
    assert all(len(c) > 20 for c in chunks)


def test_chunk_text_splits_a_single_oversized_paragraph():
    giant = " ".join(f"Sentence number {i} about margins." for i in range(200))
    chunks = rag.chunk_text(giant, size=400, overlap=40)
    assert len(chunks) > 3


def test_extract_text_handles_plain_and_html():
    assert "hello" in rag.extract_text("a.txt", "text/plain", b"hello world")
    html = b"<html><body><p>Revenue rose</p><script>evil()</script></body></html>"
    extracted = rag.extract_text("a.html", "text/html", html)
    assert "Revenue rose" in extracted
    assert "evil" not in extracted


def test_extract_text_rejects_unparseable_binary():
    with pytest.raises(rag.UnsupportedDocument):
        rag.extract_text("photo.png", "image/png", b"\x89PNG\r\n")


def test_classification_buckets():
    assert rag.classify("q3.pdf", "Gross margin and EBITDA summary") == "financial_statement"
    assert rag.classify("notes.txt", "NPS and CSAT survey feedback") == "customer_feedback"
    assert rag.classify("misc.txt", "nothing in particular here") == "business_document"


def test_search_ranks_relevant_chunks_first(client, demo):
    response = client.get(
        "/api/knowledge/search",
        params={"q": "implementation capacity utilisation delivery"},
        headers=demo["headers"],
    )
    assert response.status_code == 200
    hits = response.json()["hits"]

    assert hits, "expected the seeded QBR document to match"
    assert hits == sorted(hits, key=lambda h: -h["score"])
    assert "capacity" in hits[0]["excerpt"].lower() or "utilisation" in hits[0]["excerpt"].lower()


def test_search_returns_nothing_for_unrelated_query(client, demo):
    response = client.get(
        "/api/knowledge/search",
        params={"q": "photosynthesis chlorophyll"},
        headers=demo["headers"],
    )
    assert response.json()["hits"] == []


def test_upload_indexes_and_becomes_searchable(client, registered):
    content = (
        b"Acme Widget Corporation internal memo.\n\n"
        b"Our warehouse throughput fell 22% after the conveyor retrofit. "
        b"The bottleneck is the outbound packing station, which now handles "
        b"1,400 units per shift against a target of 1,800.\n\n"
        b"Recommended remediation is a second packing line by Q4."
    )

    upload = client.post(
        "/api/knowledge/documents",
        headers=registered["headers"],
        files={"file": ("memo.txt", content, "text/plain")},
    )
    assert upload.status_code == 201, upload.text
    body = upload.json()
    assert body["status"] == "indexed"
    assert body["chunk_count"] >= 1
    assert body["word_count"] > 20

    found = client.get(
        "/api/knowledge/search",
        params={"q": "packing station bottleneck"},
        headers=registered["headers"],
    ).json()
    assert found["hits"], "uploaded document should be immediately searchable"
    assert found["hits"][0]["filename"] == "memo.txt"


def test_upload_rejects_empty_and_unsupported(client, registered):
    empty = client.post(
        "/api/knowledge/documents",
        headers=registered["headers"],
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert empty.status_code == 400

    binary = client.post(
        "/api/knowledge/documents",
        headers=registered["headers"],
        files={"file": ("image.png", b"\x89PNG\r\n\x1a\n", "image/png")},
    )
    assert binary.status_code == 415


def test_deleting_a_document_removes_its_chunks(client, registered):
    upload = client.post(
        "/api/knowledge/documents",
        headers=registered["headers"],
        files={"file": ("temp.txt", b"Quarterly logistics throughput analysis. " * 20, "text/plain")},
    ).json()

    assert client.get(
        "/api/knowledge/search",
        params={"q": "logistics throughput"},
        headers=registered["headers"],
    ).json()["hits"]

    deleted = client.delete(
        f"/api/knowledge/documents/{upload['id']}", headers=registered["headers"]
    )
    assert deleted.status_code == 204

    after = client.get(
        "/api/knowledge/search",
        params={"q": "logistics throughput"},
        headers=registered["headers"],
    ).json()["hits"]
    assert all(h["document_id"] != upload["id"] for h in after)
