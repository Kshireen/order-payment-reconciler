import { clearTokens, getAccessToken } from "./auth";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_ROOT ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, message: string, body: unknown) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  body?: unknown;
  isFormData?: boolean;
}

/**
 * Generic authenticated fetch wrapper. Attaches the JWT access token (if any)
 * as `Authorization: Bearer <token>`. Every dashboard/API call goes through
 * this so there's exactly one place that knows about the base URL and auth
 * header.
 */
export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const token = getAccessToken();
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let body: BodyInit | undefined;
  if (options.body !== undefined) {
    if (options.isFormData) {
      body = options.body as FormData;
      // do NOT set Content-Type for FormData - the browser sets the multipart boundary
    } else {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(options.body);
    }
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: options.method ?? "GET",
      headers,
      body,
    });
  } catch {
    throw new ApiError(0, "Couldn't reach the server. Is the backend running?", null);
  }

  let data: unknown = null;
  const text = await response.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!response.ok) {
    if (response.status === 401 && token) {
      clearTokens();
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
    }

    let message = `Request failed with status ${response.status}`;
    if (data && typeof data === "object" && "detail" in data) {
      message = String((data as { detail: unknown }).detail);
    }
    throw new ApiError(response.status, message, data);
  }

  return data as T;
}

export function uploadFile(path: string, file: File): Promise<{ created: number; skipped_rows: string[] }> {
  const formData = new FormData();
  formData.append("file", file);
  return apiFetch(path, { method: "POST", body: formData, isFormData: true });
}
