"""Two-phase LLM itinerary generator.

Phase A: Extract recommendations from group chat messages.
Phase B: Generate a day-by-day itinerary from those recommendations + trip details.
"""

import json
import logging
from dataclasses import dataclass

from src.pipeline.utils.llm_client import LLMError, call_llm, parse_llm_json

logger = logging.getLogger(__name__)

# --- Phase A: Extract recommendations ---

EXTRACT_SYSTEM = """You are reading a group of friends' Instagram chat. \
They share reels, links, and discuss places they want to visit for a trip to {destination}.

Your job: Extract every SPECIFIC place, activity, restaurant, hotel, bar, beach, temple, \
tour, or thing to do that anyone recommended or discussed for {destination}.

Rules:
- Only extract things RELEVANT to {destination} or nearby areas
- Note WHO recommended it (their name from the chat)
- Note WHAT they said about it (quote or paraphrase their recommendation)
- Note any TIPS (best time, need reservations, cost, how to get there, etc.)
- Skip casual conversation, jokes, logistics like flights/visas (unless a specific tip)
- If the same place is mentioned multiple times, combine into one entry
- Return valid JSON only"""

EXTRACT_PROMPT = """Extract all {destination} trip recommendations from these messages.

MESSAGES:
{messages}

Return JSON:
{{
  "recommendations": [
    {{
      "name": "Full name of place/activity",
      "type": "restaurant|hotel|beach|temple|tour|bar|nightlife|market|landmark|park|activity|cafe|other",
      "who_said": "person's name from the chat",
      "what_they_said": "what they said about it or why they recommend it",
      "tips": "any practical tips mentioned (timing, cost, reservations, etc.)",
      "area": "neighborhood or sub-region within {destination} if mentioned"
    }}
  ]
}}"""

# --- Phase B: Generate itinerary ---

PLAN_SYSTEM = """You are an expert travel planner creating a day-by-day itinerary for a group of friends.

You have a list of recommendations extracted from their group chat — real places they've been \
sharing and discussing. Build a practical, enjoyable itinerary using these recommendations.

Planning rules:
- Group activities geographically — don't zigzag across the destination
- Respect time of day: temples/nature = morning, beaches = midday, restaurants = meal times, nightlife = evening
- Include travel time and logistics between activities
- Build in some flexibility — not every minute needs to be scheduled
- Mix vibes based on their preferences: {vibes}
- For {num_travelers} travelers
- If there aren't enough chat recommendations to fill every slot, add your own expert suggestions \
  but clearly mark them as "(suggested)" vs the friends' recommendations
- Include practical tips: how to get there, what to wear, reservations needed, approximate cost
- Day 1 should account for arrival, last day for departure
- Return valid JSON only"""

PLAN_PROMPT = """Create a {num_days}-day itinerary for {destination}, starting {start_date}.

RECOMMENDATIONS FROM THE GROUP CHAT:
{recommendations}

Return JSON:
{{
  "days": [
    {{
      "day_number": 1,
      "title": "Short title for the day (e.g., 'Arrive & Explore Ubud')",
      "notes": "Any day-level notes (travel between areas, weather tip, etc.)",
      "slots": [
        {{
          "time_of_day": "morning|afternoon|evening",
          "activity_name": "Name of the place or activity",
          "description": "What to do there and why, include travel logistics if relevant",
          "who_suggested": "friend's name or null if it's your suggestion",
          "tip": "practical tip (timing, cost, reservations, etc.) or null",
          "location": "address or area name for Google Maps"
        }}
      ]
    }}
  ]
}}

Make sure every slot has a clear activity. 2-4 slots per day is ideal. \
The itinerary should feel like a real trip plan a friend would make, not a guidebook."""


MAX_MESSAGES_PER_BATCH = 200
MAX_CHARS_PER_BATCH = 12000


@dataclass(frozen=True)
class Recommendation:
    name: str
    type: str
    who_said: str | None
    what_they_said: str | None
    tips: str | None
    area: str | None


@dataclass(frozen=True)
class ItinerarySlot:
    time_of_day: str
    activity_name: str
    description: str
    who_suggested: str | None
    tip: str | None
    location: str | None


@dataclass(frozen=True)
class ItineraryDay:
    day_number: int
    title: str
    notes: str | None
    slots: list[ItinerarySlot]


@dataclass(frozen=True)
class GeneratedItinerary:
    days: list[ItineraryDay]
    recommendations: list[Recommendation]


def _format_messages(messages: list[dict]) -> str:
    lines = []
    for msg in messages:
        sender = msg.get("sender_name", "Unknown")
        content = msg.get("content", "")
        if content:
            lines.append(f"[{sender}]: {content}")
    return "\n".join(lines)


def _batch_messages(messages: list[dict]) -> list[list[dict]]:
    batches: list[list[dict]] = []
    current_batch: list[dict] = []
    current_chars = 0

    for msg in messages:
        content = msg.get("content", "")
        msg_chars = len(content) + len(msg.get("sender_name", ""))

        if (
            len(current_batch) >= MAX_MESSAGES_PER_BATCH
            or current_chars + msg_chars > MAX_CHARS_PER_BATCH
        ):
            if current_batch:
                batches.append(current_batch)
            current_batch = [msg]
            current_chars = msg_chars
        else:
            current_batch.append(msg)
            current_chars += msg_chars

    if current_batch:
        batches.append(current_batch)

    return batches


