import type { Category } from "@/shared/types/events";

export const CATEGORY_LABELS: Record<Category, string> = {
  restaurant: "Restaurant",
  bar: "Bar",
  concert: "Concert",
  travel_spot: "Travel Spot",
  activity: "Activity",
  nightlife: "Nightlife",
  cafe: "Cafe",
  other: "Other",
};

export const CATEGORY_COLORS: Record<Category, string> = {
  restaurant: "#ef4444",
  bar: "#f59e0b",
  concert: "#8b5cf6",
  travel_spot: "#06b6d4",
  activity: "#22c55e",
  nightlife: "#ec4899",
  cafe: "#a855f7",
  other: "#6b7280",
};
