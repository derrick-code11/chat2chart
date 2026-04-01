import { useEffect, useState } from "react";
import { api } from "../lib/api";
import Spinner from "./Spinner";

export default function DatasetViewer({ datasetId, onClose }) {
  const [dataset, setDataset] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!datasetId) return;
    let cancelled = false;

    (async () => {
      await Promise.resolve();
      if (cancelled) return;
      setLoading(true);
      setError(null);
      setDataset(null);
      try {
        const data = await api.datasets.get(datasetId);
        if (!cancelled) setDataset(data);
      } catch (e) {
        if (!cancelled) setError(e?.message ?? "Failed to load dataset");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [datasetId]);

  if (loading) {
    return (
      <div className="border border-chart-border rounded-lg bg-white p-6 mb-4">
        <div className="flex items-center justify-center py-8">
          <Spinner />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="border border-chart-border rounded-lg bg-white p-4 mb-4">
        <p className="text-[13px] text-brand-error">{error}</p>
      </div>
    );
  }

  if (!dataset) return null;

  const columns = dataset.columns ?? [];
  const rows = dataset.preview?.rows ?? [];
  const truncated = dataset.preview?.truncated ?? false;

  return (
    <div className="border border-chart-border rounded-lg bg-white mb-4 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-chart-border bg-surface">
        <div className="flex items-center gap-3">
          <span className="text-[13px] font-semibold text-brand-dark">
            {dataset.original_filename}
          </span>
          <span className="text-[11px] text-brand-muted">
            {dataset.row_count?.toLocaleString() ?? "?"} rows · {columns.length} columns
          </span>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="text-brand-muted hover:text-brand-dark transition-colors p-1 rounded"
          aria-label="Close viewer"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </button>
      </div>

      <div className="overflow-auto max-h-[60vh]">
        <table className="w-full text-[12px] font-[Inter,sans-serif] border-collapse">
          <thead>
            <tr className="sticky top-0 bg-surface z-10">
              {columns.map((col) => (
                <th
                  key={col.id}
                  className="text-left px-3 py-2 font-medium text-brand-dark border-b border-chart-border whitespace-nowrap"
                >
                  <div>{col.name}</div>
                  <div className="text-[10px] font-normal text-brand-muted">{col.inferred_type}</div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className={i % 2 === 0 ? "bg-white" : "bg-surface/50"}>
                {columns.map((col) => (
                  <td
                    key={col.id}
                    className={`px-3 py-1.5 border-b border-chart-border/50 whitespace-nowrap ${
                      col.inferred_type === "numeric" || col.inferred_type === "integer" || col.inferred_type === "float"
                        ? "font-mono text-right"
                        : ""
                    }`}
                  >
                    {row[col.name] ?? ""}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {truncated && (
        <div className="px-4 py-2 border-t border-chart-border bg-surface">
          <p className="text-[11px] text-brand-muted">
            Showing preview — full dataset has {dataset.row_count?.toLocaleString()} rows
          </p>
        </div>
      )}
    </div>
  );
}
