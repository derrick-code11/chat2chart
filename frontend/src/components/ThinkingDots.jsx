import { useEffect, useState } from "react";
import Spinner from "./Spinner";

const STATUS_MESSAGES = [
  "Analyzing your dataset…",
  "Planning the best visualization…",
  "Crunching the numbers…",
  "Building your chart…",
  "Almost there…",
];

export default function ThinkingStatus() {
  const [idx, setIdx] = useState(0);
  const [fade, setFade] = useState(true);

  useEffect(() => {
    const id = setInterval(() => {
      setFade(false);
      setTimeout(() => {
        setIdx((prev) => (prev + 1) % STATUS_MESSAGES.length);
        setFade(true);
      }, 200);
    }, 2500);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="flex items-center gap-2 mb-5 h-6">
      <Spinner size={16} />
      <span
        className={`text-[13px] text-brand-muted transition-opacity duration-200 ${fade ? "opacity-100" : "opacity-0"}`}
      >
        {STATUS_MESSAGES[idx]}
      </span>
    </div>
  );
}
