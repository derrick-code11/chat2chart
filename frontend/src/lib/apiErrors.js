function looksTechnical(msg) {
  if (!msg || typeof msg !== "string") return true;
  if (msg.length > 220) return true;
  if (/Chart model request failed|Provider returned error|openrouter\.ai/i.test(msg)) {
    return true;
  }
  if (/user_id|'error':|"code":\s*429|minimax\/|OpenInference/i.test(msg)) {
    return true;
  }
  if (msg.includes("{") && (msg.includes("'error'") || msg.includes('"error"'))) {
    return true;
  }
  return false;
}

/**
 * @param {string | undefined} raw - message from API envelope
 * @param {{ code?: string, status?: number }} meta
 * @returns {string}
 */
export function humanizeErrorMessage(raw, meta = {}) {
  const { code, status } = meta;

  if (status === 429) {
    return "The service is busy. Please wait a moment and try again.";
  }
  if (status === 502 || status === 503) {
    return "The service is temporarily unavailable. Please try again shortly.";
  }

  if (code === "LLM_UPSTREAM") {
    if (raw && !looksTechnical(raw)) return raw;
    return "We couldn’t generate the chart right now. Please try again in a moment.";
  }

  if (code === "CHART_GENERATION_FAILED" && raw && !looksTechnical(raw)) {
    return raw;
  }

  if (looksTechnical(raw)) {
    if (status >= 500) {
      return "Something went wrong on our side. Please try again in a moment.";
    }
    return "Something went wrong. Please try again.";
  }

  if (!raw || !String(raw).trim()) {
    return "Something went wrong. Please try again.";
  }

  const s = String(raw).trim();
  if (
    s === "Failed to fetch" ||
    /networkerror|load failed|network request failed/i.test(s)
  ) {
    return "Network error. Check your connection and try again.";
  }

  return s;
}
