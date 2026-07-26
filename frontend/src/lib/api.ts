const API_URL = "/api";

export const getAuthHeaders = () => {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
};

function handleUnauthorizedResponse(res: Response) {
  if (res.status === 401 && typeof window !== "undefined") {
    localStorage.removeItem("token");
    const currentPath = window.location.pathname;
    if (!["/login", "/register", "/forgot-password", "/reset-password", "/session-expired"].includes(currentPath)) {
      window.location.href = "/session-expired";
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
    const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
    const res = await fetch(`${API_URL}${endpoint}`, {
      method: "POST",
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
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
