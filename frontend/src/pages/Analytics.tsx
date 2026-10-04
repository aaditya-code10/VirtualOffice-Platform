import { useCallback, useEffect, useState } from "react";
import { BarChart3, Plus, TrendingUp } from "lucide-react";

import { ApiError, api, type Analytics as AnalyticsData } from "../api";
import { useCanAdminister } from "../auth";
import { LineChart } from "../components/Charts";
import { Delta } from "../components/Delta";
import { Empty, ErrorBanner, Header, Layout } from "../components/Layout";

const UNITS = ["number", "currency", "percent", "score"] as const;

function currentPeriod(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

export default function Analytics() {
  const canEdit = useCanAdminister();
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [activeSeries, setActiveSeries] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [draft, setDraft] = useState({
    key: "",
    label: "",
    period: currentPeriod(),
    value: "",
    unit: "number" as (typeof UNITS)[number],
  });

  const load = useCallback(async () => {
    try {
      const analytics = await api.getAnalytics();
      setData(analytics);
      setActiveSeries((prev) => prev ?? analytics.series[0]?.key ?? null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load analytics.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function addMetric() {
    const numeric = Number(draft.value);
    if (!draft.key.trim() || Number.isNaN(numeric)) {
      setError("Provide a metric key and a numeric value.");
      return;
    }
    try {
      await api.upsertMetric({
        key: draft.key.trim().toLowerCase().replace(/\s+/g, "_"),
        label: draft.label.trim() || draft.key.trim(),
        period: draft.period,
        value: numeric,
        unit: draft.unit,
      });
      setDraft({ ...draft, key: "", label: "", value: "" });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save that metric.");
    }
  }

  const series = data?.series.find((s) => s.key === activeSeries) ?? data?.series[0];

  return (
    <Layout>
      <Header
        title="Enterprise Telemetry & Performance Analytics"
        subtitle="Real-time KPI metrics, financial forecasts, and historical operating data powering agent evaluations."
      />

      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

      {/* ── 1. Telemetry Health & KPI Cards Grid ───────────────────────── */}
      {data && data.kpis.length === 0 ? (
        <Empty
          icon={<BarChart3 size={26} />}
          text="No operating metrics recorded yet. Record a datapoint below to activate KPIs and trend curves."
        />
      ) : (
        <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px", marginBottom: "24px" }}>
          {/* Health Index Card */}
          <div className="apex-kpi-card" style={{ borderColor: "rgba(139, 92, 255, 0.4)", background: "rgba(139, 92, 255, 0.08)" }}>
            <span className="apex-kpi-label" style={{ color: "var(--violet-bright)" }}>
              HEALTH EVALUATION SCORE
            </span>
            <div className="apex-kpi-value" style={{ color: "var(--success)" }}>
              {data?.health_score ?? 85}%
            </div>
            <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
              Aggregated from operational & financial telemetry
            </span>
          </div>

          {(data?.kpis ?? []).map((kpi) => (
            <div className="apex-kpi-card" key={kpi.key}>
              <span className="apex-kpi-label">{kpi.label.toUpperCase()}</span>
              <div className="apex-kpi-value">{kpi.display}</div>
              <Delta kpi={kpi} />
            </div>
          ))}
        </section>
      )}

      {/* ── 2. Glowing Chart Section ───────────────────────────────────── */}
      {series && (
        <section className="glass-panel" style={{ padding: "24px", marginBottom: "24px" }}>
          <div className="panel-head" style={{ borderBottom: "1px solid var(--glass-border)", paddingBottom: "14px", marginBottom: "20px" }}>
            <h4 style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "16px", fontWeight: 700, color: "#FFFFFF" }}>
              <TrendingUp size={18} style={{ color: "var(--violet-bright)" }} /> {series.label} Telemetry Trend
            </h4>

            {/* Series Selector Pills */}
            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              {data?.series.map((s) => (
                <button
                  key={s.key}
                  type="button"
                  onClick={() => setActiveSeries(s.key)}
                  className={`sector-pill ${s.key === activeSeries ? "active" : ""}`}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>

          <LineChart values={series.values} labels={series.periods} unit={series.unit} />
        </section>
      )}

      {/* ── 3. Add Telemetry Datapoint ─────────────────────────────────── */}
      {canEdit && (
        <section className="glass-panel" style={{ padding: "24px" }}>
          <div className="panel-head">
            <h2>Record Operational Datapoint</h2>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "12px", alignItems: "flex-end" }}>
            <div className="form-field">
              <label className="form-label">METRIC KEY</label>
              <input
                className="glass-input"
                placeholder="e.g. gross_revenue"
                value={draft.key}
                onChange={(e) => setDraft({ ...draft, key: e.target.value })}
              />
            </div>

            <div className="form-field">
              <label className="form-label">DISPLAY LABEL</label>
              <input
                className="glass-input"
                placeholder="e.g. Gross Monthly Revenue"
                value={draft.label}
                onChange={(e) => setDraft({ ...draft, label: e.target.value })}
              />
            </div>

            <div className="form-field">
              <label className="form-label">PERIOD (YYYY-MM)</label>
              <input
                className="glass-input"
                value={draft.period}
                onChange={(e) => setDraft({ ...draft, period: e.target.value })}
              />
            </div>

            <div className="form-field">
              <label className="form-label">NUMERIC VALUE</label>
              <input
                className="glass-input"
                type="number"
                placeholder="50000"
                value={draft.value}
                onChange={(e) => setDraft({ ...draft, value: e.target.value })}
              />
            </div>

            <div className="form-field">
              <label className="form-label">UNIT</label>
              <select
                className="glass-input"
                value={draft.unit}
                onChange={(e) => setDraft({ ...draft, unit: e.target.value as (typeof UNITS)[number] })}
                style={{ background: "#080912", color: "#FFFFFF" }}
              >
                <option value="number">Number</option>
                <option value="currency">Currency (₹)</option>
                <option value="percent">Percentage (%)</option>
                <option value="score">Score (0-100)</option>
              </select>
            </div>

            <button
              type="button"
              className="btn-primary"
              onClick={addMetric}
              style={{ height: "44px" }}
            >
              <Plus size={16} /> Record Datapoint
            </button>
          </div>
        </section>
      )}
    </Layout>
  );
}
