"use client";

import { useEffect, useState } from "react";
import type { DiscoveredEvent } from "@/shared/types/events";
import { CATEGORY_COLORS, CATEGORY_LABELS } from "@/shared/constants/categories";

// Leaflet CSS must be imported at the component level for Next.js
import "leaflet/dist/leaflet.css";

// Dynamic imports for SSR compatibility — Leaflet requires `window`
import dynamic from "next/dynamic";

const MapContainer = dynamic(
  () => import("react-leaflet").then((mod) => mod.MapContainer),
  { ssr: false },
);
const TileLayer = dynamic(
  () => import("react-leaflet").then((mod) => mod.TileLayer),
  { ssr: false },
);
const CircleMarker = dynamic(
  () => import("react-leaflet").then((mod) => mod.CircleMarker),
  { ssr: false },
);
const Popup = dynamic(
  () => import("react-leaflet").then((mod) => mod.Popup),
  { ssr: false },
);

interface MapViewProps {
  readonly events: readonly DiscoveredEvent[];
}

const DEFAULT_CENTER: [number, number] = [39.8283, -98.5795]; // US center
const DEFAULT_ZOOM = 4;

function computeCenter(events: readonly DiscoveredEvent[]): [number, number] {
  const geoEvents = events.filter((e) => e.latitude != null && e.longitude != null);
  if (geoEvents.length === 0) return DEFAULT_CENTER;

  const avgLat = geoEvents.reduce((sum, e) => sum + (e.latitude ?? 0), 0) / geoEvents.length;
  const avgLng = geoEvents.reduce((sum, e) => sum + (e.longitude ?? 0), 0) / geoEvents.length;
  return [avgLat, avgLng];
}

function computeZoom(events: readonly DiscoveredEvent[]): number {
  const geoEvents = events.filter((e) => e.latitude != null && e.longitude != null);
  if (geoEvents.length === 0) return DEFAULT_ZOOM;
  if (geoEvents.length === 1) return 13;

  const lats = geoEvents.map((e) => e.latitude ?? 0);
  const lngs = geoEvents.map((e) => e.longitude ?? 0);
  const latSpread = Math.max(...lats) - Math.min(...lats);
  const lngSpread = Math.max(...lngs) - Math.min(...lngs);
  const maxSpread = Math.max(latSpread, lngSpread);

  if (maxSpread < 0.05) return 14;
  if (maxSpread < 0.2) return 12;
  if (maxSpread < 1) return 10;
  if (maxSpread < 5) return 7;
  return 5;
}

export function MapView({ events }: MapViewProps) {
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  const geoEvents = events.filter((e) => e.latitude != null && e.longitude != null);
  const center = computeCenter(events);
  const zoom = computeZoom(events);

  if (!isClient) {
    return (
      <div className="w-full h-[500px] bg-gray-100 rounded-xl flex items-center justify-center">
        <span className="text-gray-400">Loading map...</span>
      </div>
    );
  }

  if (geoEvents.length === 0) {
    return (
      <div className="w-full h-[500px] bg-gray-50 rounded-xl flex items-center justify-center">
        <p className="text-gray-500">No geocoded events to display on the map.</p>
      </div>
    );
  }

  return (
    <div className="w-full h-[500px] rounded-xl overflow-hidden border">
      <MapContainer
        center={center}
        zoom={zoom}
        className="w-full h-full"
        scrollWheelZoom={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {geoEvents.map((event) => (
          <CircleMarker
            key={event.id}
            center={[event.latitude!, event.longitude!]}
            radius={10}
            pathOptions={{
              color: CATEGORY_COLORS[event.category] ?? "#6b7280",
              fillColor: CATEGORY_COLORS[event.category] ?? "#6b7280",
              fillOpacity: 0.8,
              weight: 2,
            }}
          >
            <Popup>
              <div className="min-w-[200px]">
                <h3 className="font-semibold text-sm">{event.name}</h3>
                <span className="text-xs text-gray-500 capitalize">
                  {CATEGORY_LABELS[event.category] ?? event.category}
                </span>
                {event.city && (
                  <span className="text-xs text-gray-400 ml-2">{event.city}</span>
                )}
                {event.description && (
                  <p className="text-xs text-gray-600 mt-1">{event.description}</p>
                )}
                {event.reddit_sentiment !== "not_found" && (
                  <p className="text-xs mt-1">
                    Reddit:{" "}
                    <span
                      className={
                        event.reddit_sentiment === "positive"
                          ? "text-green-600"
                          : event.reddit_sentiment === "negative"
                            ? "text-red-600"
                            : "text-yellow-600"
                      }
                    >
                      {event.reddit_sentiment}
                    </span>{" "}
                    ({event.reddit_mention_count} mentions)
                  </p>
                )}
                <div className="flex gap-2 mt-2">
                  {event.google_maps_url && (
                    <a
                      href={event.google_maps_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-blue-600 hover:underline"
                    >
                      Directions
                    </a>
                  )}
                  {event.google_calendar_url && (
                    <a
                      href={event.google_calendar_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-blue-600 hover:underline"
                    >
                      Add to Calendar
                    </a>
                  )}
                </div>
              </div>
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>

      {/* Legend */}
      <div className="flex flex-wrap gap-3 mt-3 px-1">
        {Array.from(new Set(geoEvents.map((e) => e.category))).map((cat) => (
          <div key={cat} className="flex items-center gap-1">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: CATEGORY_COLORS[cat] ?? "#6b7280" }}
            />
            <span className="text-xs text-gray-600">
              {CATEGORY_LABELS[cat] ?? cat}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
