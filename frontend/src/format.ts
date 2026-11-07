import type { Check } from "./types";

export function dateTime(value: string): string {
  return (
    new Intl.DateTimeFormat("en-GB", {
      dateStyle: "medium",
      timeStyle: "medium",
      timeZone: "UTC",
    }).format(new Date(value)) + " UTC"
  );
}
export function clock(value: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    timeZone: "UTC",
  }).format(new Date(value));
}
export function latency(value: number | null | undefined): string {
  return value == null
    ? "—"
    : `${value < 10 ? value.toFixed(1) : Math.round(value)} ms`;
}
export function percent(value: number | null | undefined): string {
  return value == null ? "—" : `${value.toFixed(2)}%`;
}
export function duration(value: number): string {
  const seconds = Math.max(0, Math.floor(value));
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
}
export function checkDescription(check: Check): string {
  return `Check #${check.id} · ${dateTime(check.checked_at)} · ${check.status} · HTTP ${check.http_status ?? "no response"} · ${latency(check.response_time_ms)}${check.error_type ? ` · ${check.error_type}: ${check.error_message}` : ""}`;
}
