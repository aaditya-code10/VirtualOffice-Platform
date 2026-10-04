import { useEffect, useState } from "react";
import { Download, FileText } from "lucide-react";

import { api, type Report } from "../api";
import { Empty, Header, Layout } from "../components/Layout";

export default function Reports() {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .getReports()
      .then(setReports)
      .catch(() => setReports([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <Layout>
      <Header
        title="Executive Strategic Dossiers"
        subtitle="Formal advisory deliverables synthesized from multi-agent consultations, with departmental perspectives, risk matrices, and next actions."
      />

      {!loading && reports.length === 0 && (
        <Empty
          icon={<FileText size={26} />}
          text="No executive dossiers generated yet. Run an evaluation from the Command Center."
        />
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
        {reports.map((report) => (
          <article
            key={report.id}
            className="glass-panel glass-panel--elevated"
            style={{ padding: "28px" }}
          >
            {/* Dossier Header */}
            <div
              style={{
                display: "flex",
                alignItems: "flex-start",
                justifyContent: "space-between",
                gap: "20px",
                marginBottom: "20px",
                flexWrap: "wrap",
              }}
            >
              <div style={{ flex: 1, minWidth: "300px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
                  <span className="grounded-tag">
                    {report.code}
                  </span>
                  <span style={{ fontSize: "11px", fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
                    STRATEGIC DOSSIER · {report.date}
                  </span>
                </div>
                <h3 style={{ fontFamily: "var(--font-display)", fontSize: "20px", fontWeight: 700, color: "#FFFFFF", marginBottom: "6px" }}>
                  {report.title}
                </h3>
                <p style={{ fontSize: "14px", color: "var(--text-secondary)", lineHeight: "1.6" }}>
                  {report.summary}
                </p>
              </div>

              {/* Viability Pill */}
              <div
                style={{
                  background: "rgba(139, 92, 255, 0.12)",
                  border: "1px solid rgba(139, 92, 255, 0.35)",
                  borderRadius: "var(--radius-md)",
                  padding: "16px 20px",
                  minWidth: "160px",
                  textAlign: "center",
                }}
              >
                <span style={{ fontFamily: "var(--font-mono)", fontSize: "10px", fontWeight: 700, color: "var(--text-muted)", letterSpacing: "0.08em", display: "block", marginBottom: "4px" }}>
                  VIABILITY SCORE
                </span>
                <div style={{ fontSize: "32px", fontFamily: "var(--font-display)", fontWeight: 800, color: "var(--success)", lineHeight: 1 }}>
                  {report.health_score}%
                </div>
                <div style={{ width: "100%", height: "4px", background: "rgba(255, 255, 255, 0.1)", borderRadius: "2px", overflow: "hidden", marginTop: "8px" }}>
                  <div style={{ width: `${report.health_score}%`, height: "100%", background: "var(--success)" }} />
                </div>
              </div>
            </div>

            {/* Department Findings Grid */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "12px", marginBottom: "20px" }}>
              {report.findings.map((finding, i) => (
                <div
                  key={i}
                  className="glass-card"
                  style={{ padding: "14px 16px" }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                    <strong style={{ fontSize: "12.5px", color: "var(--violet-bright)" }}>
                      {finding.department}
                    </strong>
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: "10.5px", color: "var(--text-muted)" }}>
                      {finding.agent}
                    </span>
                  </div>
                  <p style={{ fontSize: "12.5px", color: "var(--text-secondary)", lineHeight: "1.5", margin: 0 }}>
                    {finding.text}
                  </p>
                </div>
              ))}
            </div>

            {/* Recommendation & Action Roadmap */}
            {report.recommendation && (
              <div
                style={{
                  background: "rgba(255, 255, 255, 0.04)",
                  border: "1px solid var(--glass-border)",
                  borderRadius: "var(--radius-sm)",
                  padding: "16px 20px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  flexWrap: "wrap",
                  gap: "12px",
                }}
              >
                <div>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: "10.5px", color: "var(--text-muted)" }}>
                    EXECUTIVE RECOMMENDATION
                  </span>
                  <div style={{ fontSize: "14px", fontWeight: 600, color: "#FFFFFF", marginTop: "2px" }}>
                    {report.recommendation}
                  </div>
                </div>

                <a
                  href={api.exportReportUrl(report.id)}
                  download
                  className="glass-btn glass-btn--secondary glass-btn--sm"
                >
                  <Download size={13} />
                  <span>Download Complete Dossier</span>
                </a>
              </div>
            )}
          </article>
        ))}
      </div>
    </Layout>
  );
}
