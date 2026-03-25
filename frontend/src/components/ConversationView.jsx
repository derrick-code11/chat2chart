import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import ChartCard from "./ChartCard";
import ChatInput from "./ChatInput";

const STARTER_PROMPTS = [
  "Give me an overview of this data",
  "Show the distribution across categories",
  "What are the top values?",
];

function UserBubble({ message }) {
  return (
    <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 14 }}>
      <div
        style={{
          maxWidth: "68%",
          backgroundColor: "#2A2A2A",
          color: "#F1EFEB",
          padding: "10px 14px",
          borderRadius: "6px 6px 2px 6px",
          fontSize: 14,
          lineHeight: 1.55,
          fontFamily: "Inter, sans-serif",
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
        }}
      >
        {message.content}
      </div>
    </div>
  );
}

function AssistantBubble({ message }) {
  const hasChart = !!message.chart_spec;
  return (
    <div style={{ marginBottom: 20 }}>
      {message.content && (
        <p
          style={{
            fontSize: 14,
            color: "#2A2A2A",
            lineHeight: 1.65,
            marginBottom: hasChart ? 10 : 0,
            fontFamily: "Inter, sans-serif",
          }}
        >
          {message.content}
        </p>
      )}
      {hasChart && (
        <div
          style={{
            backgroundColor: "#fff",
            border: "1px solid #E4E0DA",
            borderRadius: 6,
            padding: "16px 16px 10px",
            overflow: "hidden",
          }}
        >
          <ChartCard spec={message.chart_spec} />
        </div>
      )}
    </div>
  );
}

function ThinkingDots() {
  return (
    <div
      style={{ display: "flex", gap: 4, alignItems: "center", marginBottom: 20, height: 20 }}
      aria-label="Generating chart…"
    >
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="pulse-dot"
          style={{ animationDelay: `${i * 0.18}s` }}
        />
      ))}
    </div>
  );
}

