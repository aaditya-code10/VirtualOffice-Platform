import { useEffect, useState, type FormEvent } from "react";
import { Building2, Loader2, Save, CheckCircle2 } from "lucide-react";

import { ApiError, api, type Company } from "../api";
import { useAuth, useCanAdminister } from "../auth";
import { ErrorBanner, Header, Layout } from "../components/Layout";

export default function CompanyProfile() {
  const { company, refreshCompany } = useAuth();
  const canEdit = useCanAdminister();
  const [form, setForm] = useState<Partial<Company>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (company) setForm(company);
  }, [company]);

  async function save(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      await api.updateCompany({
        name: form.name,
        industry: form.industry,
        target_market: form.target_market,
        core_services: form.core_services,
        primary_goal: form.primary_goal,
        currency: form.currency,
        headcount: form.headcount ? Number(form.headcount) : null,
      });
      await refreshCompany();
      setSaved(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not update company profile.");
    } finally {
      setBusy(false);
    }
  }

  const set = (key: keyof Company) => (e: { target: { value: string } }) =>
    setForm({ ...form, [key]: e.target.value });

  return (
    <Layout>
      <Header
        title="Enterprise Digital Twin & Context Engine"
        subtitle="This authoritative model of your business is injected into every specialist agent's prompt context for hyper-grounded advisory."
      />

      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

      {saved && (
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
          <span>Operational digital twin updated. Agents will ground subsequent evaluations on these parameters.</span>
        </div>
      )}

      <form className="glass-panel" onSubmit={save} style={{ padding: "30px" }}>
        <div className="panel-head" style={{ borderBottom: "1px solid var(--glass-border)", paddingBottom: "16px", marginBottom: "24px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <Building2 size={20} style={{ color: "var(--violet-bright)" }} />
            <h2 style={{ fontSize: "18px", color: "#FFFFFF" }}>Operational Twin Specification</h2>
          </div>
          <span className="grounded-tag">
            {company?.onboarding_complete ? "✓ CONTEXT ACTIVE" : "ONBOARDING"}
          </span>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px", marginBottom: "24px" }}>
          <div className="form-field">
            <label className="form-label">ENTERPRISE NAME</label>
            <input
              className="glass-input"
              value={form.name || ""}
              onChange={set("name")}
              placeholder="e.g. Apex Academy"
              required
              disabled={!canEdit}
            />
          </div>

          <div className="form-field">
            <label className="form-label">INDUSTRY / SECTOR</label>
            <input
              className="glass-input"
              value={form.industry || ""}
              onChange={set("industry")}
              placeholder="e.g. Education, SaaS, Quick Commerce"
              disabled={!canEdit}
            />
          </div>

          <div className="form-field">
            <label className="form-label">TARGET MARKET & GEOGRAPHY</label>
            <input
              className="glass-input"
              value={form.target_market || ""}
              onChange={set("target_market")}
              placeholder="e.g. Urban Class 8-12 students in Mumbai"
              disabled={!canEdit}
            />
          </div>

          <div className="form-field">
            <label className="form-label">PRIMARY GOAL (NEXT 12 MONTHS)</label>
            <input
              className="glass-input"
              value={form.primary_goal || ""}
              onChange={set("primary_goal")}
              placeholder="e.g. Reach ₹15L ARR with 40% margin"
              disabled={!canEdit}
            />
          </div>

          <div className="form-field" style={{ gridColumn: "1 / -1" }}>
            <label className="form-label">CORE SERVICES / VALUE PROPOSITION</label>
            <textarea
              className="glass-input"
              style={{ height: "90px", padding: "12px 16px", resize: "vertical" }}
              value={form.core_services || ""}
              onChange={set("core_services")}
              placeholder="e.g. Small-batch personalized tuition, experienced CBSE & ICSE faculty, comprehensive study materials…"
              disabled={!canEdit}
            />
          </div>
        </div>

        {canEdit && (
          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <button
              type="submit"
              className="btn-primary"
              disabled={busy}
            >
              {busy ? (
                <>
                  <Loader2 size={16} className="spin" />
                  <span>Synchronizing Twin…</span>
                </>
              ) : (
                <>
                  <Save size={16} />
                  <span>Update Digital Twin Context</span>
                </>
              )}
            </button>
          </div>
        )}
      </form>
    </Layout>
  );
}
