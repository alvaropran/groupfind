"use client";

interface UploadProgressProps {
  readonly status: string;
  readonly fileName: string | null;
  readonly error: string | null;
  readonly onRetry: () => void;
}

const STATUS_MESSAGES: Record<string, string> = {
  validating: "Validating file...",
  uploading: "Uploading...",
  creating_job: "Starting processing...",
  done: "Upload complete! Redirecting...",
  error: "Upload failed",
};

export function UploadProgress({
  status,
  fileName,
  error,
  onRetry,
}: UploadProgressProps) {
  const isError = status === "error";
  const isLoading = !isError && status !== "done";

  return (
    <div className="w-full max-w-md mx-auto p-6 bg-white rounded-2xl shadow-sm border">
      <div className="flex items-center gap-3 mb-4">
        {isLoading && (
          <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        )}
        {isError && (
          <div className="w-5 h-5 rounded-full bg-red-100 flex items-center justify-center">
            <span className="text-red-500 text-sm font-bold">!</span>
          </div>
        )}
        {status === "done" && (
          <div className="w-5 h-5 rounded-full bg-green-100 flex items-center justify-center">
            <span className="text-green-600 text-sm">&#10003;</span>
          </div>
        )}
        <span className="font-medium text-gray-800">
          {STATUS_MESSAGES[status] ?? "Processing..."}
        </span>
      </div>

      {fileName && (
        <p className="text-sm text-gray-500 truncate">{fileName}</p>
      )}

      {isError && error && (
        <div className="mt-3">
          <p className="text-sm text-red-600 mb-3">{error}</p>
          <button
            onClick={onRetry}
            className="text-sm text-blue-600 hover:text-blue-700 font-medium"
          >
            Try again
          </button>
        </div>
      )}
    </div>
  );
}
