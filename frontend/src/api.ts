import type {
  Check,
  Dashboard,
  Incident,
  Page,
  PublicConfig,
  Service,
} from "./types";

const base = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    message: string,
    public status = 0,
  ) {
    super(message);
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  try {
    const signal = options.signal
      ? AbortSignal.any([options.signal, AbortSignal.timeout(8000)])
      : AbortSignal.timeout(8000);
    const response = await fetch(`${base}${path}`, {
      ...options,
      signal,
      headers: {
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...options.headers,
      },
    });
    if (!response.ok) {
      const body: { detail?: unknown } = await response
        .json()
        .catch(() => ({}));
      throw new ApiError(
        typeof body.detail === "string"
          ? body.detail
          : `API returned HTTP ${response.status}`,
        response.status,
      );
    }
    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  } catch (error) {
    if (options.signal?.aborted || error instanceof ApiError) throw error;
    throw new ApiError(
      "Cannot reach the PulseBoard API. Your services may still be running.",
    );
  }
}

const pageQuery = (before?: number, limit = 50) =>
  `?limit=${limit}${before ? `&before=${before}` : ""}`;
export const api = {
  config: (signal?: AbortSignal) =>
    request<PublicConfig>("/config", { signal }),
  dashboard: (signal?: AbortSignal) =>
    request<Dashboard>("/dashboard", { signal }),
  services: (signal?: AbortSignal) =>
    request<Service[]>("/services", { signal }),
  service: (id: number, signal?: AbortSignal) =>
    request<Service>(`/services/${id}`, { signal }),
  create: (name: string, url: string, signal?: AbortSignal) =>
    request<Service>("/services", {
      method: "POST",
      body: JSON.stringify({ name, url }),
      signal,
    }),
  remove: (id: number, signal?: AbortSignal) =>
    request<void>(`/services/${id}`, { method: "DELETE", signal }),
  checks: (id: number, signal?: AbortSignal, before?: number, limit = 50) =>
    request<Page<Check>>(`/services/${id}/checks${pageQuery(before, limit)}`, {
      signal,
    }),
  check: (id: number, signal?: AbortSignal) =>
    request<Check>(`/checks/${id}`, { signal }),
  incidents: (signal?: AbortSignal, before?: number) =>
    request<Page<Incident>>(`/incidents${pageQuery(before)}`, { signal }),
  serviceIncidents: (id: number, signal?: AbortSignal, before?: number) =>
    request<Page<Incident>>(`/services/${id}/incidents${pageQuery(before)}`, {
      signal,
    }),
};
