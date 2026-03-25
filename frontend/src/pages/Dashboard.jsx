import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import ConversationView from "../components/ConversationView";
import EmptyState from "../components/EmptyState";
import Sidebar from "../components/Sidebar";
import { clearToken } from "../lib/auth";
import { api } from "../lib/api";

export default function Dashboard() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId] = useState(null);
  const [initialDataset, setInitialDataset] = useState(null);
  const [bootstrapping, setBootstrapping] = useState(true);
  const [bootError, setBootError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    Promise.all([api.me(), api.conversations.list()])
      .then(([userData, convData]) => {
        if (cancelled) return;
        setUser(userData);
        const items = convData?.items ?? [];
        setConversations(items);
        if (items.length > 0) setActiveConvId(items[0].id);
      })
      .catch(() => {
        if (cancelled) return;
        clearToken();
        navigate("/", { replace: true });
      })
      .finally(() => {
        if (!cancelled) setBootstrapping(false);
      });

    return () => {
      cancelled = true;
    };
  }, [navigate]);

  function handleSignOut() {
    clearToken();
    navigate("/", { replace: true });
  }

  function handleNewChat() {
    setActiveConvId(null);
    setInitialDataset(null);
  }

  function handleConversationCreated(conv, dataset) {
    setConversations((prev) => [conv, ...prev]);
    setActiveConvId(conv.id);
    setInitialDataset(dataset ?? null);
  }

  function handleConversationUpdated(patch) {
    setConversations((prev) =>
      prev.map((c) => (c.id === patch.id ? { ...c, ...patch } : c))
    );
  }

  const activeConv = conversations.find((c) => c.id === activeConvId) ?? null;

  if (bootstrapping) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: "100vh",
          backgroundColor: "#F1EFEB",
        }}
      >
        <svg className="spin" width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <circle
            cx="12"
            cy="12"
            r="9"
            stroke="#C4D8CB"
            strokeWidth="2.5"
            strokeDasharray="48"
            strokeDashoffset="16"
          />
        </svg>
      </div>
    );
  }

  if (bootError) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: "100vh",
          backgroundColor: "#F1EFEB",
        }}
      >
        <p style={{ fontSize: 14, color: "#C0392B", fontFamily: "Inter, sans-serif" }}>
          {bootError}
        </p>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden" }}>
      <Sidebar
        user={user}
        conversations={conversations}
        activeConvId={activeConvId}
        onSelect={(id) => {
          setActiveConvId(id);
          setInitialDataset(null);
        }}
        onNewChat={handleNewChat}
        onSignOut={handleSignOut}
      />

      <main
        style={{
          flex: 1,
          overflow: "hidden",
          backgroundColor: "#F1EFEB",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {activeConv ? (
          <ConversationView
            key={activeConv.id}
            conv={activeConv}
            initialDataset={initialDataset}
            onConversationUpdated={handleConversationUpdated}
          />
        ) : (
          <EmptyState onConversationCreated={handleConversationCreated} />
        )}
      </main>
    </div>
  );
}
