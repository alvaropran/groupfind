"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useJobPolling } from "@/features/processing/hooks/useJobPolling";
import { StatusTracker } from "@/features/processing/components/StatusTracker";

export default function ProcessingPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = typeof params.jobId === "string" ? params.jobId : null;
  const { job, error } = useJobPolling(jobId);

  useEffect(() => {
    if (job?.status === "complete") {
      const timer = setTimeout(() => {
        router.push(`/results/${jobId}`);
      }, 1500);
      return () => clearTimeout(timer);
    }
  }, [job?.status, jobId, router]);

  if (!jobId) {
    return (
      <main className="flex-1 flex items-center justify-center">
        <p className="text-gray-500">Invalid job ID</p>
      </main>
    );
  }

  return (
    <main className="flex-1 flex flex-col items-center justify-center px-4 py-16">
      <h1 className="text-2xl font-bold text-gray-900 mb-8">
        Processing your group chat...
      </h1>

      {error && !job && (
        <div className="p-4 bg-red-50 rounded-lg max-w-md">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {job && <StatusTracker job={job} />}

      {!job && !error && (
        <div className="flex items-center gap-3">
          <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-gray-500">Connecting...</span>
        </div>
      )}
    </main>
  );
}
