import { useCallback, useRef, useState } from "react";
import { api } from "../lib/api";
import Spinner from "./Spinner";

const EXAMPLE_PROMPTS = [
  "Give me an overview of this data",
  "Show the distribution across categories",
  "What are the top values?",
];

export default function EmptyState({ onConversationCreated }) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadStep, setUploadStep] = useState(null);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  const handleFile = useCallback(
    async (file) => {
      if (!file || uploading) return;
      setError(null);
      setUploading(true);
      try {
        setUploadStep("Uploading file…");
        const dataset = await api.datasets.upload(file);
        if (!dataset) return;
        if (dataset.status === "failed") {
          throw new Error(dataset.parse_error || "File could not be parsed. Try a different file.");
        }

        setUploadStep("Creating workspace…");
        const title = file.name.replace(/\.[^.]+$/, "");
        const conv = await api.conversations.create({
          title,
          dataset_ids: [dataset.id],
        });
        if (conv) onConversationCreated(conv, dataset);
      } catch (e) {
        setError(e.message);
      } finally {
        setUploading(false);
        setUploadStep(null);
      }
    },
    [uploading, onConversationCreated]
  );

  const onDrop = useCallback(
    (e) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  return (
    <div className="flex flex-col items-center justify-center h-full px-6 py-8">
      <svg
        width="44"
        height="44"
        viewBox="0 0 44 44"
        fill="none"
        className="mb-4.5 opacity-35"
        aria-hidden="true"
      >
        <rect x="4" y="26" width="8" height="14" rx="1.5" fill="#107A4D" />
        <rect x="18" y="16" width="8" height="24" rx="1.5" fill="#107A4D" />
        <rect x="32" y="6" width="8" height="34" rx="1.5" fill="#107A4D" />
        <path d="M4 6h36" stroke="#C4D8CB" strokeWidth="1.5" strokeLinecap="square" />
        <path d="M4 6v34" stroke="#C4D8CB" strokeWidth="1.5" strokeLinecap="square" />
      </svg>

      <h2 className="text-[21px] font-semibold text-brand-dark tracking-[-0.02em] mb-2 text-center">
        Create your first chart
      </h2>
      <p className="text-sm text-brand-muted mb-7 text-center max-w-[320px] leading-[1.6]">
        Upload a CSV or Excel file and ask a question in plain English.
      </p>

      <div
        onClick={() => !uploading && fileInputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`w-full max-w-[400px] border-2 border-dashed rounded-[6px] px-6 py-8 flex flex-col items-center gap-2 transition-colors duration-150 ${
          uploading ? "cursor-default" : "cursor-pointer"
        } ${
          dragging
            ? "border-brand-accent bg-brand-primary/10"
            : "border-brand-primary"
        }`}
      >
        {uploading ? (
          <>
            <Spinner />
            <p className="text-[13px] text-brand-muted">{uploadStep}</p>
          </>
        ) : (
          <>
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true">
              <path d="M11 3v12" stroke="#107A4D" strokeWidth="1.5" strokeLinecap="square" />
              <path d="M7 7l4-4 4 4" stroke="#107A4D" strokeWidth="1.5" strokeLinecap="square" strokeLinejoin="miter" />
              <path d="M3 15v2a2 2 0 002 2h12a2 2 0 002-2v-2" stroke="#C4D8CB" strokeWidth="1.5" strokeLinecap="square" />
            </svg>
            <p className="text-sm text-brand-dark font-medium">
              Drop a file here, or{" "}
              <span className="text-brand-accent">browse</span>
            </p>
            <p className="text-xs text-muted-light">CSV, XLSX, or XLS · up to 10 MB</p>
          </>
        )}
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept=".csv,.xlsx,.xls"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) handleFile(f);
          e.target.value = "";
        }}
      />

      {error && (
        <p className="mt-3.5 text-[13px] text-brand-error text-center max-w-[380px] leading-normal">
          {error}
        </p>
      )}

      {!uploading && (
        <div className="mt-8 text-center">
          <p className="text-[11px] text-muted-light font-mono uppercase tracking-widest mb-2.5">
            Example questions
          </p>
          <div className="flex flex-col gap-1.5">
            {EXAMPLE_PROMPTS.map((p) => (
              <span
                key={p}
                className="text-xs text-brand-muted bg-black/4 rounded px-3 py-[5px] inline-block"
              >
                &ldquo;{p}&rdquo;
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
