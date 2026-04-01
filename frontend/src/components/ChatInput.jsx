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
    <div className="px-4 pt-2 pb-4">
      {datasetName && (
        <div className="mb-1.5 flex items-center gap-1.5">
          <span className="inline-flex items-center gap-[5px] text-[11px] font-mono text-brand-accent bg-brand-accent/[0.07] border border-brand-accent/18 rounded-[3px] px-2 py-[2px] max-w-60 truncate">
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true">
              <rect x="1" y="1" width="8" height="8" rx="1" stroke="currentColor" strokeWidth="1.2" />
              <path d="M1 4h8" stroke="currentColor" strokeWidth="1.2" />
            </svg>
            {datasetName}
          </span>
          {onNewDataset && (
            <>
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="text-[11px] text-muted-light bg-transparent border-none p-0 hover:text-brand-dark"
              >
                Change
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv,.xlsx,.xls"
                className="hidden"
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

      <div className="flex items-end gap-2 bg-surface border border-brand-border rounded-[6px] px-3 py-2.5">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about your data…"
          disabled={disabled}
          rows={1}
          className="flex-1 resize-none border-none outline-none text-sm text-brand-dark bg-transparent leading-[1.55] placeholder:text-muted-light"
        />
        <button
          type="button"
          onClick={handleSubmit}
          disabled={!canSend}
          aria-label="Send"
          className={`shrink-0 w-[30px] h-[30px] rounded flex items-center justify-center border-none transition-colors duration-120 ${
            canSend ? "bg-brand-dark" : "bg-chart-border"
          }`}
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
            <path
              d="M6 1v10M2 5l4-4 4 4"
              stroke={canSend ? "var(--color-brand-bg)" : "var(--color-muted-light)"}
              strokeWidth="1.5"
              strokeLinecap="square"
            />
          </svg>
        </button>
      </div>
    </div>
  );
}
