/**
 * lib/api.ts — Typed fetch wrapper for the FastAPI backend.
 * All API calls in this app must go through these helpers.
 * Never call fetch() directly in components or pages.
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

interface RequestOptions<TBody = unknown> {
  method?: HttpMethod;
  body?: TBody;
  headers?: Record<string, string>;
}

/**
 * Core fetch wrapper. Sends credentials (cookies) on every request.
 * Throws on non-2xx responses with the parsed error detail.
 */
async function request<TResponse>(
  path: string,
  options: RequestOptions = {}
): Promise<TResponse> {
  const { method = "GET", body, headers = {} } = options;

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    credentials: "include", // send the HttpOnly session cookie
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail ?? "Request failed");
  }

  // 204 No Content — return empty
  if (res.status === 204) return undefined as TResponse;

  return res.json() as Promise<TResponse>;
}

// ---------------------------------------------------------------------------
// Convenience wrappers
// ---------------------------------------------------------------------------

export const api = {
  get: <T>(path: string, headers?: Record<string, string>) =>
    request<T>(path, { method: "GET", headers }),

  post: <T, B = unknown>(path: string, body?: B, headers?: Record<string, string>) =>
    request<T>(path, { method: "POST", body, headers }),

  put: <T, B = unknown>(path: string, body?: B) =>
    request<T>(path, { method: "PUT", body }),

  patch: <T, B = unknown>(path: string, body?: B) =>
    request<T>(path, { method: "PATCH", body }),

  delete: <T>(path: string) =>
    request<T>(path, { method: "DELETE" }),
};

// ---------------------------------------------------------------------------
// Typed API surface — add endpoint types here as the backend grows
// ---------------------------------------------------------------------------

export interface UserResponse {
  id: string;
  email: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface HealthResponse {
  status: string;
  timestamp: string;
}

export const authApi = {
  register: (email: string, password: string) =>
    api.post<UserResponse>("/api/v1/users/register", { email, password }),

  login: (email: string, password: string) =>
    api.post<UserResponse>("/api/v1/users/login", { email, password }),

  logout: () =>
    api.post<void>("/api/v1/users/logout"),

  me: () =>
    api.get<UserResponse>("/api/v1/users/me"),
};

export const healthApi = {
  check: () => api.get<HealthResponse>("/api/v1/health"),
};
