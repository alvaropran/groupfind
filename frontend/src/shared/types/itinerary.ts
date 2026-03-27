export interface ItinerarySlot {
  readonly id: string;
  readonly time_of_day: "morning" | "afternoon" | "evening";
  readonly activity_name: string;
  readonly description: string;
  readonly who_suggested: string | null;
  readonly tip: string | null;
  readonly location: string | null;
  readonly google_maps_url: string | null;
  readonly google_calendar_url: string | null;
}

export interface ItineraryDay {
  readonly day_number: number;
  readonly date: string;
  readonly title: string;
  readonly notes: string | null;
  readonly slots: readonly ItinerarySlot[];
}

export interface Itinerary {
  readonly destination: string;
  readonly start_date: string;
  readonly num_days: number;
  readonly num_travelers: number;
  readonly vibes: readonly string[];
  readonly days: readonly ItineraryDay[];
}

export interface Recommendation {
  readonly name: string;
  readonly type: string;
  readonly who_said: string | null;
  readonly what_they_said: string | null;
  readonly tips: string | null;
  readonly area: string | null;
}

export interface ItineraryResults {
  readonly itinerary: Itinerary;
  readonly recommendations: readonly Recommendation[];
  readonly message_count: number;
}
