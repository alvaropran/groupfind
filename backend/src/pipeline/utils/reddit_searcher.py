"""Search Reddit for venue/event verification using PRAW + PullPush.

Two-tier search strategy:
1. PRAW (official Reddit API) — subreddit search for posts
2. PullPush API — historical comment search (Reddit's API can't search comments)
"""

import logging
from dataclasses import dataclass

import httpx
import praw

from src.config import settings

logger = logging.getLogger(__name__)

PULLPUSH_BASE_URL = "https://api.pullpush.io/reddit/search"


@dataclass(frozen=True)
class RedditResult:
    subreddit: str
    post_title: str
    post_url: str
    post_score: int
    comment_snippet: str | None
    search_source: str  # "praw" or "pullpush"


# City -> subreddit mappings (top US cities)
CITY_SUBREDDITS: dict[str, list[str]] = {
    "new york": ["nyc", "AskNYC", "FoodNYC", "newyorkcity"],
    "los angeles": ["LosAngeles", "AskLosAngeles", "FoodLosAngeles"],
    "chicago": ["chicago", "chicagofood"],
    "houston": ["houston"],
    "phoenix": ["phoenix"],
    "philadelphia": ["philadelphia"],
    "san antonio": ["sanantonio"],
    "san diego": ["sandiego", "FoodSanDiego"],
    "dallas": ["Dallas"],
    "austin": ["Austin", "austinfood"],
    "san francisco": ["sanfrancisco", "AskSF"],
    "seattle": ["Seattle", "seattlefood"],
    "denver": ["Denver"],
    "boston": ["boston", "BostonFood"],
    "nashville": ["nashville"],
    "portland": ["Portland"],
    "miami": ["Miami"],
    "atlanta": ["Atlanta"],
    "las vegas": ["vegas", "LasVegas"],
    "detroit": ["Detroit"],
    "minneapolis": ["Minneapolis"],
    "washington": ["washingtondc"],
    "new orleans": ["NewOrleans"],
    "tampa": ["tampa"],
    "orlando": ["orlando"],
    "pittsburgh": ["pittsburgh"],
    "charlotte": ["Charlotte"],
    "raleigh": ["raleigh"],
    "salt lake city": ["SaltLakeCity"],
    "honolulu": ["Hawaii"],
}

# General food/travel subreddits as fallback
FALLBACK_SUBREDDITS = ["food", "travel", "foodporn"]


def _get_subreddits_for_city(city: str | None) -> list[str]:
    """Get relevant subreddits for a city."""
    if not city:
        return FALLBACK_SUBREDDITS

    city_lower = city.lower().strip()
    for key, subs in CITY_SUBREDDITS.items():
        if key in city_lower or city_lower in key:
            return subs

    return FALLBACK_SUBREDDITS


def search_with_praw(
    venue_name: str,
    subreddits: list[str],
    limit: int = 5,
) -> list[RedditResult]:
    """Search Reddit posts via PRAW (official API).

    Requires PRAW credentials to be configured. Returns empty list if
    credentials are missing.
    """
    reddit_client_id = settings.reddit_client_id if hasattr(settings, 'reddit_client_id') else ""
    reddit_client_secret = settings.reddit_client_secret if hasattr(settings, 'reddit_client_secret') else ""

    if not reddit_client_id or not reddit_client_secret:
        logger.debug("PRAW credentials not configured, skipping")
        return []

    try:
        reddit = praw.Reddit(
            client_id=reddit_client_id,
            client_secret=reddit_client_secret,
            user_agent="GroupFind/0.1.0",
        )

        results: list[RedditResult] = []
        for sub_name in subreddits[:3]:  # Limit to 3 subreddits
            try:
                subreddit = reddit.subreddit(sub_name)
                for post in subreddit.search(venue_name, limit=limit, sort="relevance"):
                    results.append(
                        RedditResult(
                            subreddit=sub_name,
                            post_title=post.title,
                            post_url=f"https://reddit.com{post.permalink}",
                            post_score=post.score,
                            comment_snippet=post.selftext[:500] if post.selftext else None,
                            search_source="praw",
                        )
                    )
            except Exception as e:
                logger.warning("PRAW search failed for r/%s: %s", sub_name, e)
                continue

        return results

    except Exception as e:
        logger.warning("PRAW initialization failed: %s", e)
        return []


async def search_with_pullpush(
    venue_name: str,
    subreddits: list[str],
    limit: int = 5,
) -> list[RedditResult]:
    """Search Reddit comments via PullPush API (Pushshift successor).

    PullPush can search comments, which is where most restaurant
    opinions live. Reddit's official API cannot search comments.
    """
    results: list[RedditResult] = []
    sub_list = ",".join(subreddits[:3])

    async with httpx.AsyncClient(timeout=15.0) as client:
        # Search comments
        try:
            comment_response = await client.get(
                f"{PULLPUSH_BASE_URL}/comment",
                params={
                    "q": venue_name,
                    "subreddit": sub_list,
                    "size": limit,
                    "sort": "desc",
                    "sort_type": "score",
                },
            )
            comment_response.raise_for_status()
            comments = comment_response.json().get("data", [])

            for comment in comments:
                results.append(
                    RedditResult(
                        subreddit=comment.get("subreddit", "unknown"),
                        post_title=f"Comment in r/{comment.get('subreddit', 'unknown')}",
                        post_url=f"https://reddit.com/comments/{comment.get('link_id', '')[3:]}/comment/{comment.get('id', '')}",
                        post_score=comment.get("score", 0),
                        comment_snippet=comment.get("body", "")[:500],
                        search_source="pullpush",
                    )
                )
        except Exception as e:
            logger.warning("PullPush comment search failed: %s", e)

        # Search submissions
        try:
            post_response = await client.get(
                f"{PULLPUSH_BASE_URL}/submission",
                params={
                    "q": venue_name,
                    "subreddit": sub_list,
                    "size": limit,
                    "sort": "desc",
                    "sort_type": "score",
                },
            )
            post_response.raise_for_status()
            posts = post_response.json().get("data", [])

            for post in posts:
                results.append(
                    RedditResult(
                        subreddit=post.get("subreddit", "unknown"),
                        post_title=post.get("title", "Untitled"),
                        post_url=f"https://reddit.com{post.get('permalink', '')}",
                        post_score=post.get("score", 0),
                        comment_snippet=post.get("selftext", "")[:500] or None,
                        search_source="pullpush",
                    )
                )
        except Exception as e:
            logger.warning("PullPush submission search failed: %s", e)

    return results


async def search_reddit(
    venue_name: str,
    city: str | None = None,
    limit: int = 5,
) -> list[RedditResult]:
    """Search Reddit for a venue using all available strategies.

    Tries PRAW first, then PullPush as fallback. Returns combined
    and deduplicated results sorted by score.
    """
    subreddits = _get_subreddits_for_city(city)

    # Tier 1: PRAW (synchronous)
    results = search_with_praw(venue_name, subreddits, limit=limit)

    # Tier 2: PullPush (async, catches what PRAW misses — especially comments)
    pullpush_results = await search_with_pullpush(venue_name, subreddits, limit=limit)
    results.extend(pullpush_results)

    # Deduplicate by URL
    seen_urls: set[str] = set()
    unique_results: list[RedditResult] = []
    for result in results:
        if result.post_url not in seen_urls:
            seen_urls.add(result.post_url)
            unique_results.append(result)

    # Sort by score descending
    return sorted(unique_results, key=lambda r: r.post_score, reverse=True)[:limit]
