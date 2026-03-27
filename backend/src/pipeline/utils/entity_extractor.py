"""Extract venues, events, and activities from chat messages using an LLM.

Takes batches of messages and reel captions, sends them to Llama 3.1,
and returns structured entity data with name, category, city, and confidence.
"""

import logging
from dataclasses import dataclass

from src.pipeline.utils.llm_client import LLMError, call_llm, parse_llm_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an assistant that extracts REAL, NOTABLE venues and destinations \
from a group of friends' Instagram chat. They share reels and discuss places they want to visit together.

STRICT RULES:
- Only extract places that are REAL destinations someone would actually visit on a trip \
(restaurants, hotels, beaches, landmarks, tours, bars, clubs, parks, temples, markets)
- A place must be mentioned as a RECOMMENDATION or plan, not just in passing conversation
- Do NOT extract: people's names, inside jokes, generic locations ("the mall", "his house"), \
nicknames, memes, one-off mentions with no travel intent, services (Uber, airlines), \
or vague references ("that place")
- If multiple people discuss a place or someone says "we should go" / "add this to the list" / \
"let's do this" — that's HIGH confidence
- If it's just mentioned once casually — that's LOW confidence (below 0.4), skip it
- MERGE duplicates: if the same place appears with different names or spellings, combine them
- Include the FULL proper name of the venue, not abbreviations
- For the address field: include the specific address if mentioned, otherwise just city + country
- Return valid JSON only"""

SYSTEM_PROMPT_WITH_FOCUS = """You are an assistant that extracts REAL, NOTABLE venues and destinations \
from a group of friends' Instagram chat. They share reels and discuss places they want to visit together.

The user is specifically interested in: {focus}
Prioritize and surface results related to this focus. Still include other strong recommendations, \
but weight results toward the focus topic.

STRICT RULES:
- Only extract places that are REAL destinations someone would actually visit on a trip \
(restaurants, hotels, beaches, landmarks, tours, bars, clubs, parks, temples, markets)
- A place must be mentioned as a RECOMMENDATION or plan, not just in passing conversation
- Do NOT extract: people's names, inside jokes, generic locations ("the mall", "his house"), \
nicknames, memes, one-off mentions with no travel intent, services (Uber, airlines), \
or vague references ("that place")
- If multiple people discuss a place or someone says "we should go" / "add this to the list" / \
"let's do this" — that's HIGH confidence
- If it's just mentioned once casually — that's LOW confidence (below 0.4), skip it
- MERGE duplicates: if the same place appears with different names or spellings, combine them
- Include the FULL proper name of the venue, not abbreviations
- For the address field: include the specific address if mentioned, otherwise just city + country
- Return valid JSON only"""

USER_PROMPT_TEMPLATE = """Analyze these group chat messages. \
Extract ONLY real, visitable places that the group is planning or recommending to each other.

{focus_instruction}

MESSAGES:
{messages}

REEL CAPTIONS:
{captions}

Return a JSON object with this exact structure:
{{
  "events": [
    {{
      "name": "Full proper name of the place",
      "category": "restaurant|bar|hotel|beach|landmark|tour|nightlife|cafe|market|temple|park|other",
      "city": "City name",
      "country": "Country name",
      "address": "Specific address if known, otherwise city + country",
      "description": "Why the group wants to go / what was said about it",
      "confidence": 0.85,
      "mention_count": 3
    }}
  ]
}}

