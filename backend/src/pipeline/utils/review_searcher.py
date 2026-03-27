"""Search the web for activity reviews and booking links.

Uses LLM knowledge for review summaries (most reliable).
Builds direct search URLs for booking providers (always works).
"""

import logging
from dataclasses import dataclass
from urllib.parse import quote_plus

from src.pipeline.utils.llm_client import LLMError, call_llm, parse_llm_json

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReviewSummary:
    rating: float
    summary: str
    pros: list[str]
    cons: list[str]
    best_tip: str | None
    sources: list[str]


@dataclass(frozen=True)
class BookingOption:
    provider: str
    url: str
    title: str
    price: str | None


REVIEW_SYSTEM = """You are an expert travel reviewer. Based on your extensive knowledge of \
travel reviews from TripAdvisor, Reddit, Google Reviews, and travel blogs, \
give an honest review summary for a travel activity.

Be specific and practical. Mention real details like prices, timing, crowds.
Return valid JSON only."""

REVIEW_PROMPT = """Give an honest review summary for: "{activity_name}" in {destination}

Return JSON:
{{
  "rating": 4.2,
  "summary": "2-3 sentence honest consensus based on what travelers typically say",
  "pros": ["specific pro 1", "specific pro 2", "specific pro 3"],
  "cons": ["specific con 1", "specific con 2"],
  "best_tip": "single most useful practical tip for someone doing this activity",
  "estimated_cost": "$25-40 per person" or null,
  "duration": "3-4 hours" or null,
  "sources": ["TripAdvisor", "Reddit", "travel blogs"]
}}

Be honest — if it's touristy but fun, say so. If overpriced, say so. \
Include approximate costs and duration if known."""


async def search_reviews(
    activity_name: str,
    destination: str,
) -> ReviewSummary | None:
    """Get a review summary using AI knowledge."""
    short_dest = destination.split(",")[0].strip()

    try:
        response = await call_llm(
            REVIEW_PROMPT.format(
                activity_name=activity_name,
                destination=short_dest,
            ),
            system=REVIEW_SYSTEM,
        )
        parsed = parse_llm_json(response)
    except LLMError as e:
        logger.warning("Review generation failed for '%s': %s", activity_name, e)
        return None

    rating = parsed.get("rating", 3.0)
    if not isinstance(rating, (int, float)):
        rating = 3.0
    rating = max(1.0, min(5.0, float(rating)))

    # Include cost/duration in the summary if provided
    summary = parsed.get("summary", "")
    cost = parsed.get("estimated_cost")
    duration = parsed.get("duration")
    extras = []
    if cost:
        extras.append(f"Cost: {cost}")
    if duration:
        extras.append(f"Duration: {duration}")
    if extras:
        summary = f"{summary} ({', '.join(extras)})"

    return ReviewSummary(
        rating=rating,
        summary=summary,
        pros=parsed.get("pros", [])[:5],
        cons=parsed.get("cons", [])[:5],
        best_tip=parsed.get("best_tip") or None,
        sources=parsed.get("sources", []),
    )


async def search_booking_links(
    activity_name: str,
    destination: str,
) -> list[BookingOption]:
    """Build direct search URLs for booking providers.

    Links to search results on GetYourGuide, Viator, Klook.
    Always works — no web scraping needed.
    """
    short_dest = destination.split(",")[0].strip()
    query = quote_plus(f"{activity_name} {short_dest}")

    return [
        BookingOption(
            provider="GetYourGuide",
            url=f"https://www.getyourguide.com/s/?q={query}",
            title=f"Search on GetYourGuide",
            price=None,
        ),
        BookingOption(
            provider="Viator",
            url=f"https://www.viator.com/searchResults/all?text={query}",
            title=f"Search on Viator",
            price=None,
        ),
        BookingOption(
            provider="Klook",
            url=f"https://www.klook.com/search/?query={query}",
            title=f"Search on Klook",
            price=None,
        ),
    ]
