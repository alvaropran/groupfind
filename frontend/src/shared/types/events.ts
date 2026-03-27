export const CATEGORIES = [
  "restaurant",
  "bar",
  "concert",
  "travel_spot",
  "activity",
  "nightlife",
  "cafe",
  "other",
] as const;

export type Category = (typeof CATEGORIES)[number];

export type RedditSentiment = "positive" | "mixed" | "negative" | "not_found";

export interface DiscoveredEvent {
  readonly id: string;
  readonly name: string;
  readonly category: Category;
  readonly description: string | null;
  readonly city: string | null;
  readonly address: string | null;
  readonly latitude: number | null;
  readonly longitude: number | null;
  readonly confidence_score: number;
  readonly source_type: string;
  readonly google_maps_url: string | null;
  readonly google_calendar_url: string | null;
  readonly reddit_sentiment: RedditSentiment;
  readonly reddit_mention_count: number;
  readonly reddit_verifications: readonly RedditVerification[];
}

export interface RedditVerification {
  readonly id: string;
  readonly subreddit: string;
  readonly post_title: string;
  readonly post_url: string;
  readonly post_score: number;
  readonly comment_snippet: string | null;
  readonly sentiment: RedditSentiment;
}

export interface ExtractedMessage {
  readonly id: string;
  readonly sender_name: string;
  readonly content: string;
  readonly timestamp_ms: number;
  readonly message_type: string;
}
