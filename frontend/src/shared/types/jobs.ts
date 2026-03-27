export const JOB_STATUSES = [
  "pending",
  "parsing",
  "extracting",
  "verifying",
  "complete",
  "failed",
] as const;

export type JobStatus = (typeof JOB_STATUSES)[number];

export interface Job {
  readonly job_id: string;
  readonly status: JobStatus;
  readonly progress_message: string | null;
  readonly progress_percent: number;
  readonly error_message: string | null;
  readonly created_at: string;
  readonly completed_at: string | null;
}

export interface CreateJobResponse {
  readonly job_id: string;
  readonly session_id: string;
}

export interface TripDetails {
  readonly destination: string;
  readonly start_date: string;
  readonly num_days: number;
  readonly num_travelers: number;
  readonly vibes: readonly string[];
}
