// The only fetch wrapper for the API server; features call it through "@/shared/api".
//
// The web app and the API are deployed separately (docs/decisions.md D13):
// production calls VITE_API_URL cross-origin with the session cookie
// (credentials: "include"). In development VITE_API_URL is empty and Vite
// proxies the API paths, so requests stay same-origin.

export const API_URL: string = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

/** Absolute URL of an API path, e.g. apiUrl("/auth/google/start"). */
export function apiUrl(path: string): string {
  return API_URL + path;
}

export interface ErrorDetail {
  field: string;
  message: string;
}

/**
 * A failed API call. `code` is stable (D19): translate it with the i18n key
 * `error.<code>` and fall back to `message`, which is English and for logs.
 */
export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details: ErrorDetail[] = [],
  ) {
    super(message);
    this.name = "ApiError";
  }
}

interface ErrorBody {
  error?: { code?: string; message?: string; details?: ErrorDetail[] };
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(apiUrl(path), {
    credentials: "include",
    ...init,
    headers: { "content-type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const { error } = (await res.json().catch(() => ({}))) as ErrorBody;
    throw new ApiError(
      res.status,
      error?.code ?? `HTTP_${res.status}`,
      error?.message ?? res.statusText,
      error?.details ?? [],
    );
  }
  return (await res.json()) as T;
}
