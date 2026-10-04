import { useCallback, useEffect, useState } from "react";
import {
  ClipboardCheck,
  Loader2,
  Search,
  ShieldAlert,
  BrainCircuit,
  TrendingUp,
  CheckCircle2,
  ArrowRight,
  Filter,
} from "lucide-react";

import { ApiError, api, type WorkOrder, type WorkOrderSummary } from "../api";
import { Empty, ErrorBanner, Header, Layout } from "../components/Layout";
import { WorkOrderModal } from "../components/WorkOrderModal";

function VerdictSignal({ verdict }: { verdict: string | null }) {
  if (!verdict) return <span className="verdict-badge pending">PENDING</span>;
  const v = verdict.toUpperCase();
  if (v.includes("NO-GO") || v.includes("NOGO")) {
    return (
      <span className="verdict-badge nogo">
        <ShieldAlert size={12} /> NO-GO
      </span>
    );
  }
  if (v.includes("PIVOT")) {
    return (
      <span className="verdict-badge pivot">
        <TrendingUp size={12} /> PIVOT
      </span>
    );
  }
  if (v.includes("GO")) {
    return (
      <span className="verdict-badge go">
        <CheckCircle2 size={12} /> GO
      </span>
    );
  }
  return <span className="verdict-badge pending">{verdict.slice(0, 15)}</span>;
}

export default function WorkOrders() {
  const [orders, setOrders] = useState<WorkOrderSummary[]>([]);
  const [selected, setSelected] = useState<WorkOrder | null>(null);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setOrders(await api.getWorkOrders({ limit: 100 }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load work orders.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = orders.filter((order) => {
    const matchesQuery = (
      order.command +
      (order.headline ?? "") +
      (order.category ?? "")
    )
      .toLowerCase()
      .includes(query.toLowerCase());

    const matchesStatus =
      statusFilter === "ALL" ||
      (statusFilter === "GO" && order.recommendation?.toUpperCase().includes("GO") && !order.recommendation?.toUpperCase().includes("NO-GO")) ||
      (statusFilter === "PIVOT" && order.recommendation?.toUpperCase().includes("PIVOT")) ||
      (statusFilter === "NO-GO" && (order.recommendation?.toUpperCase().includes("NO-GO") || order.recommendation?.toUpperCase().includes("NOGO")));

    return matchesQuery && matchesStatus;
  });

  async function open(id: string) {
    try {
      setSelected(await api.getWorkOrder(id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not open that work order.");
    }
  }

  return (
    <Layout>
      <Header
        title="Strategic Work Orders & Archive"
        subtitle={`${orders.length} enterprise evaluation${orders.length === 1 ? "" : "s"} executed and cataloged across the digital workforce.`}
      />

      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

      {/* Filter / Search Bar */}
      <div
        className="glass-panel"
        style={{
          padding: "16px 20px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "16px",
          flexWrap: "wrap",
          marginBottom: "24px",
        }}
      >
        <div style={{ flex: 1, minWidth: "260px" }}>
          <div className="glass-input-wrapper">
            <span className="glass-input-icon">
              <Search size={16} />
            </span>
            <input
              className="glass-input has-icon"
              placeholder="Search evaluations by keyword, sector, or finding…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Filter size={14} style={{ color: "var(--text-muted)" }} />
          <span style={{ fontSize: "11px", fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
            VERDICT:
          </span>
          {["ALL", "GO", "PIVOT", "NO-GO"].map((filter) => (
            <button
              key={filter}
              type="button"
              onClick={() => setStatusFilter(filter)}
              className={`sector-pill ${statusFilter === filter ? "active" : ""}`}
              style={{ fontSize: "11px", padding: "4px 10px" }}
            >
              {filter}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="spinner-row" style={{ padding: "40px 0" }}>
          <Loader2 size={24} className="spin text-violet" />
          <span>Retrieving archived strategic dossiers…</span>
        </div>
      ) : filtered.length === 0 ? (
        <Empty
          icon={<ClipboardCheck size={26} />}
          text="No work orders match your search criteria."
        />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {filtered.map((order) => (
            <div
              key={order.id}
              className="glass-card glass-card--interactive"
              onClick={() => open(order.id)}
              style={{ padding: "18px 22px" }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  justifyContent: "space-between",
                  gap: "16px",
                  flexWrap: "wrap",
                }}
              >
                <div style={{ display: "flex", gap: "14px", flex: 1, minWidth: "280px" }}>
                  <div
                    style={{
                      width: "40px",
                      height: "40px",
                      borderRadius: "10px",
                      background: "rgba(139, 92, 255, 0.15)",
                      border: "1px solid rgba(139, 92, 255, 0.3)",
                      display: "grid",
                      placeItems: "center",
                      color: "var(--violet-bright)",
                      flexShrink: 0,
                    }}
                  >
                    <BrainCircuit size={18} />
                  </div>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                      {order.category && (
                        <span className="grounded-tag">
                          {order.category}
                        </span>
                      )}
                      <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--text-muted)" }}>
                        {new Date(order.created_at).toLocaleDateString("en-IN", {
                          day: "numeric",
                          month: "short",
                          year: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                    </div>
                    <h3 style={{ fontSize: "15px", fontWeight: 600, color: "#FFFFFF", marginBottom: "4px" }}>
                      {order.command}
                    </h3>
                    {order.headline && (
                      <p style={{ fontSize: "12.5px", color: "var(--text-secondary)" }}>
                        {order.headline}
                      </p>
                    )}
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
                  <div style={{ textAlign: "right" }}>
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: "10px", color: "var(--text-muted)" }}>
                      CONFIDENCE
                    </div>
                    <div style={{ fontSize: "15px", fontWeight: 700, color: "var(--violet-bright)" }}>
                      {order.confidence}%
                    </div>
                  </div>
                  <VerdictSignal verdict={order.recommendation} />
                  <ArrowRight size={16} style={{ color: "var(--violet-bright)" }} />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {selected && <WorkOrderModal order={selected} onClose={() => setSelected(null)} />}
    </Layout>
  );
}
