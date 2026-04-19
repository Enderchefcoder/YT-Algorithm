"""
Trending video fetcher.
Used as the cold-start fallback when a session has no watch history.
"""

from __future__ import annotations

from typing import List, Dict, Any

from video.search import search_videos


# Broad trending search terms we rotate through for variety.
# These are intentionally generic and safe.
_TRENDING_QUERIES = [
    "trending today",
    "popular videos",
    "most watched",
    "viral video",
    "best of the week",
]


def get_trending(max_results: int = 20) -> List[Dict[str, Any]]:
    """
    Pull a mix of results from several broad trending queries.
    De-duplicate and return up to max_results.
    """
    import random
    queries = random.sample(_TRENDING_QUERIES, k=min(3, len(_TRENDING_QUERIES)))

    seen: set = set()
    results: List[Dict[str, Any]] = []

    per_query = max(1, max_results // len(queries))

    for query in queries:
        batch = search_videos(query, max_results=per_query)
        for v in batch:
            vid_id = v.get("id", "")
            if vid_id and vid_id not in seen:
                seen.add(vid_id)
                results.append(v)
            if len(results) >= max_results:
                break

    return results[:max_results]
