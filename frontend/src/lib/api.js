import { authHeaders, clearToken } from "./auth";
import { humanizeErrorMessage } from "./apiErrors";

const BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

function throwApiError(data, status) {
  const raw = data?.message ?? "Request failed";
  const code = data?.error?.code;
  const msg = humanizeErrorMessage(raw, { code, status });
  const err = new Error(msg);
  err.code = code;
  err.status = status;
  throw err;
}

async function request(path, opts = {}) {
  const { json: body, ...rest } = opts;
  const headers = {
    ...authHeaders(),
    ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
    ...(rest.headers ?? {}),
  };

  const res = await fetch(`${BASE}${path}`, {
    ...rest,
    headers,
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  });

  if (res.status === 401) {
    clearToken();
    window.location.href = "/";
    return null;
  }

  let data;
  try {
    data = await res.json();
  } catch {
    if (!res.ok) {
      throw new Error(
        humanizeErrorMessage(undefined, { status: res.status }),
      );
    }
    return null;
  }

  if (!res.ok) throwApiError(data, res.status);
  return data.data;
}

export const api = {
  me: () => request("/api/v1/me"),

  conversations: {
    list: () => request("/api/v1/conversations"),
    get: (id) => request(`/api/v1/conversations/${id}`),
    create: (body) => request("/api/v1/conversations", { method: "POST", json: body }),
    patch: (id, body) =>
      request(`/api/v1/conversations/${id}`, { method: "PATCH", json: body }),
    delete: (id) => request(`/api/v1/conversations/${id}`, { method: "DELETE" }),
    listDatasets: (id) => request(`/api/v1/conversations/${id}/datasets`),
    attachDataset: (id, datasetId) =>
      request(`/api/v1/conversations/${id}/datasets`, {
        method: "POST",
        json: { dataset_id: datasetId },
      }),
    listMessages: (id) => request(`/api/v1/conversations/${id}/messages`),
    createMessage: (id, body) =>
      request(`/api/v1/conversations/${id}/messages`, { method: "POST", json: body }),
  },

  datasets: {
    get: (id) => request(`/api/v1/datasets/${id}`),
    upload: async (file) => {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`${BASE}/api/v1/datasets`, {
        method: "POST",
        headers: authHeaders(),
        body: form,
      });
      if (res.status === 401) {
        clearToken();
        window.location.href = "/";
        return null;
      }
      let data;
      try {
        data = await res.json();
      } catch {
        if (!res.ok) {
          throw new Error(humanizeErrorMessage(undefined, { status: res.status }));
        }
        return null;
      }
      if (!res.ok) throwApiError(data, res.status);
      return data.data;
    },
  },

  messages: {
    exportPng: async (messageId) => {
      const res = await fetch(`${BASE}/api/v1/messages/${messageId}/export?format=png`, {
        headers: authHeaders(),
      });
      if (res.status === 401) {
        clearToken();
        window.location.href = "/";
        return null;
      }
      if (!res.ok) {
        let data = {};
        try {
          data = await res.json();
        } catch {
          /* ignore */
        }
        throwApiError(data, res.status);
      }
      return res.blob();
    },
  },
};
