import { useCallback, useRef, useState } from "react";
import { api } from "../lib/api";

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
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        height: "100%",
        padding: "32px 24px",
      }}
    >
      {/* Icon */}
      <svg
        width="44"
        height="44"
        viewBox="0 0 44 44"
        fill="none"
        style={{ marginBottom: 18, opacity: 0.35 }}
        aria-hidden="true"
      >
        <rect x="4" y="26" width="8" height="14" rx="1.5" fill="#107A4D" />
        <rect x="18" y="16" width="8" height="24" rx="1.5" fill="#107A4D" />
        <rect x="32" y="6" width="8" height="34" rx="1.5" fill="#107A4D" />
        <path d="M4 6h36" stroke="#C4D8CB" strokeWidth="1.5" strokeLinecap="square" />
        <path d="M4 6v34" stroke="#C4D8CB" strokeWidth="1.5" strokeLinecap="square" />
      </svg>

      <h2
        style={{
          fontSize: 21,
          fontWeight: 600,
          color: "#2A2A2A",
          letterSpacing: "-0.02em",
          marginBottom: 8,
          textAlign: "center",
        }}
      >
        Create your first chart
      </h2>
      <p
        style={{
          fontSize: 14,
          color: "#6B6B6B",
          marginBottom: 28,
          textAlign: "center",
          maxWidth: 320,
          lineHeight: 1.6,
        }}
      >
        Upload a CSV or Excel file and ask a question in plain English.
      </p>

      {/* Drop zone */}
      <div
        onClick={() => !uploading && fileInputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        style={{
          width: "100%",
          maxWidth: 400,
          border: `2px dashed ${dragging ? "#107A4D" : "#C4D8CB"}`,
          borderRadius: 6,
          padding: "32px 24px",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 8,
          cursor: uploading ? "default" : "pointer",
          backgroundColor: dragging ? "rgba(196, 216, 203, 0.1)" : "transparent",
          transition: "border-color 0.15s, background-color 0.15s",
        }}
      >
        {uploading ? (
          <>
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
            <p style={{ fontSize: 13, color: "#6B6B6B", fontFamily: "Inter, sans-serif" }}>
              {uploadStep}
            </p>
          </>
        ) : (
          <>
            <svg
              width="22"
              height="22"
              viewBox="0 0 22 22"
              fill="none"
              aria-hidden="true"
            >
              <path
                d="M11 3v12"
                stroke="#107A4D"
                strokeWidth="1.5"
                strokeLinecap="square"
              />
              <path
                d="M7 7l4-4 4 4"
                stroke="#107A4D"
                strokeWidth="1.5"
                strokeLinecap="square"
                strokeLinejoin="miter"
              />
              <path
                d="M3 15v2a2 2 0 002 2h12a2 2 0 002-2v-2"
                stroke="#C4D8CB"
                strokeWidth="1.5"
                strokeLinecap="square"
              />
            </svg>
            <p
              style={{
                fontSize: 14,
                color: "#2A2A2A",
                fontWeight: 500,
                fontFamily: "Inter, sans-serif",
              }}
            >
              Drop a file here, or{" "}
              <span style={{ color: "#107A4D" }}>browse</span>
            </p>
            <p
              style={{
                fontSize: 12,
                color: "#9A9A8A",
                fontFamily: "Inter, sans-serif",
              }}
            >
              CSV, XLSX, or XLS · up to 10 MB
            </p>
          </>
        )}
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept=".csv,.xlsx,.xls"
        style={{ display: "none" }}
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) handleFile(f);
          e.target.value = "";
        }}
      />

      {error && (
        <p
          style={{
            marginTop: 14,
            fontSize: 13,
            color: "#C0392B",
            textAlign: "center",
            maxWidth: 380,
            lineHeight: 1.5,
            fontFamily: "Inter, sans-serif",
          }}
        >
          {error}
        </p>
      )}

      {/* Example prompts hint */}
      {!uploading && (
        <div style={{ marginTop: 32, textAlign: "center" }}>
          <p
            style={{
              fontSize: 11,
              color: "#9A9A8A",
              fontFamily: '"Geist Mono", monospace',
              textTransform: "uppercase",
              letterSpacing: "0.1em",
              marginBottom: 10,
            }}
          >
            Example questions
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {EXAMPLE_PROMPTS.map((p) => (
              <span
                key={p}
                style={{
                  fontSize: 12,
                  color: "#6B6B6B",
                  fontFamily: "Inter, sans-serif",
                  backgroundColor: "rgba(0,0,0,0.04)",
                  borderRadius: 4,
                  padding: "5px 12px",
                  display: "inline-block",
                }}
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