Only include places with confidence >= 0.5. Merge duplicates."""

MAX_MESSAGES_PER_BATCH = 200
MAX_CHARS_PER_BATCH = 12000


@dataclass(frozen=True)
class ExtractedEntity:
    name: str
    category: str
    city: str | None
    country: str | None
    address: str | None
    description: str | None
    confidence: float
    mention_count: int


def _format_messages(messages: list[dict]) -> str:
    """Format messages for the LLM prompt."""
    lines = []
    for msg in messages:
        sender = msg.get("sender_name", "Unknown")
        content = msg.get("content", "")
        if content:
            lines.append(f"[{sender}]: {content}")
    return "\n".join(lines)


def _format_captions(captions: list[str]) -> str:
    """Format reel captions for the LLM prompt."""
    if not captions:
        return "(none)"
    return "\n".join(f"- {cap}" for cap in captions if cap)


def _batch_messages(
    messages: list[dict],
) -> list[list[dict]]:
    """Split messages into batches that fit within LLM context."""
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


def _validate_entity(raw: dict) -> ExtractedEntity | None:
    """Validate and normalize a raw entity dict from the LLM."""
    name = raw.get("name", "").strip()
    if not name or len(name) < 3:
        return None

    category = raw.get("category", "other")
    valid_categories = {
        "restaurant", "bar", "hotel", "beach", "landmark", "tour",
        "nightlife", "cafe", "market", "temple", "park",
        "concert", "travel_spot", "activity", "other",
    }
    if category not in valid_categories:
        category = "other"

    confidence = raw.get("confidence", 0.5)
    if not isinstance(confidence, (int, float)):
        confidence = 0.5
    confidence = max(0.0, min(1.0, float(confidence)))

    # Skip low confidence results
    if confidence < 0.5:
        return None

    city = raw.get("city")
    if city and isinstance(city, str):
        city = city.strip() or None
    else:
        city = None

    country = raw.get("country")
    if country and isinstance(country, str):
        country = country.strip() or None
    else:
        country = None

    address = raw.get("address")
    if address and isinstance(address, str):
        address = address.strip() or None
    else:
        address = None

    description = raw.get("description")
    if description and isinstance(description, str):
        description = description.strip() or None
    else:
        description = None

    mention_count = raw.get("mention_count", 1)
    if not isinstance(mention_count, int):
        mention_count = 1

    return ExtractedEntity(
        name=name,
        category=category,
        city=city,
        country=country,
        address=address,
        description=description,
        confidence=confidence,
        mention_count=mention_count,
    )


def _merge_entities(entities: list[ExtractedEntity]) -> list[ExtractedEntity]:
    """Merge duplicate entities by normalized name, keeping highest confidence."""
    seen: dict[str, ExtractedEntity] = {}
    for entity in entities:
        # Normalize: lowercase, strip common suffixes
        key = entity.name.lower().strip()
        for suffix in [" restaurant", " bar", " hotel", " beach", " cafe"]:
            if key.endswith(suffix):
                alt_key = key[: -len(suffix)]
                if alt_key in seen:
                    key = alt_key
                    break

        existing = seen.get(key)
        if existing is None:
            seen[key] = entity
        else:
            # Merge: take highest confidence, sum mention counts, keep longer description
            merged = ExtractedEntity(
                name=entity.name if len(entity.name) >= len(existing.name) else existing.name,
                category=entity.category if entity.confidence > existing.confidence else existing.category,
                city=entity.city or existing.city,
                country=entity.country or existing.country,
                address=entity.address or existing.address,
                description=entity.description if (entity.description and (not existing.description or len(entity.description) > len(existing.description))) else existing.description,
                confidence=max(entity.confidence, existing.confidence),
                mention_count=entity.mention_count + existing.mention_count,
            )
            seen[key] = merged

    return list(seen.values())


async def extract_entities(
    messages: list[dict],
    captions: list[str],
    focus: str | None = None,
) -> list[ExtractedEntity]:
    """Extract venue/event entities from messages and captions.

    Args:
        messages: List of message dicts with 'sender_name' and 'content' keys.
        captions: List of reel caption strings.
        focus: Optional user focus like "Indonesia trip" to prioritize results.

    Returns:
        List of validated, merged, and sorted ExtractedEntity objects.
    """
    if not messages and not captions:
        return []

    # Choose system prompt based on focus
    if focus:
        system = SYSTEM_PROMPT_WITH_FOCUS.format(focus=focus)
        focus_instruction = f"PRIORITY FOCUS: The user is planning a \"{focus}\". Prioritize places related to this."
    else:
        system = SYSTEM_PROMPT
        focus_instruction = ""

    all_entities: list[ExtractedEntity] = []
    batches = _batch_messages(messages)

    if not batches and captions:
        batches = [[]]

    for batch in batches:
        formatted_messages = _format_messages(batch) if batch else "(no text messages in this batch)"
        formatted_captions = _format_captions(captions)

        prompt = USER_PROMPT_TEMPLATE.format(
            messages=formatted_messages,
            captions=formatted_captions,
            focus_instruction=focus_instruction,
        )

        try:
            response = await call_llm(prompt, system=system)
            parsed = parse_llm_json(response)
        except LLMError as e:
            logger.error("LLM entity extraction failed for batch: %s", e)
            continue

        raw_events = []
        if isinstance(parsed, dict):
            raw_events = parsed.get("events", [])
        elif isinstance(parsed, list):
            raw_events = parsed

        for raw in raw_events:
            entity = _validate_entity(raw)
            if entity is not None:
                all_entities.append(entity)

    # Merge duplicates across batches
    merged = _merge_entities(all_entities)

    # Sort by confidence * mention_count (most recommended first)
    merged.sort(key=lambda e: e.confidence * e.mention_count, reverse=True)

    return merged
