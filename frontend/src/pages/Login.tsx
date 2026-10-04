import { useEffect, useState, type FormEvent } from "react";
import { ArrowRight, Loader2, Sparkles, Lock, Mail, Building, User as UserIcon } from "lucide-react";
import { ApiError } from "../api";
import { useAuth } from "../auth";
import { BrandLogo } from "../components/brand/BrandLogo";
import { AnimatedBackground } from "../components/background/AnimatedBackground";

export default function Login() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Cinematic Intro Sequence Stage (0: Black -> 1: Glow -> 2: Brand Reveal -> 3: Full Glass Interactive)
  const [introStage, setIntroStage] = useState(0);

  // Form State
  const [email, setEmail] = useState("owner@virtualoffice.ai");
  const [password, setPassword] = useState("password123");
  const [fullName, setFullName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [industry, setIndustry] = useState("");

  useEffect(() => {
    // Cinematic timed sequence (completes naturally in ~1.8 seconds)
    const t1 = setTimeout(() => setIntroStage(1), 200);  // Ambient violet glow
    const t2 = setTimeout(() => setIntroStage(2), 700);  // Logo halo & title
    const t3 = setTimeout(() => setIntroStage(3), 1400); // Glass panel slides in & interactive
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
    };
  }, []);

  function skipAnimation() {
    setIntroStage(3);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register({
          email,
          password,
          full_name: fullName,
          company_name: companyName,
          industry: industry || undefined,
        });
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Authentication failed.");
    } finally {
      setBusy(false);
    }
  }

  function fillDemo(demoEmail: string, demoPass: string) {
    setEmail(demoEmail);
    setPassword(demoPass);
    setError(null);
  }

  return (
    <div className="cinematic-auth-root">
      <AnimatedBackground />

      {/* Skip Animation helper */}
      {introStage < 3 && (
        <button
          type="button"
          className="cinematic-skip-btn"
          onClick={skipAnimation}
        >
          Skip Intro ➔
        </button>
      )}

      <div
        className="auth-glass-container"
        style={{
          opacity: introStage >= 2 ? 1 : 0,
          transform: introStage >= 3 ? "translateY(0) scale(1)" : "translateY(24px) scale(0.96)",
          transition: "all 0.6s cubic-bezier(0.16, 1, 0.3, 1)",
        }}
      >
        <div className="auth-glass-card">
          {/* Top Brand Identity Block */}
          <div className="auth-brand-center">
            <BrandLogo size="lg" />
            <p className="auth-tagline">
              Autonomous Executive Advisory Board & Digital Workforce
            </p>
          </div>

          {error && (
            <div className="error-banner" role="alert" style={{ marginBottom: "16px" }}>
              <span>{error}</span>
            </div>
          )}

          {/* Form */}
          <form className="auth-form" onSubmit={handleSubmit}>
            {mode === "register" && (
              <>
                <div className="form-field">
                  <label className="form-label" htmlFor="fullName">OPERATOR FULL NAME</label>
                  <div className="glass-input-wrapper">
                    <span className="glass-input-icon"><UserIcon size={16} /></span>
                    <input
                      id="fullName"
                      className="glass-input has-icon"
                      placeholder="e.g. Alex Morgan"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <div className="form-field">
                  <label className="form-label" htmlFor="companyName">ENTERPRISE WORKSPACE NAME</label>
                  <div className="glass-input-wrapper">
                    <span className="glass-input-icon"><Building size={16} /></span>
                    <input
                      id="companyName"
                      className="glass-input has-icon"
                      placeholder="e.g. Northwind Dynamics"
                      value={companyName}
                      onChange={(e) => setCompanyName(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <div className="form-field">
                  <label className="form-label" htmlFor="industry">INDUSTRY SECTOR</label>
                  <div className="glass-input-wrapper">
                    <input
                      id="industry"
                      className="glass-input"
                      placeholder="e.g. Education, SaaS, Logistics"
                      value={industry}
                      onChange={(e) => setIndustry(e.target.value)}
                    />
                  </div>
                </div>
              </>
            )}

            <div className="form-field">
              <label className="form-label" htmlFor="email">EXECUTIVE EMAIL</label>
              <div className="glass-input-wrapper">
                <span className="glass-input-icon"><Mail size={16} /></span>
                <input
                  id="email"
                  type="email"
                  className="glass-input has-icon"
                  placeholder="founder@venture.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="form-field">
              <label className="form-label" htmlFor="password">ACCESS KEY / PASSWORD</label>
              <div className="glass-input-wrapper">
                <span className="glass-input-icon"><Lock size={16} /></span>
                <input
                  id="password"
                  type="password"
                  className="glass-input has-icon"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              className="auth-submit-btn"
              disabled={busy}
            >
              {busy ? (
                <>
                  <Loader2 size={16} className="spin" />
                  <span>Authorizing Digital Workspace…</span>
                </>
              ) : (
                <>
                  <Sparkles size={16} />
                  <span>{mode === "login" ? "Enter Command Center" : "Initialize Workspace"}</span>
                  <ArrowRight size={14} />
                </>
              )}
            </button>
          </form>

          {/* Quick Demo Accounts */}
          <div className="auth-demo-accounts">
            <span className="demo-title">INSTANT ACCESS DEMO CREDENTIALS:</span>
            <div className="demo-pills">
              <button
                type="button"
                className="demo-pill-btn"
                onClick={() => fillDemo("owner@virtualoffice.ai", "password123")}
              >
                Owner Demo
              </button>
              <button
                type="button"
                className="demo-pill-btn"
                onClick={() => fillDemo("founder@northwind.io", "demo1234")}
              >
                Founder Demo
              </button>
            </div>
          </div>

          {/* Toggle Login / Register */}
          <div style={{ marginTop: "16px", textAlign: "center" }}>
            <button
              type="button"
              onClick={() => {
                setMode(mode === "login" ? "register" : "login");
                setError(null);
              }}
              style={{
                background: "none",
                border: "none",
                color: "var(--violet-bright)",
                fontSize: "12px",
                cursor: "pointer",
                fontWeight: 500,
              }}
            >
              {mode === "login"
                ? "Need to provision a new workspace? Register here"
                : "Already have workspace credentials? Sign in"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
