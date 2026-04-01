import { useCallback, useEffect, useRef, useState } from "react";
import { humanizeErrorMessage } from "../lib/apiErrors";
import { api } from "../lib/api";
import AssistantBubble from "./AssistantBubble";
import ChatInput from "./ChatInput";
import DatasetPeekToolbar from "./DatasetPeekToolbar";
import DatasetReadyPrompt from "./DatasetReadyPrompt";
import DatasetViewer from "./DatasetViewer";
import Spinner from "./Spinner";
import ThinkingDots from "./ThinkingDots";
import UserBubble from "./UserBubble";

export default function ConversationView({
  conv,
  initialDataset,
  onConversationUpdated,
}) {
  const [messages, setMessages] = useState([]);
  const [attachedDatasets, setAttachedDatasets] = useState(
    initialDataset ? [initialDataset] : [],
  );
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState(null);
  const [prefill, setPrefill] = useState(null);
  const [showDataViewer, setShowDataViewer] = useState(false);
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
    (d) => d.dataset_id === conv.current_dataset_id,
  );

  const handleSend = useCallback(
    async (text) => {
      const isFirstMessage = messages.length === 0;
      const optimisticId = `pending-${Date.now()}`;
      const optimisticMsg = { id: optimisticId, role: "user", content: text };

      setSending(true);
      setSendError(null);
      setMessages((prev) => [...prev, optimisticMsg]);

      try {
        const result = await api.conversations.createMessage(conv.id, {
          content: text,
        });
        if (!result) return;
        setMessages((prev) =>
          prev
            .filter((m) => m.id !== optimisticId)
            .concat([result.user_message, result.assistant_message]),
        );

        const patch = result.conversation
          ? { id: conv.id, ...result.conversation }
          : { id: conv.id };

        if (isFirstMessage) {
          const title = text.length > 50 ? text.slice(0, 50) + "…" : text;
          try {
            await api.conversations.patch(conv.id, { title });
            patch.title = title;
          } catch {
            // title update is best-effort
          }
        }

        onConversationUpdated?.(patch);
      } catch (e) {
        setMessages((prev) => prev.filter((m) => m.id !== optimisticId));
        setSendError(
          humanizeErrorMessage(e?.message, {
            code: e?.code,
            status: e?.status,
          }),
        );
      } finally {
        setSending(false);
      }
    },
    [conv.id, messages.length, onConversationUpdated],
  );

  const handleNewDataset = useCallback(
    async (file) => {
      try {
        const dataset = await api.datasets.upload(file);
        if (!dataset) return;
        await api.conversations.attachDataset(conv.id, dataset.id);
        await api.conversations.patch(conv.id, {
          current_dataset_id: dataset.id,
        });
        const dsData = await api.conversations.listDatasets(conv.id);
        if (dsData) setAttachedDatasets(dsData.items ?? []);
        onConversationUpdated?.({
          id: conv.id,
          current_dataset_id: dataset.id,
        });
      } catch (e) {
        setSendError(
          humanizeErrorMessage(e?.message, {
            code: e?.code,
            status: e?.status,
          }),
        );
      }
    },
    [conv.id, onConversationUpdated],
  );

  const showDatasetPrompt = !loading && messages.length === 0 && currentDataset;

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto relative">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <Spinner />
          </div>
        ) : showDatasetPrompt ? (
          <div className="max-w-[720px] mx-auto px-6 pt-7 pb-4 w-full min-h-full flex flex-col">
            <DatasetPeekToolbar
              className="mb-3 shrink-0"
              filename={currentDataset.original_filename}
              showViewer={showDataViewer}
              onToggle={() => setShowDataViewer((v) => !v)}
            />
            {showDataViewer && currentDataset && (
              <DatasetViewer
                datasetId={currentDataset.dataset_id}
                onClose={() => setShowDataViewer(false)}
              />
            )}
            <div className="flex-1 flex flex-col min-h-0">
              <DatasetReadyPrompt
                datasetName={currentDataset.original_filename}
                onPromptClick={(p) => setPrefill(p)}
              />
            </div>
          </div>
        ) : (
          <div className="max-w-[720px] mx-auto px-6 pt-7 pb-4">
            {currentDataset && (
              <DatasetPeekToolbar
                className="mb-4"
                filename={currentDataset.original_filename}
                showViewer={showDataViewer}
                onToggle={() => setShowDataViewer((v) => !v)}
              />
            )}
            {showDataViewer && currentDataset && (
              <DatasetViewer
                datasetId={currentDataset.dataset_id}
                onClose={() => setShowDataViewer(false)}
              />
            )}
            {messages.map((m) =>
              m.role === "user" ? (
                <UserBubble key={m.id} message={m} />
              ) : (
                <AssistantBubble key={m.id} message={m} />
              ),
            )}
            {sending && <ThinkingDots />}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {sendError && (
        <div className="px-6 py-2 bg-brand-error/[0.07] border-t border-brand-error/15">
          <p className="text-[13px] text-brand-error max-w-[720px] mx-auto">
            {sendError}
          </p>
        </div>
      )}

      <div className="max-w-[768px] mx-auto w-full">
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
