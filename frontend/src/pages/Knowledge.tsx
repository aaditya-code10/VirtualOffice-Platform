import { useCallback, useEffect, useRef, useState } from "react";
import {
  Database,
  FileText,
  Loader2,
  Plus,
  Search,
  Trash2,
  UploadCloud,
  CheckCircle2,
} from "lucide-react";

import { ApiError, api, type DocumentRecord, type Fact, type SearchHit } from "../api";
import { Empty, ErrorBanner, Header, Layout } from "../components/Layout";

const CLASSIFICATIONS = ["known", "derived", "assumption", "unknown"] as const;

export default function Knowledge() {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [facts, setFacts] = useState<Fact[]>([]);
  const [hits, setHits] = useState<SearchHit[] | null>(null);
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadStage, setUploadStage] = useState<"IDLE" | "UPLOAD" | "PARSING" | "CHUNKING" | "EMBEDDING" | "INDEXED">("IDLE");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const [draft, setDraft] = useState({
    title: "",
    statement: "",
    category: "General",
    classification: "known" as (typeof CLASSIFICATIONS)[number],
    source: "User input",
  });

  const load = useCallback(async () => {
    try {
      const [docs, fs] = await Promise.all([api.getDocuments(), api.getFacts()]);
      setDocuments(docs);
      setFacts(fs);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load the knowledge base.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function upload(file: File) {
    setUploading(true);
    setError(null);
    setNotice(null);
    setUploadStage("UPLOAD");

    try {
      // Step 1: Uploading
      setTimeout(() => setUploadStage("PARSING"), 400);
      setTimeout(() => setUploadStage("CHUNKING"), 900);
      setTimeout(() => setUploadStage("EMBEDDING"), 1400);

      const doc = await api.uploadDocument(file);
      setUploadStage("INDEXED");

      setNotice(
        `Successfully indexed "${doc.filename}" — ${doc.chunk_count} chunks, ` +
          `${doc.word_count.toLocaleString()} words, categorized as ${doc.classification.replace(/_/g, " ")}.`,
      );
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Document indexing failed.");
      setUploadStage("IDLE");
    } finally {
      setTimeout(() => {
        setUploading(false);
        setUploadStage("IDLE");
      }, 1800);
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  async function runSearch() {
    const text = query.trim();
    if (!text) {
      setHits(null);
      return;
    }
    setSearching(true);
    try {
      setHits((await api.search(text)).hits);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Search failed.");
    } finally {
      setSearching(false);
    }
  }

  async function addFact() {
    if (!draft.statement.trim()) return;
    try {
      await api.createFact({ ...draft, title: draft.title || "Business Fact" });
      setDraft({ ...draft, title: "", statement: "" });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save that fact.");
    }
  }

  async function deleteFact(id: string) {
    try {
      await api.deleteFact(id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not delete fact.");
    }
  }

  async function deleteDoc(id: string) {
    try {
      await api.deleteDocument(id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not delete document.");
    }
  }

  return (
    <Layout>
      <Header
        title="Knowledge Corpus & Document Intelligence"
        subtitle="Upload business plans, financials, and transcripts. Documents are chunked, vectorized, and injected into multi-agent prompts."
      />

      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

      {notice && (
        <div
          style={{
            background: "rgba(124, 255, 178, 0.12)",
            border: "1px solid rgba(124, 255, 178, 0.35)",
            borderRadius: "var(--radius-sm)",
            padding: "12px 18px",
            color: "var(--success)",
            marginBottom: "20px",
            display: "flex",
            alignItems: "center",
            gap: "10px",
          }}
        >
          <CheckCircle2 size={16} />
          <span>{notice}</span>
        </div>
      )}

      {/* ── 1. Futuristic Glass Upload Zone ───────────────────────────── */}
      <section
        className="knowledge-upload-box"
        onClick={() => fileInput.current?.click()}
      >
        <input
          ref={fileInput}
          type="file"
          accept=".pdf,.docx,.txt,.md"
          style={{ display: "none" }}
          onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])}
          disabled={uploading}
        />

        <div className="upload-icon-orb">
          {uploading ? (
            <Loader2 size={26} className="spin" />
          ) : (
            <UploadCloud size={26} />
          )}
        </div>

        <h3 style={{ fontFamily: "var(--font-display)", fontSize: "19px", fontWeight: 700, color: "#FFFFFF", marginBottom: "6px" }}>
          {uploading ? "Ingesting & Indexing Document…" : "Drop Business Document or Proposal"}
        </h3>
        <p style={{ fontSize: "13.5px", color: "var(--text-muted)", maxWidth: "560px" }}>
          PDF, Word, or Markdown files are parsed, chunked, and embedded into the local semantic vector store for instant agent retrieval.
        </p>

        {/* Animated Upload Pipeline Sequence */}
        <div className="upload-pipeline-strip">
          <span className={`pipeline-step-item ${uploadStage === "UPLOAD" ? "active" : ""}`}>
            01 UPLOAD
          </span>
          <span className="pipeline-arrow">➔</span>
          <span className={`pipeline-step-item ${uploadStage === "PARSING" ? "active" : ""}`}>
            02 PARSING
          </span>
          <span className="pipeline-arrow">➔</span>
          <span className={`pipeline-step-item ${uploadStage === "CHUNKING" ? "active" : ""}`}>
            03 CHUNKING
          </span>
          <span className="pipeline-arrow">➔</span>
          <span className={`pipeline-step-item ${uploadStage === "EMBEDDING" ? "active" : ""}`}>
            04 EMBEDDING
          </span>
          <span className="pipeline-arrow">➔</span>
          <span className={`pipeline-step-item ${uploadStage === "INDEXED" ? "active" : ""}`}>
            05 INDEXED
          </span>
        </div>
      </section>

      {/* ── 2. Semantic Document Search ───────────────────────────────── */}
      <div style={{ margin: "24px 0" }}>
        <div className="glass-panel" style={{ padding: "16px 20px" }}>
          <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
            <div className="glass-input-wrapper" style={{ flex: 1 }}>
              <span className="glass-input-icon"><Search size={16} /></span>
              <input
                className="glass-input has-icon"
                placeholder="Search knowledge corpus across all indexed documents & paragraphs…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && runSearch()}
              />
            </div>
            <button
              type="button"
              className="btn-primary"
              onClick={runSearch}
              disabled={searching || !query.trim()}
            >
              {searching ? <Loader2 size={15} className="spin" /> : <span>Search</span>}
            </button>
          </div>

          {/* Search Hits */}
          {hits && (
            <div style={{ marginTop: "16px", paddingTop: "14px", borderTop: "1px solid var(--glass-border)" }}>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--text-muted)", marginBottom: "12px" }}>
                {hits.length} RETRIEVAL MATCHES FOR "{query}"
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {hits.map((hit) => (
                  <div key={hit.chunk_id} className="glass-card" style={{ padding: "14px 16px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                      <span style={{ fontSize: "12px", color: "var(--soft-blue)", fontWeight: 600 }}>
                        {hit.filename} · Chunk #{hit.position}
                      </span>
                      <span className="grounded-tag">
                        Score {hit.score.toFixed(2)}
                      </span>
                    </div>
                    <p style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: "1.5" }}>
                      {hit.excerpt}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── 3. Split: Stored Documents & Curated Business Facts ────────── */}
      <div className="dashboard-split">
        {/* Indexed Documents Panel */}
        <div className="panel">
          <div className="panel-head">
            <h2>Indexed Documents ({documents.length})</h2>
          </div>

          {documents.length === 0 ? (
            <Empty
              icon={<FileText size={24} />}
              text="No documents uploaded yet. Drop a PDF above to ground the AI advisors."
            />
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {documents.map((doc) => (
                <div key={doc.id} className="glass-card" style={{ padding: "14px 16px" }}>
                  <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
                    <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
                      <div
                        style={{
                          width: "36px",
                          height: "36px",
                          borderRadius: "8px",
                          background: "rgba(139, 92, 255, 0.15)",
                          display: "grid",
                          placeItems: "center",
                          color: "var(--violet-bright)",
                        }}
                      >
                        <FileText size={18} />
                      </div>
                      <div>
                        <strong style={{ fontSize: "13.5px", color: "#FFFFFF", display: "block" }}>
                          {doc.filename}
                        </strong>
                        <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                          {doc.chunk_count} chunks · {(doc.size_bytes / 1024).toFixed(1)} KB · {doc.classification}
                        </span>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => deleteDoc(doc.id)}
                      title="Delete document"
                      style={{
                        background: "none",
                        border: "none",
                        color: "var(--text-muted)",
                        cursor: "pointer",
                        padding: "4px",
                      }}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Curated Business Facts Panel */}
        <div className="panel">
          <div className="panel-head">
            <h2>Verified Enterprise Facts ({facts.length})</h2>
          </div>

          {/* New Fact Composer */}
          <div style={{ marginBottom: "16px", display: "flex", flexDirection: "column", gap: "8px" }}>
            <input
              className="glass-input"
              placeholder="Fact title (e.g. Current monthly revenue)"
              value={draft.title}
              onChange={(e) => setDraft({ ...draft, title: e.target.value })}
            />
            <div style={{ display: "flex", gap: "8px" }}>
              <input
                className="glass-input"
                placeholder="Authoritative statement (e.g. Monthly burn is ₹1.2L)"
                value={draft.statement}
                onChange={(e) => setDraft({ ...draft, statement: e.target.value })}
                style={{ flex: 1 }}
              />
              <button
                type="button"
                className="btn-primary"
                onClick={addFact}
                disabled={!draft.statement.trim()}
              >
                <Plus size={15} />
              </button>
            </div>
          </div>

          {facts.length === 0 ? (
            <Empty
              icon={<Database size={24} />}
              text="No facts recorded. Add authoritative corporate statements above."
            />
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "8px", maxHeight: "420px", overflowY: "auto" }}>
              {facts.map((fact) => (
                <div key={fact.id} className="glass-card" style={{ padding: "12px 14px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                    <strong style={{ fontSize: "12.5px", color: "var(--violet-bright)" }}>
                      {fact.title}
                    </strong>
                    <button
                      type="button"
                      onClick={() => deleteFact(fact.id)}
                      style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer" }}
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                  <p style={{ fontSize: "12px", color: "var(--text-secondary)", margin: 0 }}>
                    {fact.statement}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
