"""Extract bookable activities and tours from group chat messages.

Focused specifically on experiences you can DO and BOOK:
snorkeling, temple tours, cooking classes, boat tours, etc.
NOT restaurants, hotels, or generic places.
"""

import logging
from dataclasses import dataclass

from src.pipeline.utils.llm_client import LLMError, call_llm, parse_llm_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are reading a group of friends' Instagram chat. \
They share reels and discuss activities and tours they want to do on a trip to {destination}.

Your job: Extract every BOOKABLE ACTIVITY, TOUR, or EXPERIENCE that anyone recommended.

INCLUDE:
- Tours (temple tours, food tours, walking tours, boat tours)
- Adventure activities (snorkeling, diving, surfing, zip lining, ATV rides, rafting)
- Classes (cooking classes, craft workshops, dance classes)
- Day trips and excursions
- Shows and performances
- Wellness (spa treatments, yoga retreats, sound baths)
- Water activities (jet ski, parasailing, kayaking)
- Cultural experiences (ceremonies, local festivals, village visits)
- Nature activities (hiking, volcano treks, waterfall visits, rice terrace walks)

DO NOT INCLUDE:
- Restaurants, cafes, or food spots (unless it's a food tour/cooking class)
- Hotels, villas, hostels, or any accommodation
- Generic places ("the beach", "the market", "the mall")
- Transportation (Grab, flights, ferries as transport — but a boat TOUR is fine)
- Shopping
- Casual conversation not about activities

IMPORTANT:
- MERGE similar activities into one. E.g., "Ijen trek" and "Mount Ijen tour" = same activity
- Use the most commonly known name for each activity
- For each activity note WHO recommended it and WHAT they said about it
- Return valid JSON only"""

EXTRACT_PROMPT = """Extract all bookable activities and tours for {destination} from these messages.

MESSAGES:
{messages}

Return JSON:
{{
  "activities": [
    {{
      "name": "Full name of the activity or tour",
      "type": "tour|adventure|class|day_trip|show|wellness|water_sport|cultural|nature|other",
      "area": "specific area or region within {destination}",
      "who_suggested": "person's name from the chat",
      "what_they_said": "what they said about it / why they recommend it",
      "details": "any specifics mentioned (duration, price, provider, tips)"
    }}
  ]
}}"""

MAX_MESSAGES_PER_BATCH = 200
MAX_CHARS_PER_BATCH = 12000


@dataclass(frozen=True)
class ExtractedActivity:
    name: str
    type: str
    area: str | None
    who_suggested: str | None
    what_they_said: str | None
    details: str | None


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


def _validate_activity(raw: dict) -> ExtractedActivity | None:
    name = raw.get("name", "").strip()
    if not name or len(name) < 3:
        return None

    valid_types = {
        "tour", "adventure", "class", "day_trip", "show",
        "wellness", "water_sport", "cultural", "nature", "other",
    }
    activity_type = raw.get("type", "other")
    if activity_type not in valid_types:
        activity_type = "other"

    return ExtractedActivity(
        name=name,
        type=activity_type,
        area=raw.get("area") or None,
        who_suggested=raw.get("who_suggested") or None,
        what_they_said=raw.get("what_they_said") or None,
        details=raw.get("details") or None,
    )


def _normalize_key(name: str) -> str:
    """Normalize an activity name for deduplication.

    'Mount Ijen Trek' and 'Ijen Volcano Tour' should match.
    """
    key = name.lower().strip()
    # Remove common prefixes/suffixes
    for word in ["mount ", "mt ", "mt. ", "the ", "a "]:
        if key.startswith(word):
            key = key[len(word):]
    for word in [" tour", " trek", " trip", " excursion", " experience", " activity", " class"]:
        if key.endswith(word):
            key = key[: -len(word)]
    return key.strip()


def _is_accommodation(name: str) -> bool:
    """Filter out accommodation that slipped through the LLM."""
    lower = name.lower()
    return any(word in lower for word in ["villa ", "hotel ", "hostel ", "resort ", "airbnb", "homestay"])


def _merge_activities(activities: list[ExtractedActivity]) -> list[ExtractedActivity]:
    # First filter out accommodation
    activities = [a for a in activities if not _is_accommodation(a.name)]

    seen: dict[str, ExtractedActivity] = {}
    for act in activities:
        key = _normalize_key(act.name)

        # Check if any existing key is a substring or vice versa
        matched_key = None
        for existing_key in seen:
            if key in existing_key or existing_key in key:
                matched_key = existing_key
                break

        target_key = matched_key or key
        existing = seen.get(target_key)

        if existing is None:
            seen[target_key] = act
        else:
            merged_who = existing.who_suggested or ""
            if act.who_suggested and act.who_suggested not in merged_who:
                merged_who = f"{merged_who}, {act.who_suggested}" if merged_who else act.who_suggested

            merged_details = existing.details or ""
            if act.details and act.details not in merged_details:
                merged_details = f"{merged_details}; {act.details}" if merged_details else act.details

            merged_said = existing.what_they_said or ""
            if act.what_they_said and act.what_they_said not in merged_said:
                merged_said = f"{merged_said}; {act.what_they_said}" if merged_said else act.what_they_said

            seen[target_key] = ExtractedActivity(
                name=act.name if len(act.name) >= len(existing.name) else existing.name,
                type=existing.type,
                area=existing.area or act.area,
                who_suggested=merged_who or None,
                what_they_said=merged_said or None,
                details=merged_details or None,
            )

    return list(seen.values())


async def extract_activities(
    messages: list[dict],
    destination: str,
) -> list[ExtractedActivity]:
    """Extract bookable activities/tours from chat messages."""
    if not messages:
        return []

    all_activities: list[ExtractedActivity] = []
    batches = _batch_messages(messages)

    for batch in batches:
        formatted = _format_messages(batch)
        system = SYSTEM_PROMPT.format(destination=destination)
        prompt = EXTRACT_PROMPT.format(
            destination=destination,
            messages=formatted,
        )

        try:
            response = await call_llm(prompt, system=system)
            parsed = parse_llm_json(response)
        except LLMError as e:
            logger.error("Activity extraction failed: %s", e)
            continue

        raw_activities = parsed.get("activities", []) if isinstance(parsed, dict) else parsed
        for raw in raw_activities:
            act = _validate_activity(raw)
            if act is not None:
                all_activities.append(act)

    return _merge_activities(all_activities)
