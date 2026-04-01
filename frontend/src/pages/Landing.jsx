import { useState } from "react";
import { GoogleLogin } from "@react-oauth/google";
import { setToken } from "../lib/auth";

const API_BASE = import.meta.env.VITE_API_BASE_URL;

const FEATURES = [
  {
    label: "Upload any dataset",
    desc: "CSV, JSON, or paste raw data — we parse it instantly.",
  },
  {
    label: "Ask in plain English",
    desc: '"Show me monthly revenue by region" — done.',
  },
  {
    label: "Export anywhere",
    desc: "PNG, SVG, or embed-ready iframe with one click.",
  },
];

export default function Landing() {
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleGoogleSuccess(credentialResponse) {
    setError(null);
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/google`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ credential: credentialResponse.credential }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data?.message ?? "Sign in failed. Please try again.");
        return;
      }
      setToken(data.data.access_token);
      window.location.href = "/app";
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  function handleGoogleError() {
    setError("Google sign-in was cancelled or failed.");
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-brand-bg">
      <div
        className="hidden md:flex flex-col justify-between w-[58%] p-14 relative overflow-hidden bg-brand-dark"
        style={{
          backgroundImage:
            "repeating-linear-gradient(0deg,rgba(255,255,255,0.04) 0px,rgba(255,255,255,0.04) 1px,transparent 1px,transparent 48px)," +
            "repeating-linear-gradient(90deg,rgba(255,255,255,0.04) 0px,rgba(255,255,255,0.04) 1px,transparent 1px,transparent 48px)",
        }}
      >
        <div className="relative z-10">
          <span className="text-sm font-mono tracking-[0.18em] uppercase text-brand-primary">
            chat2chart
          </span>
        </div>

        <div className="relative z-10 max-w-lg">
          <p className="text-xs font-mono uppercase tracking-widest mb-6 text-brand-accent">
            Data → Charts
          </p>
          <h1 className="text-5xl font-semibold leading-[1.1] mb-8 text-brand-bg tracking-[-0.02em]">
            Your data, <span className="text-brand-primary">visualized</span> in seconds.
          </h1>
          <p className="text-base leading-relaxed text-muted-light">
            Upload a dataset, ask a question in plain English, and get a
            publication-ready chart — no SQL, no code, no fuss.
          </p>

          <ul className="mt-10 space-y-5">
            {FEATURES.map((f) => (
              <li key={f.label} className="flex gap-4 items-start">
                <span className="mt-0.5 shrink-0 w-4 h-4 flex items-center justify-center text-brand-accent">
                  <svg viewBox="0 0 16 16" fill="none" width="16" height="16">
                    <path d="M3 8.5L6.5 12 13 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="square" />
                  </svg>
                </span>
                <span>
                  <span className="text-sm font-medium text-sidebar-text-active">{f.label}</span>
                  <span className="text-sm text-sidebar-text"> — {f.desc}</span>
                </span>
              </li>
            ))}
          </ul>
        </div>

        <div className="relative z-10">
          <p className="text-xs font-mono text-sidebar-text-dim">
            Free to start. No credit card required.
          </p>
        </div>
      </div>

      <div className="flex flex-col items-center justify-center flex-1 px-8 bg-brand-bg">
        <div className="w-full max-w-[340px]">
          <p className="md:hidden text-xs font-mono uppercase tracking-[0.18em] mb-10 text-center text-brand-accent">
            chat2chart
          </p>

          <h2 className="text-2xl font-semibold mb-2 text-brand-dark tracking-[-0.02em]">
            Get started
          </h2>
          <p className="text-sm mb-8 text-brand-muted">
            Sign in to create your first chart.
          </p>

          <div className="w-full h-px mb-8 bg-brand-border" />

          <div className="flex flex-col items-stretch gap-3">
            {loading ? (
              <div className="flex items-center justify-center gap-2 py-3 text-sm text-brand-muted">
                <svg className="animate-spin" width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <circle cx="8" cy="8" r="6" stroke="#C4D8CB" strokeWidth="2" strokeDasharray="28" strokeDashoffset="10" />
                </svg>
                Signing in…
              </div>
            ) : (
              <GoogleLogin
                onSuccess={handleGoogleSuccess}
                onError={handleGoogleError}
                useOneTap={false}
                theme="outline"
                size="large"
                width="340"
                text="continue_with"
                shape="square"
              />
            )}
          </div>

          {error && (
            <p className="mt-4 text-xs text-center leading-snug text-brand-error">
              {error}
            </p>
          )}

          <div className="w-full h-px mt-8 mb-6 bg-brand-border" />

          <p className="text-xs text-center leading-relaxed text-muted-light">
            By continuing, you agree to our{" "}
            <a href="/terms" className="text-brand-accent hover:underline">Terms</a>{" "}
            and{" "}
            <a href="/privacy" className="text-brand-accent hover:underline">Privacy Policy</a>.
          </p>
        </div>
      </div>
    </div>
  );
}
