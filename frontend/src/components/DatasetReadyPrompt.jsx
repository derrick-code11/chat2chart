const STARTER_PROMPTS = [
  "Give me an overview of this data",
  "Show the distribution across categories",
  "What are the top values?",
];

export default function DatasetReadyPrompt({ datasetName, onPromptClick }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6">
      <div className="inline-flex items-center gap-1.5 text-xs font-mono text-brand-accent bg-brand-accent/[0.07] border border-brand-accent/18 rounded-[3px] px-2.5 py-[3px] mb-4">
        <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true">
          <rect x="1" y="1" width="8" height="8" rx="1" stroke="currentColor" strokeWidth="1.2" />
          <path d="M1 4h8" stroke="currentColor" strokeWidth="1.2" />
        </svg>
        {datasetName}
      </div>
      <p className="text-[15px] font-medium text-brand-dark mb-1.5 tracking-[-0.01em]">
        Dataset ready — ask your first question
      </p>
      <p className="text-[13px] text-muted-light mb-5.5 leading-[1.6]">
        Describe what you want to see in plain English.
      </p>
      <div className="flex flex-col gap-1.5 w-full max-w-[300px]">
        {STARTER_PROMPTS.map((p) => (
          <button
            type="button"
            key={p}
            onClick={() => onPromptClick(p)}
            className="text-[13px] text-brand-dark bg-surface border border-brand-border rounded px-3.5 py-2 text-left transition-[border-color] duration-120 hover:border-muted-light"
          >
            {p}
          </button>
        ))}
      </div>
    </div>
  );
}
