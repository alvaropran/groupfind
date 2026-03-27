export interface ReviewData {
  readonly rating: number | null;
  readonly summary: string | null;
  readonly pros: readonly string[];
  readonly cons: readonly string[];
  readonly best_tip: string | null;
  readonly sources: readonly string[];
}

export interface BookingOption {
  readonly provider: string;
  readonly url: string;
  readonly title: string;
  readonly price: string | null;
}

export interface Activity {
  readonly id: string;
  readonly name: string;
  readonly type: string;
  readonly area: string | null;
  readonly destination: string;
  readonly who_suggested: string | null;
  readonly what_they_said: string | null;
  readonly details: string | null;
  readonly review: ReviewData | null;
  readonly booking_options: readonly BookingOption[];
}

export interface ActivityResults {
  readonly destination: string;
  readonly activities: readonly Activity[];
  readonly message_count: number;
}
