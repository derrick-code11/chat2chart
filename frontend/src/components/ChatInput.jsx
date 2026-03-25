import { useRef, useState } from "react";

export default function ChatInput({
  datasetName,
  disabled,
  onSend,
  onNewDataset,
  prefill,
  onPrefillConsumed,
}) {
  const [text, setText] = useState(prefill ?? "");
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  // Apply prefill when it changes from parent
  if (prefill && text !== prefill) {
    setText(prefill);
    onPrefillConsumed?.();
  }

  function adjustHeight() {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 148) + "px";
  }

  function handleChange(e) {
    setText(e.target.value);
    adjustHeight();
  }

  function handleSubmit() {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }

  const canSend = text.trim().length > 0 && !disabled;

  return (
    <div style={{ padding: "8px 16px 16px" }}>
      {/* Dataset pill */}
      {datasetName && (
        <div style={{ marginBottom: 6, display: "flex", alignItems: "center", gap: 6 }}>
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 5,
              fontSize: 11,
              fontFamily: '"Geist Mono", monospace',
              color: "#107A4D",
              backgroundColor: "rgba(16, 122, 77, 0.07)",
              border: "1px solid rgba(16, 122, 77, 0.18)",
              borderRadius: 3,
              padding: "2px 8px",
              maxWidth: 240,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true">
              <rect x="1" y="1" width="8" height="8" rx="1" stroke="currentColor" strokeWidth="1.2" />
              <path d="M1 4h8" stroke="currentColor" strokeWidth="1.2" />
            </svg>
            {datasetName}
          </span>
          {onNewDataset && (
            <>
              <button
                onClick={() => fileInputRef.current?.click()}
                style={{
                  fontSize: 11,
                  color: "#9A9A8A",
                  backgroundColor: "transparent",
                  border: "none",
                  cursor: "pointer",
                  padding: 0,
                  fontFamily: "Inter, sans-serif",
                }}
              >
                Change
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv,.xlsx,.xls"
                style={{ display: "none" }}
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) onNewDataset(f);
                  e.target.value = "";
                }}
              />
            </>
          )}
        </div>
      )}

      {/* Input row */}
      <div
        style={{
          display: "flex",
          alignItems: "flex-end",
          gap: 8,
          backgroundColor: "#fff",
          border: "1px solid #D4D0CA",
          borderRadius: 6,
          padding: "10px 12px",
        }}
      >
        <textarea
          ref={textareaRef}
          value={text}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about your data…"
          disabled={disabled}
          rows={1}
          style={{
            flex: 1,
            resize: "none",
            border: "none",
            outline: "none",
            fontSize: 14,
            fontFamily: "Inter, sans-serif",
            color: "#2A2A2A",
            backgroundColor: "transparent",
            lineHeight: 1.55,
          }}
        />
        <button
          onClick={handleSubmit}
          disabled={!canSend}
          aria-label="Send"
          style={{
            flexShrink: 0,
            width: 30,
            height: 30,
            borderRadius: 4,
            backgroundColor: canSend ? "#2A2A2A" : "#E4E0DA",
            border: "none",
            cursor: canSend ? "pointer" : "not-allowed",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            transition: "background-color 0.12s",
          }}
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
            <path
              d="M6 1v10M2 5l4-4 4 4"
              stroke={canSend ? "#F1EFEB" : "#9A9A8A"}
              strokeWidth="1.5"
              strokeLinecap="square"
            />
          </svg>
        </button>
      </div>
    </div>
  );
}
