"use client";

import { useCallback, useState } from "react";

const VIBE_OPTIONS = [
  { id: "adventure", label: "Adventure" },
  { id: "foodie", label: "Foodie" },
  { id: "beach", label: "Beach & Chill" },
  { id: "nightlife", label: "Nightlife" },
  { id: "culture", label: "Culture" },
  { id: "budget", label: "Budget" },
  { id: "luxury", label: "Luxury" },
  { id: "nature", label: "Nature" },
] as const;

interface TripFormData {
  readonly destination: string;
  readonly start_date: string;
  readonly num_days: number;
  readonly num_travelers: number;
  readonly vibes: readonly string[];
}

interface TripFormProps {
  readonly chatTitle: string;
  readonly onSubmit: (data: TripFormData) => void;
  readonly loading?: boolean;
}

export function TripForm({ chatTitle, onSubmit, loading = false }: TripFormProps) {
  const [destination, setDestination] = useState("");
  const [startDate, setStartDate] = useState("");
  const [numDays, setNumDays] = useState(7);
  const [numTravelers, setNumTravelers] = useState(2);
  const [vibes, setVibes] = useState<string[]>([]);

  const toggleVibe = useCallback((vibe: string) => {
    setVibes((prev) =>
      prev.includes(vibe) ? prev.filter((v) => v !== vibe) : [...prev, vibe],
    );
  }, []);

  const handleSubmit = useCallback(() => {
    if (!destination.trim()) return;
    onSubmit({
      destination: destination.trim(),
      start_date: startDate,
      num_days: numDays,
      num_travelers: numTravelers,
      vibes,
    });
  }, [destination, startDate, numDays, numTravelers, vibes, onSubmit]);

  const isValid = destination.trim().length > 0;

  return (
    <div className="w-full max-w-2xl mx-auto">
      <h2 className="text-xl font-semibold text-slate-900 mb-1">
        Plan your trip
      </h2>
      <p className="text-sm text-slate-500 mb-6">
        We&apos;ll read through <strong className="text-slate-700">{chatTitle}</strong> and
        build a day-by-day itinerary based on what your group has been sharing.
      </p>

      <div className="space-y-5">
        {/* Destination */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1.5">
            Where are you going?
          </label>
          <input
            type="text"
            value={destination}
            onChange={(e) => setDestination(e.target.value)}
            placeholder="e.g. Bali, Indonesia"
            disabled={loading}
            className="w-full px-4 py-3 bg-white border border-slate-300 rounded-xl text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-violet-400 focus:border-transparent"
          />
        </div>

        {/* Date + Duration row */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              Start date
            </label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              disabled={loading}
              className="w-full px-4 py-3 bg-white border border-slate-300 rounded-xl text-slate-800 focus:outline-none focus:ring-2 focus:ring-violet-400 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              Number of days
            </label>
            <input
              type="number"
              value={numDays}
              onChange={(e) => setNumDays(Math.max(1, parseInt(e.target.value) || 1))}
              min={1}
              max={30}
              disabled={loading}
              className="w-full px-4 py-3 bg-white border border-slate-300 rounded-xl text-slate-800 focus:outline-none focus:ring-2 focus:ring-violet-400 focus:border-transparent"
            />
          </div>
        </div>

        {/* Travelers */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1.5">
            How many travelers?
          </label>
          <input
            type="number"
            value={numTravelers}
            onChange={(e) => setNumTravelers(Math.max(1, parseInt(e.target.value) || 1))}
            min={1}
            max={20}
            disabled={loading}
            className="w-full px-4 py-3 bg-white border border-slate-300 rounded-xl text-slate-800 focus:outline-none focus:ring-2 focus:ring-violet-400 focus:border-transparent"
          />
        </div>

        {/* Vibes */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-2">
            What&apos;s the vibe?
          </label>
          <div className="flex flex-wrap gap-2">
            {VIBE_OPTIONS.map((vibe) => {
              const selected = vibes.includes(vibe.id);
              return (
                <button
                  key={vibe.id}
                  onClick={() => toggleVibe(vibe.id)}
                  disabled={loading}
                  className={`
                    px-4 py-2 rounded-full text-sm font-medium transition-all border
                    ${selected
                      ? "bg-slate-900 text-white border-slate-900"
                      : "bg-white text-slate-600 border-slate-300 hover:border-slate-400"
                    }
                  `}
                >
                  {vibe.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Submit */}
        <button
          onClick={handleSubmit}
          disabled={loading || !isValid}
          className={`
            w-full px-4 py-3.5 rounded-xl font-semibold text-white transition-all text-base
            ${loading || !isValid
              ? "bg-slate-300 cursor-not-allowed"
              : "bg-slate-900 hover:bg-slate-800 active:bg-slate-700"
            }
          `}
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Planning...
            </span>
          ) : (
            `Plan my ${destination.trim() || "trip"}`
          )}
        </button>
      </div>
    </div>
  );
}

export type { TripFormData };