function DatasetReadyPrompt({ datasetName, onPromptClick }) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        height: "100%",
        textAlign: "center",
        padding: "0 24px",
      }}
    >
      <div
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 6,
          fontSize: 12,
          fontFamily: '"Geist Mono", monospace',
          color: "#107A4D",
          backgroundColor: "rgba(16, 122, 77, 0.07)",
          border: "1px solid rgba(16, 122, 77, 0.18)",
          borderRadius: 3,
          padding: "3px 10px",
          marginBottom: 16,
        }}
      >
        <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true">
          <rect x="1" y="1" width="8" height="8" rx="1" stroke="currentColor" strokeWidth="1.2" />
          <path d="M1 4h8" stroke="currentColor" strokeWidth="1.2" />
        </svg>
        {datasetName}
      </div>
      <p
        style={{
          fontSize: 15,
          fontWeight: 500,
          color: "#2A2A2A",
          marginBottom: 6,
          letterSpacing: "-0.01em",
        }}
      >
        Dataset ready — ask your first question
      </p>
      <p style={{ fontSize: 13, color: "#9A9A8A", marginBottom: 22, lineHeight: 1.6 }}>
        Describe what you want to see in plain English.
      </p>
      <div style={{ display: "flex", flexDirection: "column", gap: 6, width: "100%", maxWidth: 300 }}>
        {STARTER_PROMPTS.map((p) => (
          <button
            key={p}
            onClick={() => onPromptClick(p)}
            style={{
              fontSize: 13,
              color: "#2A2A2A",
              backgroundColor: "#fff",
              border: "1px solid #D4D0CA",
              borderRadius: 4,
              padding: "8px 14px",
              cursor: "pointer",
              textAlign: "left",
              fontFamily: "Inter, sans-serif",
              transition: "border-color 0.12s",
            }}
          >
            {p}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function ConversationView({ conv, initialDataset, onConversationUpdated }) {
  const [messages, setMessages] = useState([]);
  const [attachedDatasets, setAttachedDatasets] = useState(
    initialDataset ? [initialDataset] : []
  );
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState(null);
  const [prefill, setPrefill] = useState(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setSendError(null);

    Promise.all([
      api.conversations.listMessages(conv.id),
      api.conversations.listDatasets(conv.id),
    ])
      .then(([msgData, dsData]) => {
        if (cancelled) return;
        setMessages(msgData?.items ?? []);
        setAttachedDatasets(dsData?.items ?? []);
      })
      .catch(() => {
        if (!cancelled) setSendError("Failed to load conversation.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [conv.id]);

  useEffect(() => {
    if (!loading) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, sending, loading]);

  const currentDataset = attachedDatasets.find(
    (d) => d.dataset_id === conv.current_dataset_id
  );

  const handleSend = useCallback(
    async (text) => {
      setSending(true);
      setSendError(null);
      try {
        const result = await api.conversations.createMessage(conv.id, { content: text });
        if (!result) return;
        setMessages((prev) => [
          ...prev,
          result.user_message,
          result.assistant_message,
        ]);
        if (result.conversation) {
          onConversationUpdated?.({ id: conv.id, ...result.conversation });
        }
      } catch (e) {
        setSendError(e.message);
      } finally {
        setSending(false);
      }
    },
    [conv.id, onConversationUpdated]
  );

  const handleNewDataset = useCallback(
    async (file) => {
      try {
        const dataset = await api.datasets.upload(file);
        if (!dataset) return;
        await api.conversations.attachDataset(conv.id, dataset.id);
        await api.conversations.patch(conv.id, { current_dataset_id: dataset.id });
        const dsData = await api.conversations.listDatasets(conv.id);
        if (dsData) setAttachedDatasets(dsData.items ?? []);
        onConversationUpdated?.({
          id: conv.id,
          current_dataset_id: dataset.id,
        });
      } catch (e) {
        setSendError(e.message);
      }
    },
    [conv.id, onConversationUpdated]
  );

  const showDatasetPrompt = !loading && messages.length === 0 && currentDataset;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Message thread */}
      <div style={{ flex: 1, overflowY: "auto", position: "relative" }}>
        {loading ? (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
            }}
          >
            <svg
              className="spin"
              width="20"
              height="20"
              viewBox="0 0 20 20"
              fill="none"
              aria-hidden="true"
            >
              <circle
                cx="10"
                cy="10"
                r="7"
                stroke="#C4D8CB"
                strokeWidth="2"
                strokeDasharray="36"
                strokeDashoffset="12"
              />
            </svg>
          </div>
        ) : showDatasetPrompt ? (
          <DatasetReadyPrompt
            datasetName={currentDataset.original_filename}
            onPromptClick={(p) => setPrefill(p)}
          />
        ) : (
          <div
            style={{
              maxWidth: 720,
              margin: "0 auto",
              padding: "28px 24px 16px",
            }}
          >
            {messages.map((m) =>
              m.role === "user" ? (
                <UserBubble key={m.id} message={m} />
              ) : (
                <AssistantBubble key={m.id} message={m} />
              )
            )}
            {sending && <ThinkingDots />}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Error banner */}
      {sendError && (
        <div
          style={{
            padding: "8px 24px",
            backgroundColor: "rgba(192, 57, 43, 0.07)",
            borderTop: "1px solid rgba(192, 57, 43, 0.15)",
          }}
        >
          <p
            style={{
              fontSize: 13,
              color: "#C0392B",
              fontFamily: "Inter, sans-serif",
              maxWidth: 720,
              margin: "0 auto",
            }}
          >
            {sendError}
          </p>
        </div>
      )}

      {/* Chat input */}
      <div style={{ maxWidth: 720 + 48, margin: "0 auto", width: "100%" }}>
        <ChatInput
          datasetName={currentDataset?.original_filename}
          disabled={sending || loading}
          onSend={handleSend}
          onNewDataset={handleNewDataset}
          prefill={prefill}
          onPrefillConsumed={() => setPrefill(null)}
        />
      </div>
    </div>
  );
}
