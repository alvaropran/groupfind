"use client";

import { useCallback, useState } from "react";

interface FocusInputProps {
  readonly chatTitle: string;
  readonly onSubmit: (focus: string | null) => void;
  readonly loading?: boolean;
}

export function FocusInput({ chatTitle, onSubmit, loading = false }: FocusInputProps) {
  const [focus, setFocus] = useState("");

  const handleSubmit = useCallback(() => {
    onSubmit(focus.trim() || null);
  }, [focus, onSubmit]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter") {
        handleSubmit();
      }
    },
    [handleSubmit],
  );

  return (
    <div className="w-full max-w-2xl mx-auto">
      <h2 className="text-xl font-semibold text-slate-900 mb-2">
        What are you planning?
      </h2>
      <p className="text-sm text-slate-500 mb-6">
        Tell us what to focus on and we&apos;ll prioritize those results from
        <strong className="text-slate-700"> {chatTitle}</strong>.
        Or skip to see everything.
      </p>

      <div className="space-y-4">
        <input
          type="text"
          value={focus}
          onChange={(e) => setFocus(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="e.g. Indonesia trip, NYC restaurants, Thailand nightlife..."
          disabled={loading}
          className="w-full px-4 py-3 bg-white border border-slate-300 rounded-xl text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-violet-400 focus:border-transparent transition-all"
        />

        <div className="flex gap-3">
          <button
            onClick={handleSubmit}
            disabled={loading}
            className={`
              flex-1 px-4 py-3 rounded-xl font-medium text-white transition-all
              ${loading
                ? "bg-slate-300 cursor-not-allowed"
                : "bg-slate-900 hover:bg-slate-800 active:bg-slate-700"
              }
            `}
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Starting...
              </span>
            ) : focus.trim() ? (
              `Find ${focus.trim()} spots`
            ) : (
              "Find all spots"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
