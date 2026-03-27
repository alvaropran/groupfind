"use client";

import { useCallback, useState } from "react";
import { apiClient } from "@/lib/apiClient";
import type { CreateJobResponse } from "@/shared/types/jobs";
import { validateZipFile } from "../validators/zipValidator";

interface UploadState {
  readonly status: "idle" | "validating" | "uploading" | "creating_job" | "done" | "error";
  readonly error: string | null;
  readonly file: File | null;
  readonly jobId: string | null;
  readonly sessionId: string | null;
}

const INITIAL_STATE: UploadState = {
  status: "idle",
  error: null,
  file: null,
  jobId: null,
  sessionId: null,
};

export function useFileUpload() {
  const [state, setState] = useState<UploadState>(INITIAL_STATE);

  const reset = useCallback(() => {
    setState(INITIAL_STATE);
  }, []);

  const upload = useCallback(async (file: File) => {
    setState({ ...INITIAL_STATE, status: "validating", file });

    const validation = validateZipFile(file);
    if (!validation.valid) {
      setState((prev) => ({
        ...prev,
        status: "error",
        error: validation.error,
      }));
      return;
    }

    try {
      setState((prev) => ({ ...prev, status: "uploading" }));

      // For MVP: upload file directly to backend as form data
      // TODO: Switch to Supabase Storage presigned URL for production
      const formData = new FormData();
      formData.append("file", file);

      const uploadResponse = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/upload`,
        { method: "POST", body: formData },
      );

      if (!uploadResponse.ok) {
        throw new Error("Failed to upload file");
      }

      const { file_url } = (await uploadResponse.json()) as { file_url: string };

      setState((prev) => ({ ...prev, status: "creating_job" }));

      const job = await apiClient.post<CreateJobResponse>("/jobs", {
        file_url,
      });

      setState((prev) => ({
        ...prev,
        status: "done",
        jobId: job.job_id,
        sessionId: job.session_id,
      }));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Upload failed";
      setState((prev) => ({ ...prev, status: "error", error: message }));
    }
  }, []);

  return { ...state, upload, reset } as const;
}
