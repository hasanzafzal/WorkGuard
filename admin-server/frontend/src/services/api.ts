/**
 * WorkGuard Centralized API Service Layer
 * Connects directly to FastAPI backend.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || "";

export async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });

  if (!res.ok) {
    let errorDetail = res.statusText;
    try {
      const errJson = await res.json();
      if (errJson.detail) {
        errorDetail = typeof errJson.detail === "string" ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // Ignore JSON parsing errors for error response
    }
    throw new Error(`API Error [${res.status}]: ${errorDetail}`);
  }

  return await res.json();
}

export { API_BASE_URL };
