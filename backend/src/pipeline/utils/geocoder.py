"""Geocode venue names/addresses to lat/lng using Nominatim (OpenStreetMap).

Nominatim is free, no API key needed. Rate limit: 1 request per second.
https://nominatim.org/release-docs/latest/api/Search/
"""

import logging
import time
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
RATE_LIMIT_SECONDS = 1.1  # Nominatim requires max 1 req/sec
USER_AGENT = "GroupFind/0.1.0 (event-discovery-app)"


@dataclass(frozen=True)
class GeocodingResult:
    latitude: float
    longitude: float
    display_name: str


async def geocode(query: str) -> GeocodingResult | None:
    """Geocode a venue name or address to coordinates.

    Args:
        query: Venue name with optional city (e.g., "Tatiana Restaurant, NYC").

    Returns:
        GeocodingResult with lat/lng, or None if not found.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(
                NOMINATIM_URL,
                params={
                    "q": query,
                    "format": "json",
                    "limit": 1,
                    "addressdetails": 0,
                },
                headers={"User-Agent": USER_AGENT},
            )
            response.raise_for_status()
            results = response.json()

            if not results:
                return None

            first = results[0]
            return GeocodingResult(
                latitude=float(first["lat"]),
                longitude=float(first["lon"]),
                display_name=first.get("display_name", ""),
            )
        except Exception as e:
            logger.warning("Geocoding failed for '%s': %s", query, e)
            return None


async def geocode_batch(
    queries: list[str],
) -> list[tuple[str, GeocodingResult | None]]:
    """Geocode multiple queries with rate limiting.

    Args:
        queries: List of venue name/address strings.

    Returns:
        List of (query, result_or_none) tuples.
    """
    results: list[tuple[str, GeocodingResult | None]] = []

    for i, query in enumerate(queries):
        result = await geocode(query)
        results.append((query, result))

        # Rate limit (skip after last)
        if i < len(queries) - 1:
            time.sleep(RATE_LIMIT_SECONDS)

    return results
