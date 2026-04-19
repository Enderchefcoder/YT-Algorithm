"""
Guardrail system: attention span tracking and mandatory break enforcement.

All statistics are per-session and reset after each break is served.

Guardrail logic:
  A = watch_time_seconds    (how long the user watched)
  B = video_duration_seconds (full length)
  C = session_time_minutes  (total watch time this session)
  H = hour_of_day

  Attention span % = A / B

  Discard if A < 5 seconds.

  Trigger break if:
    - attention% < 25% AND C > 8 minutes  (lots of short skips = unfocused)
    - C > 20 minutes  (hard cap regardless of attention)

  Break NEVER cuts a video.  It is flagged and served when the current
  video ends (enforced client-side with player.js).

  Break length = f(H), scaled from 3 min (daytime) to 10 min (late night).
  Parents can override to 10 / 30 / 60 min presets.
"""

from __future__ import annotations

from datetime import datetime, timezone, date
from typing import Optional

from database.db import db
from database.models import SessionStats, WatchEvent, ParentSettings
from config import GUARDRAIL_CONFIG


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_or_create_stats(session_id: str) -> SessionStats:
    stats = SessionStats.query.filter_by(session_id=session_id).first()
    if stats is None:
        stats = SessionStats(session_id=session_id)
        db.session.add(stats)
        db.session.commit()
    return stats


def _reset_if_new_day(stats: SessionStats) -> None:
    """Reset daily stats if we've rolled past midnight."""
    last = stats.last_reset
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    today = datetime.now(timezone.utc).date()
    if last.date() < today:
        stats.reset()
        db.session.commit()


def _get_parent_override(session_id: str) -> Optional[int]:
    ps = ParentSettings.query.filter_by(session_id=session_id).first()
    if ps and ps.break_override_seconds:
        return ps.break_override_seconds
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def record_watch(
    session_id: str,
    video_id: str,
    video_title: str,
    video_hashtags: str,
    watch_time_seconds: float,
    video_duration_seconds: float,
    liked: bool = False,
    disliked: bool = False,
) -> dict:
    """
    Record a watch event and update session stats.

    Returns a dict:
        {
            "recorded": bool,          # False if thrown out (< 5 sec)
            "break_needed": bool,      # True if a break should be triggered
            "break_seconds": int,      # How long the break should be
            "reason": str,             # Human-readable reason for break
        }
    """
    # Discard very short watches
    if watch_time_seconds < GUARDRAIL_CONFIG.min_watch_seconds:
        return {"recorded": False, "break_needed": False,
                "break_seconds": 0, "reason": "watch_too_short"}

    hour = datetime.now(timezone.utc).hour

    # Persist the event
    event = WatchEvent(
        session_id=session_id,
        video_id=video_id,
        video_title=video_title,
        video_hashtags=video_hashtags,
        watch_time_seconds=watch_time_seconds,
        video_duration_seconds=max(video_duration_seconds, 1.0),
        liked=liked,
        disliked=disliked,
        hour_of_day=hour,
    )
    db.session.add(event)

    # Update session stats
    stats = _get_or_create_stats(session_id)
    _reset_if_new_day(stats)

    watch_minutes = watch_time_seconds / 60.0
    stats.total_watch_minutes += watch_minutes

    attention_pct = watch_time_seconds / max(video_duration_seconds, 1.0)
    if attention_pct < GUARDRAIL_CONFIG.low_attention_threshold:
        stats.low_attention_minutes += watch_minutes

    db.session.commit()

    # --- Evaluate guardrails ---
    break_needed = False
    reason = ""

    hard_limit = GUARDRAIL_CONFIG.hard_session_limit_minutes
    low_att_limit = GUARDRAIL_CONFIG.low_attention_session_minutes

    if stats.total_watch_minutes > hard_limit:
        break_needed = True
        reason = f"Hard session limit ({hard_limit} min) reached."

    elif (
        attention_pct < GUARDRAIL_CONFIG.low_attention_threshold
        and stats.low_attention_minutes > low_att_limit
    ):
        break_needed = True
        reason = (
            f"Low attention ({attention_pct:.0%} completion) for over "
            f"{low_att_limit} min."
        )

    parent_override = _get_parent_override(session_id)
    break_seconds = GUARDRAIL_CONFIG.break_length_for_hour(hour, parent_override)

    if break_needed:
        # Stats reset AFTER the break is served, not here.
        # We just flag it so the client knows to show the break screen.
        pass

    return {
        "recorded": True,
        "break_needed": break_needed,
        "break_seconds": break_seconds,
        "reason": reason,
    }


def reset_after_break(session_id: str) -> None:
    """
    Called when the user completes their break.
    Resets the session stats so the next session starts fresh.
    """
    stats = _get_or_create_stats(session_id)
    stats.reset()
    db.session.commit()


def get_session_summary(session_id: str) -> dict:
    """Return current stats for a session (used by the parent dashboard)."""
    stats = _get_or_create_stats(session_id)
    _reset_if_new_day(stats)
    return {
        "total_watch_minutes": round(stats.total_watch_minutes, 1),
        "low_attention_minutes": round(stats.low_attention_minutes, 1),
        "last_reset": stats.last_reset.isoformat(),
    }
