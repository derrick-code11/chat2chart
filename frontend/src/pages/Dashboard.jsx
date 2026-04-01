import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import ConversationView from "../components/ConversationView";
import EmptyState from "../components/EmptyState";
import Sidebar from "../components/Sidebar";
import Spinner from "../components/Spinner";
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

  async function handleDeleteConversation(id) {
    try {
      await api.conversations.delete(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (activeConvId === id) setActiveConvId(null);
    } catch {
      // conversation may already be gone
    }
  }

  function handleConversationUpdated(patch) {
    setConversations((prev) =>
      prev.map((c) => (c.id === patch.id ? { ...c, ...patch } : c))
    );
  }

  const activeConv = conversations.find((c) => c.id === activeConvId) ?? null;

  if (bootstrapping) {
    return (
      <div className="flex items-center justify-center h-screen bg-brand-bg">
        <Spinner size={24} />
      </div>
    );
  }

  if (bootError) {
    return (
      <div className="flex items-center justify-center h-screen bg-brand-bg">
        <p className="text-sm text-brand-error">{bootError}</p>
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        user={user}
        conversations={conversations}
        activeConvId={activeConvId}
        onSelect={(id) => {
          setActiveConvId(id);
          setInitialDataset(null);
        }}
        onNewChat={handleNewChat}
        onDelete={handleDeleteConversation}
        onSignOut={handleSignOut}
      />

      <main className="flex-1 overflow-hidden bg-brand-bg flex flex-col">
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
