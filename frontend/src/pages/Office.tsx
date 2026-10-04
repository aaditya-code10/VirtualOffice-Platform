import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Users, Loader2 } from "lucide-react";

import { api, type Agent } from "../api";
import { Empty, Header, Layout } from "../components/Layout";
import { AgentCard } from "../components/workforce/AgentCard";

export default function Office() {
  const navigate = useNavigate();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .getAgents()
      .then(setAgents)
      .catch(() => setAgents([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <Layout>
      <Header
        title="AI Digital Workforce & Workstations"
        subtitle="Autonomous digital workforce roster. Monitor each C-suite specialist's cognition, focus remit, and task assignments."
      />

      {loading && (
        <div className="spinner-row" style={{ padding: "40px 0" }}>
          <Loader2 size={24} className="spin text-violet" />
          <span>Connecting to autonomous agent workstations…</span>
        </div>
      )}

      {!loading && agents.length === 0 && (
        <Empty icon={<Users size={24} />} text="No specialized agents provisioned for this workspace." />
      )}

      <div className="floorplan-container">
        {agents.map((agent) => (
          <AgentCard
            key={agent.id}
            agent={agent}
            onClick={() => navigate(`/agents/${agent.key}`)}
          />
        ))}
      </div>
    </Layout>
  );
}
