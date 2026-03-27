import type { JobStatus } from "@/shared/types/jobs";

export const JOB_STATUS_LABELS: Record<JobStatus, string> = {
  pending: "Waiting to start...",
  parsing: "Parsing Instagram export...",
  extracting: "Finding activities from your chat...",
  verifying: "Checking reviews & finding booking links...",
  complete: "Done!",
  failed: "Something went wrong",
};

export const JOB_STATUS_ORDER: readonly JobStatus[] = [
  "pending",
  "parsing",
  "extracting",
  "verifying",
  "complete",
];
