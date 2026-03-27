"""Fetch Instagram reel metadata using Instaloader.

Extracts caption, location tags, hashtags, and owner username
from public reel URLs. Rate-limited to avoid Instagram blocks.
"""

import logging
import re
import time
from dataclasses import dataclass

import instaloader

logger = logging.getLogger(__name__)

RATE_LIMIT_SECONDS = 3.0
SHORTCODE_PATTERN = re.compile(r"instagram\.com/(?:reel|p)/([A-Za-z0-9_-]+)")


@dataclass(frozen=True)
class ReelMetadata:
    shortcode: str
    caption: str | None
    location_name: str | None
    hashtags: list[str]
    owner_username: str | None


class ReelFetchError(Exception):
    pass


def _extract_shortcode(url: str) -> str:
    """Extract the shortcode from an Instagram reel/post URL."""
    match = SHORTCODE_PATTERN.search(url)
    if not match:
        raise ReelFetchError(f"Could not extract shortcode from URL: {url}")
    return match.group(1)


def _extract_hashtags(caption: str) -> list[str]:
    """Extract hashtags from a caption string."""
    return re.findall(r"#(\w+)", caption)


def fetch_reel_metadata(url: str) -> ReelMetadata:
    """Fetch metadata for a single Instagram reel/post.

    Args:
        url: Instagram reel or post URL.

    Returns:
        ReelMetadata with caption, location, hashtags, owner.

    Raises:
        ReelFetchError: If the reel cannot be fetched.
    """
    shortcode = _extract_shortcode(url)

    loader = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
        quiet=True,
    )

    try:
        post = instaloader.Post.from_shortcode(loader.context, shortcode)

        caption = post.caption
        location_name = post.location.name if post.location else None
        hashtags = list(post.caption_hashtags) if post.caption_hashtags else []
        owner_username = post.owner_username

        return ReelMetadata(
            shortcode=shortcode,
            caption=caption,
            location_name=location_name,
            hashtags=hashtags,
            owner_username=owner_username,
        )
    except Exception as e:
        raise ReelFetchError(f"Failed to fetch reel {shortcode}: {e}") from e


def fetch_reels_batch(
    urls: list[str],
    on_progress: callable | None = None,
) -> list[tuple[str, ReelMetadata | None, str | None]]:
    """Fetch metadata for multiple reels with rate limiting.

    Args:
        urls: List of Instagram reel/post URLs.
        on_progress: Optional callback(current, total) for progress updates.

    Returns:
        List of (url, metadata_or_none, error_or_none) tuples.
    """
    results: list[tuple[str, ReelMetadata | None, str | None]] = []

    for i, url in enumerate(urls):
        if on_progress:
            on_progress(i + 1, len(urls))

        try:
            metadata = fetch_reel_metadata(url)
            results.append((url, metadata, None))
        except ReelFetchError as e:
            logger.warning("Failed to fetch reel %s: %s", url, e)
            results.append((url, None, str(e)))

        # Rate limit between requests (skip after last)
        if i < len(urls) - 1:
            time.sleep(RATE_LIMIT_SECONDS)

    return results
