export type Status = "UNKNOWN" | "UP" | "DOWN";

export interface Check {
  id: number;
  service_id: number;
  checked_at: string;
  status: Exclude<Status, "UNKNOWN">;
  http_status: number | null;
  response_time_ms: number | null;
  error_type: string | null;
  error_message: string | null;
  gap_before_seconds: number;
}

export interface Service {
  id: number;
  name: string;
  url: string;
  created_at: string;
  status: Status;
  latest_check: Check | null;
  recent_checks: Check[];
  check_count: number;
  success_count: number;
  availability_percent: number | null;
  stale: boolean;
}

export interface Incident {
  id: number;
  service_id: number;
  service_name: string;
  opened_at: string;
  closed_at: string | null;
  opening_check_id: number;
  closing_check_id: number | null;
  reason: string;
  last_observed_at: string;
  observation_gap_seconds: number;
  observed_duration_seconds: number;
  elapsed_seconds: number;
}

export interface Page<T> {
  items: T[];
  next_cursor: number | null;
}
export interface PublicConfig {
  read_only: boolean;
  interval_seconds: number;
  timeout_seconds: number;
  concurrency: number;
  gap_threshold_seconds: number;
  max_services: number;
}
export interface Dashboard {
  total_services: number;
  up_services: number;
  down_services: number;
  unknown_services: number;
  stale_services: number;
  open_incidents: number;
  check_count: number;
  availability_percent: number | null;
  generated_at: string;
}
