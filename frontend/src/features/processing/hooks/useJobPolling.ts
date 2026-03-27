"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiClient } from "@/lib/apiClient";
import type { Job } from "@/shared/types/jobs";

const POLL_INTERVAL_MS = 3000;

interface UseJobPollingResult {
  readonly job: Job | null;
  readonly error: string | null;
  readonly isPolling: boolean;
}

export function useJobPolling(jobId: string | null): UseJobPollingResult {
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setIsPolling(false);
  }, []);

  const fetchStatus = useCallback(async () => {
    if (!jobId) return;

    try {
      const data = await apiClient.get<Job>(`/jobs/${jobId}/status`);
      setJob(data);
      setError(null);

      if (data.status === "complete" || data.status === "failed") {
        stopPolling();
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to fetch status";
      setError(message);
    }
  }, [jobId, stopPolling]);

  useEffect(() => {
    if (!jobId) return;

    setIsPolling(true);
    fetchStatus();

    intervalRef.current = setInterval(fetchStatus, POLL_INTERVAL_MS);

    return () => {
      stopPolling();
    };
  }, [jobId, fetchStatus, stopPolling]);

  return { job, error, isPolling };
}
