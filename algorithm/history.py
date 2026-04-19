"""
Retrieves and weights watch history for the feed algorithm.

Decay model (○ resolved):
  weight = 0.5 ^ (age_in_days / half_life_days)

  half_life = 3 days (from FeedConfig)
  - A video watched 3 days ago has weight 0.5
  - A video watched 1 day ago has weight ~0.79
  - A video watched 7 days ago has weight ~0.22
  - A video watched 14 days ago has weight ~0.05  (near-irrelevant)

This strikes a balance: recent taste dominates but a coherent interest
watched several days ago still influences the feed meaningfully.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import List, Dict, Any

from database.models import WatchEvent
from config import FEED_CONFIG


def _age_days(timestamp: datetime) -> float:
    """Return how many days ago a UTC datetime was."""
    now = datetime.now(timezone.utc)
    # Make timestamp timezone-aware if it isn't (SQLite stores naive UTC)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    delta = now - timestamp
    return max(delta.total_seconds() / 86400.0, 0.0)


def _decay_weight(age_days: float) -> float:
    """
    Exponential decay.  weight = 0.5^(age/half_life)
    Returns a value in (0, 1].
    """
    return math.pow(0.5, age_days / FEED_CONFIG.watch_half_life_days)


def get_weighted_history(session_id: str) -> List[Dict[str, Any]]:
    """
    Return all non-disliked watch events for the session, each annotated
    with a temporal decay weight.

    Returns list of dicts:
        {
            "video_id": str,
            "title": str,
            "hashtags": [str, ...],
            "liked": bool,
            "weight": float,          # decay-adjusted importance
            "completion": float,      # 0-1 completion ratio
        }
    """
    events: List[WatchEvent] = (
        WatchEvent.query
        .filter_by(session_id=session_id)
        .filter(WatchEvent.disliked == False)           # noqa: E712
        .order_by(WatchEvent.timestamp.desc())
        .all()
    )

    results = []
    for ev in events:
        age = _age_days(ev.timestamp)
        base_weight = _decay_weight(age)

        # Boost weight if the user liked the video
        like_multiplier = 1.5 if ev.liked else 1.0

        # Boost weight proportional to how much they watched
        # A video watched to completion is weighted fully;
        # one watched 10% gets 10% of the weight.
        completion_multiplier = max(ev.completion_ratio, 0.1)

        final_weight = base_weight * like_multiplier * completion_multiplier

        results.append({
            "video_id": ev.video_id,
            "title": ev.video_title,
            "hashtags": ev.hashtag_list,
            "liked": ev.liked,
            "weight": final_weight,
            "completion": ev.completion_ratio,
        })

    return results


def get_disliked_signals(session_id: str) -> Dict[str, float]:
    """
    Return a mapping of {word_or_hashtag: penalty_weight} built from
    disliked videos.  These are subtracted from or used to filter
    algorithm outputs.
    """
    events: List[WatchEvent] = (
        WatchEvent.query
        .filter_by(session_id=session_id)
        .filter(WatchEvent.disliked == True)            # noqa: E712
        .all()
    )

    penalties: Dict[str, float] = {}
    for ev in events:
        age = _age_days(ev.timestamp)
        weight = _decay_weight(age) * 2.0   # Dislikes penalise harder

        # Penalise all hashtags from disliked videos
        for tag in ev.hashtag_list:
            tag_lower = tag.lower()
            penalties[tag_lower] = penalties.get(tag_lower, 0.0) + weight

        # Also tokenise the title
        for word in ev.video_title.lower().split():
            word = word.strip("\"'.,!?#@")
            if len(word) > 2:
                penalties[word] = penalties.get(word, 0.0) + weight * 0.5

    return penalties
