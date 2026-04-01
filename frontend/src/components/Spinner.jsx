export default function Spinner({ size = 20 }) {
  const r = Math.round(size * 0.35);
  const dash = Math.round(2 * Math.PI * r);
  return (
    <svg
      className="spin"
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      fill="none"
      aria-hidden="true"
    >
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        stroke="var(--color-brand-primary)"
        strokeWidth={size >= 24 ? 2.5 : 2}
        strokeDasharray={dash}
        strokeDashoffset={Math.round(dash / 3)}
      />
    </svg>
  );
}
