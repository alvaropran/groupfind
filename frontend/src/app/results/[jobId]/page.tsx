"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { apiClient } from "@/lib/apiClient";
import type { Activity, ActivityResults, BookingOption, ReviewData } from "@/shared/types/activity";

function StarRating({ rating }: { readonly rating: number }) {
  const full = Math.floor(rating);
  const half = rating - full >= 0.5;
  return (
    <span className="inline-flex items-center gap-0.5">
      {Array.from({ length: 5 }, (_, i) => (
        <span
          key={i}
          className={`text-sm ${i < full ? "text-amber-400" : i === full && half ? "text-amber-300" : "text-slate-200"}`}
        >
          ★
        </span>
      ))}
      <span className="ml-1 text-sm font-semibold text-slate-700">{rating.toFixed(1)}</span>
    </span>
  );
}

function ReviewSection({ review }: { readonly review: ReviewData }) {
  return (
    <div className="mt-3 p-4 bg-slate-50 rounded-xl border border-slate-200">
      <div className="flex items-center justify-between mb-2">
        {review.rating && <StarRating rating={review.rating} />}
        {review.sources.length > 0 && (
          <span className="text-xs text-slate-400">
            via {review.sources.join(", ")}
          </span>
        )}
      </div>

      {review.summary && (
        <p className="text-sm text-slate-600 leading-relaxed">{review.summary}</p>
      )}

      {(review.pros.length > 0 || review.cons.length > 0) && (
        <div className="grid grid-cols-2 gap-3 mt-3">
          {review.pros.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-green-700 mb-1">Pros</p>
              <ul className="space-y-0.5">
                {review.pros.map((pro, i) => (
                  <li key={i} className="text-xs text-slate-600 flex gap-1">
                    <span className="text-green-500 flex-shrink-0">+</span> {pro}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {review.cons.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-red-700 mb-1">Cons</p>
              <ul className="space-y-0.5">
                {review.cons.map((con, i) => (
                  <li key={i} className="text-xs text-slate-600 flex gap-1">
                    <span className="text-red-400 flex-shrink-0">-</span> {con}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {review.best_tip && (
        <div className="mt-3 px-3 py-2 bg-amber-50 border border-amber-200 rounded-lg">
          <p className="text-xs text-amber-800">
            <strong>Top tip:</strong> {review.best_tip}
          </p>
        </div>
      )}
    </div>
  );
}

function BookingSection({ options }: { readonly options: readonly BookingOption[] }) {
  if (options.length === 0) return null;

  return (
    <div className="mt-3">
      <p className="text-xs font-semibold text-slate-500 mb-2">Book this activity</p>
      <div className="flex flex-wrap gap-2">
        {options.map((opt, i) => (
          <a
            key={i}
            href={opt.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-3 py-2 bg-white border border-slate-300 rounded-lg hover:border-blue-400 hover:shadow-sm transition-all text-sm"
          >
            <span className="font-medium text-slate-800">{opt.provider}</span>
            {opt.price && (
              <span className="text-xs text-green-700 font-semibold">{opt.price}</span>
            )}
            <svg className="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>
        ))}
      </div>
    </div>
  );
}

const TYPE_LABELS: Record<string, string> = {
  tour: "Tour",
  adventure: "Adventure",
  class: "Class",
  day_trip: "Day Trip",
  show: "Show",
  wellness: "Wellness",
  water_sport: "Water Sport",
  cultural: "Cultural",
  nature: "Nature",
  other: "Activity",
};

function ActivityCard({ activity }: { readonly activity: Activity }) {
  return (
    <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-5">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-bold text-slate-900">{activity.name}</h3>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-xs px-2.5 py-0.5 bg-slate-100 text-slate-600 rounded-full font-medium">
              {TYPE_LABELS[activity.type] ?? activity.type}
            </span>
            {activity.area && (
              <span className="text-xs text-slate-500">{activity.area}</span>
            )}
          </div>
        </div>
        {activity.review?.rating && (
          <StarRating rating={activity.review.rating} />
        )}
      </div>

      {activity.who_suggested && (
        <p className="mt-2 text-sm text-slate-500">
          Suggested by <span className="font-medium text-slate-700">@{activity.who_suggested}</span>
          {activity.what_they_said && (
            <span>: &ldquo;{activity.what_they_said}&rdquo;</span>
          )}
        </p>
      )}

      {activity.details && (
        <p className="mt-1 text-xs text-slate-400">{activity.details}</p>
      )}

      {activity.review && <ReviewSection review={activity.review} />}

      <BookingSection options={activity.booking_options} />
    </div>
  );
}

export default function ResultsPage() {
  const params = useParams();
  const jobId = typeof params.jobId === "string" ? params.jobId : null;
  const [data, setData] = useState<ActivityResults | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) return;
    apiClient
      .get<ActivityResults>(`/results/${jobId}`)
      .then(setData)
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load results");
      });
  }, [jobId]);

  if (!jobId) {
    return (
      <main className="flex-1 flex items-center justify-center">
        <p className="text-slate-500">Invalid job ID</p>
      </main>
    );
  }

  if (error) {
    return (
      <main className="flex-1 flex items-center justify-center">
        <div className="p-4 bg-red-50 rounded-lg">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="flex-1 flex items-center justify-center">
        <div className="flex items-center gap-3">
          <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-slate-500">Loading activities...</span>
        </div>
      </main>
    );
  }

  const withReviews = data.activities.filter((a) => a.review?.rating);
  const withoutReviews = data.activities.filter((a) => !a.review?.rating);

  return (
    <main className="flex-1 px-4 py-8 max-w-3xl mx-auto w-full">
      <div className="text-center mb-10">
        <h1 className="text-3xl font-bold text-slate-900">
          {data.destination} Activities
        </h1>
        <p className="text-slate-500 mt-2">
          {data.activities.length} activities found from {data.message_count.toLocaleString()} messages
        </p>
        <p className="text-xs text-slate-400 mt-1">
          Verified with online reviews &middot; Booking links included
        </p>
      </div>

      <div className="space-y-5">
        {withReviews.map((activity) => (
          <ActivityCard key={activity.id} activity={activity} />
        ))}
        {withoutReviews.map((activity) => (
          <ActivityCard key={activity.id} activity={activity} />
        ))}
      </div>
    </main>
  );
}
