/**
 * Copyright (c) 2026 Dennis Guse. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in project root.
 */

import { clearSession, hasSessionHint } from "@/lib/session";

const API_URL = "/api";

// The session lives in an httpOnly cookie that the browser attaches to same-origin
// requests by itself and the Next.js proxy turns into the Authorization header for
// the backend - scripts never see or send the token, so there is nothing to add here.
export const getAuthHeaders = () => ({
  "Content-Type": "application/json",
});

function handleUnauthorizedResponse(res: Response) {
  if (res.status === 401 && typeof window !== "undefined") {
    const hadSession = hasSessionHint();
    clearSession();
    const currentPath = window.location.pathname;
    if (!["/login", "/register", "/forgot-password", "/reset-password", "/session-expired"].includes(currentPath)) {
      window.location.href = hadSession ? "/session-expired" : "/login";
    }
  }
}

async function parseError(res: Response): Promise<string> {
  handleUnauthorizedResponse(res);
  let msg = `API Fehler (${res.status})`;
  try {
    const text = await res.text();
    try {
      const err = JSON.parse(text);
      if (err.detail) {
        msg = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail);
      }
    } catch (_) {
      if (text) msg = text.substring(0, 100);
    }
  } catch (_) {}
  return msg;
}

export const api = {
  get: async (endpoint: string) => {
    const res = await fetch(`${API_URL}${endpoint}`, { headers: getAuthHeaders() });
    if (!res.ok) throw new Error(await parseError(res));
    return res.json();
  },
  post: async (endpoint: string, data: any) => {
    const res = await fetch(`${API_URL}${endpoint}`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error(await parseError(res));
    return res.json();
  },
  put: async (endpoint: string, data: any) => {
    const res = await fetch(`${API_URL}${endpoint}`, {
      method: "PUT",
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error(await parseError(res));
    return res.json();
  },
  postForm: async (endpoint: string, formData: FormData) => {
    const res = await fetch(`${API_URL}${endpoint}`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error(await parseError(res));
    return res.json();
  },
  delete: async (endpoint: string) => {
    const res = await fetch(`${API_URL}${endpoint}`, {
      method: "DELETE",
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error(await parseError(res));
    return res.json();
  }
};
