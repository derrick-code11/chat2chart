export default function DatasetPeekToolbar({
  filename,
  showViewer,
  onToggle,
  className = "",
}) {
  return (
    <div
      className={`flex items-center gap-2 -ml-3 w-max max-w-full sm:-ml-5 ${className}`}
    >
      <button
        type="button"
        onClick={onToggle}
        className="flex items-center -ml-38 gap-1.5 text-[12px] text-brand-muted hover:text-brand-dark transition-colors border border-chart-border rounded-md px-2.5 py-1.5"
        title="View dataset"
      >
        <svg
          width="14"
          height="14"
          viewBox="0 0 16 16"
          fill="none"
          aria-hidden="true"
        >
          <rect
            x="2"
            y="2"
            width="12"
            height="12"
            rx="1.5"
            stroke="currentColor"
            strokeWidth="1.3"
          />
          <line
            x1="2"
            y1="6"
            x2="14"
            y2="6"
            stroke="currentColor"
            strokeWidth="1.3"
          />
          <line
            x1="2"
            y1="10"
            x2="14"
            y2="10"
            stroke="currentColor"
            strokeWidth="1.3"
          />
          <line
            x1="6"
            y1="2"
            x2="6"
            y2="14"
            stroke="currentColor"
            strokeWidth="1.3"
          />
        </svg>
        {showViewer ? "Hide data" : "View data"}
      </button>
      <span className="text-[11px] text-brand-muted">{filename}</span>
    </div>
  );
}
