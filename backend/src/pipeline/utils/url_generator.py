"""Generate Google Maps and Google Calendar URLs for discovered events.

All URLs are free and require no API keys.
"""

from urllib.parse import quote


def generate_maps_url(name: str, address: str | None = None) -> str:
    """Generate a Google Maps search URL for a venue.

    Args:
        name: Venue name (e.g., "Tatiana Restaurant").
        address: Optional address to improve accuracy.

    Returns:
        Google Maps search URL.
    """
    query = name
    if address:
        query = f"{name}, {address}"
    return f"https://www.google.com/maps/search/?api=1&query={quote(query)}"


def generate_calendar_url(
    name: str,
    location: str | None = None,
    description: str | None = None,
) -> str:
    """Generate a Google Calendar event creation URL.

    Opens Google Calendar with a pre-filled event. No API key needed.

    Args:
        name: Event/venue name.
        location: Optional location string.
        description: Optional event description.

    Returns:
        Google Calendar URL that opens the "create event" form.
    """
    params = [f"text={quote(name)}"]

    if location:
        params.append(f"location={quote(location)}")

    if description:
        params.append(f"details={quote(description)}")

    return f"https://calendar.google.com/calendar/render?action=TEMPLATE&{'&'.join(params)}"