def _validate_recommendation(raw: dict) -> Recommendation | None:
    name = raw.get("name", "").strip()
    if not name or len(name) < 3:
        return None

    return Recommendation(
        name=name,
        type=raw.get("type", "other"),
        who_said=raw.get("who_said") or None,
        what_they_said=raw.get("what_they_said") or None,
        tips=raw.get("tips") or None,
        area=raw.get("area") or None,
    )


def _merge_recommendations(recs: list[Recommendation]) -> list[Recommendation]:
    seen: dict[str, Recommendation] = {}
    for rec in recs:
        key = rec.name.lower().strip()
        existing = seen.get(key)
        if existing is None:
            seen[key] = rec
        else:
            # Merge: combine tips and what_they_said
            merged_what = existing.what_they_said or ""
            if rec.what_they_said and rec.what_they_said not in merged_what:
                merged_what = f"{merged_what}; {rec.what_they_said}" if merged_what else rec.what_they_said

            merged_tips = existing.tips or ""
            if rec.tips and rec.tips not in merged_tips:
                merged_tips = f"{merged_tips}; {rec.tips}" if merged_tips else rec.tips

            seen[key] = Recommendation(
                name=rec.name if len(rec.name) >= len(existing.name) else existing.name,
                type=existing.type,
                who_said=f"{existing.who_said}, {rec.who_said}" if existing.who_said and rec.who_said and rec.who_said not in existing.who_said else existing.who_said or rec.who_said,
                what_they_said=merged_what or None,
                tips=merged_tips or None,
                area=existing.area or rec.area,
            )

    return list(seen.values())


def _format_recommendations(recs: list[Recommendation]) -> str:
    lines = []
    for rec in recs:
        parts = [f"- {rec.name} ({rec.type})"]
        if rec.who_said:
            parts.append(f"  Recommended by: {rec.who_said}")
        if rec.what_they_said:
            parts.append(f"  What they said: {rec.what_they_said}")
        if rec.tips:
            parts.append(f"  Tips: {rec.tips}")
        if rec.area:
            parts.append(f"  Area: {rec.area}")
        lines.append("\n".join(parts))
    return "\n\n".join(lines)


def _parse_itinerary(raw: dict | list) -> list[ItineraryDay]:
    days_raw = raw.get("days", []) if isinstance(raw, dict) else raw
    days: list[ItineraryDay] = []

    for d in days_raw:
        slots: list[ItinerarySlot] = []
        for s in d.get("slots", []):
            time = s.get("time_of_day", "morning")
            if time not in ("morning", "afternoon", "evening"):
                time = "morning"

            slots.append(ItinerarySlot(
                time_of_day=time,
                activity_name=s.get("activity_name", "Activity"),
                description=s.get("description", ""),
                who_suggested=s.get("who_suggested") or None,
                tip=s.get("tip") or None,
                location=s.get("location") or None,
            ))

        days.append(ItineraryDay(
            day_number=d.get("day_number", len(days) + 1),
            title=d.get("title", f"Day {len(days) + 1}"),
            notes=d.get("notes") or None,
            slots=slots,
        ))

    return days


async def extract_recommendations(
    messages: list[dict],
    destination: str,
) -> list[Recommendation]:
    """Phase A: Extract trip recommendations from chat messages."""
    all_recs: list[Recommendation] = []
    batches = _batch_messages(messages)

    for batch in batches:
        formatted = _format_messages(batch)
        system = EXTRACT_SYSTEM.format(destination=destination)
        prompt = EXTRACT_PROMPT.format(
            destination=destination,
            messages=formatted,
        )

        try:
            response = await call_llm(prompt, system=system)
            parsed = parse_llm_json(response)
        except LLMError as e:
            logger.error("Recommendation extraction failed: %s", e)
            continue

        raw_recs = parsed.get("recommendations", []) if isinstance(parsed, dict) else parsed
        for raw in raw_recs:
            rec = _validate_recommendation(raw)
            if rec is not None:
                all_recs.append(rec)

    return _merge_recommendations(all_recs)


async def generate_itinerary(
    recommendations: list[Recommendation],
    destination: str,
    start_date: str,
    num_days: int,
    num_travelers: int,
    vibes: list[str],
) -> GeneratedItinerary:
    """Phase B: Generate a day-by-day itinerary from recommendations + trip details."""
    formatted_recs = _format_recommendations(recommendations)
    vibes_str = ", ".join(vibes) if vibes else "general exploration"

    system = PLAN_SYSTEM.format(
        vibes=vibes_str,
        num_travelers=num_travelers,
    )
    prompt = PLAN_PROMPT.format(
        num_days=num_days,
        destination=destination,
        start_date=start_date,
        recommendations=formatted_recs if formatted_recs else "(No specific recommendations found in chat — use your expert knowledge to plan a great trip)",
    )

    try:
        response = await call_llm(prompt, system=system)
        parsed = parse_llm_json(response)
    except LLMError as e:
        logger.error("Itinerary generation failed: %s", e)
        raise

    days = _parse_itinerary(parsed)

    return GeneratedItinerary(
        days=days,
        recommendations=recommendations,
    )
