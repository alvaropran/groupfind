"use client";

import type { Job, JobStatus } from "@/shared/types/jobs";
import {
  JOB_STATUS_LABELS,
  JOB_STATUS_ORDER,
} from "@/shared/constants/jobStatuses";

interface StatusTrackerProps {
  readonly job: Job;
}

function getStepState(
  stepStatus: JobStatus,
  currentStatus: JobStatus,
): "done" | "active" | "pending" {
  const currentIdx = JOB_STATUS_ORDER.indexOf(currentStatus);
  const stepIdx = JOB_STATUS_ORDER.indexOf(stepStatus);

  if (stepIdx < currentIdx) return "done";
  if (stepIdx === currentIdx) return "active";
  return "pending";
}

export function StatusTracker({ job }: StatusTrackerProps) {
  const steps = JOB_STATUS_ORDER.filter((s) => s !== "complete");

  return (
    <div className="w-full max-w-lg mx-auto p-6">
      <div className="space-y-4">
        {steps.map((step) => {
          const state = job.status === "failed" ? "pending" : getStepState(step, job.status);
          return (
            <div key={step} className="flex items-center gap-3">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                  state === "done"
                    ? "bg-green-100 text-green-600"
                    : state === "active"
                      ? "bg-blue-100 text-blue-600"
                      : "bg-gray-100 text-gray-400"
                }`}
              >
                {state === "done" && <span className="text-sm">&#10003;</span>}
                {state === "active" && (
                  <div className="w-3 h-3 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                )}
                {state === "pending" && (
                  <div className="w-2 h-2 bg-gray-300 rounded-full" />
                )}
              </div>
              <span
                className={`text-sm ${
                  state === "active"
                    ? "text-gray-900 font-medium"
                    : state === "done"
                      ? "text-gray-500"
                      : "text-gray-400"
                }`}
              >
                {JOB_STATUS_LABELS[step]}
              </span>
            </div>
          );
        })}
      </div>

      {job.progress_message && (
        <p className="mt-4 text-sm text-gray-500 text-center">
          {job.progress_message}
        </p>
      )}

      {job.status === "complete" && (
        <div className="mt-6 text-center">
          <div className="inline-flex items-center gap-2 text-green-600 font-medium">
            <span>&#10003;</span> Processing complete!
          </div>
        </div>
      )}

      {job.status === "failed" && (
        <div className="mt-6 p-4 bg-red-50 rounded-lg">
          <p className="text-sm text-red-700">
            {job.error_message ?? "An unexpected error occurred"}
          </p>
        </div>
      )}

      {job.progress_percent > 0 && job.status !== "complete" && (
        <div className="mt-4">
          <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 rounded-full transition-all duration-500"
              style={{ width: `${job.progress_percent}%` }}
            />
          </div>
          <p className="text-xs text-gray-400 mt-1 text-right">
            {job.progress_percent}%
          </p>
        </div>
      )}
    </div>
  );
}
