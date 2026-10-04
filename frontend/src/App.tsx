import { Navigate, Route, Routes } from "react-router-dom";

import { useAuth } from "./auth";

import AgentWorkspace from "./pages/AgentWorkspace";
import Analytics from "./pages/Analytics";
import Approvals from "./pages/Approvals";
import CommandCenter from "./pages/CommandCenter";
import CompanyProfile from "./pages/CompanyProfile";
import Knowledge from "./pages/Knowledge";
import Login from "./pages/Login";
import Office from "./pages/Office";
import Reports from "./pages/Reports";
import Settings from "./pages/Settings";
import WorkOrders from "./pages/WorkOrders";

export default function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="boot-screen">
        <span className="spinner" aria-hidden />
        <p>Starting the virtual office…</p>
      </div>
    );
  }

  if (!user) {
    return <Login />;
  }

  return (
    <Routes>
      <Route path="/" element={<CommandCenter />} />
      <Route path="/office" element={<Office />} />
      <Route path="/agents/:agentKey" element={<AgentWorkspace />} />
      <Route path="/work-orders" element={<WorkOrders />} />
      <Route path="/knowledge" element={<Knowledge />} />
      <Route path="/analytics" element={<Analytics />} />
      <Route path="/reports" element={<Reports />} />
      <Route path="/approvals" element={<Approvals />} />
      <Route path="/company" element={<CompanyProfile />} />
      <Route path="/settings" element={<Settings />} />
      <Route
        path="*"
        element={<Navigate to="/" replace />}
      />
    </Routes>
  );
}