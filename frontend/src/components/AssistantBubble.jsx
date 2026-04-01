import { useState } from "react";
import { api } from "../lib/api";
import ChartCard from "./ChartCard";

function ExportToolbar({ message }) {
  const [exporting, setExporting] = useState(false);
  const [copied, setCopied] = useState(false);

  async function handleSavePng() {
    setExporting(true);
    try {
      const blob = await api.messages.exportPng(message.id);
      if (!blob) return;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "chart.png";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      // best-effort
    } finally {
      setExporting(false);
    }
  }

  function handleCopyData() {
    const rows = message.chart_spec?.data?.rows;
    if (!rows) return;
    navigator.clipboard.writeText(JSON.stringify(rows, null, 2)).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div className="flex items-center gap-3 mt-1.5 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
      <button
        type="button"
        onClick={handleSavePng}
        disabled={exporting}
        className="flex items-center gap-1 text-[11px] text-brand-muted hover:text-brand-dark transition-colors disabled:opacity-50"
      >
        <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
          <path d="M3 10v2.5a.5.5 0 00.5.5h9a.5.5 0 00.5-.5V10M8 2v8M5 7l3 3 3-3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        {exporting ? "Saving…" : "Save as PNG"}
      </button>
      <button
        type="button"
        onClick={handleCopyData}
        className="flex items-center gap-1 text-[11px] text-brand-muted hover:text-brand-dark transition-colors"
      >
        <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
          <rect x="5" y="5" width="7.5" height="8.5" rx="1" stroke="currentColor" strokeWidth="1.3" />
          <path d="M10.5 5V3.5a1 1 0 00-1-1H4a1 1 0 00-1 1V11a1 1 0 001 1h1.5" stroke="currentColor" strokeWidth="1.3" />
        </svg>
        {copied ? "Copied!" : "Copy data"}
      </button>
    </div>
  );
}

function hasRenderableChart(spec) {
  return (
    spec &&
    typeof spec === "object" &&
    spec.type &&
    Array.isArray(spec.data?.rows) &&
    spec.data.rows.length > 0
  );
}

export default function AssistantBubble({ message }) {
  const hasChart = hasRenderableChart(message.chart_spec);
  return (
    <div className="mb-5">
      {message.content && (
        <p className={`text-sm text-brand-dark leading-[1.65] ${hasChart ? "mb-2.5" : ""}`}>
          {message.content}
        </p>
      )}
      {hasChart && (
        <div className="group">
          <div className="bg-surface border border-chart-border rounded-[6px] px-4 pt-4 pb-2.5 overflow-hidden">
            <ChartCard spec={message.chart_spec} />
          </div>
          <ExportToolbar message={message} />
        </div>
      )}
    </div>
  );
}
