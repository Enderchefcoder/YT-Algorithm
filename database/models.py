"""
SQLAlchemy ORM models.
"""

from datetime import datetime
from database.db import db


class WatchEvent(db.Model):
    """
    One row per completed (or significant) watch session.

    Fields map directly to the algorithm spec:
      A  watch_time_seconds   – how long the user actually watched
      B  video_duration_seconds – full length of the video
      C  session_time_minutes  – rolling session time (minutes watched today)
      D  video_title
      E  video_hashtags        – pipe-separated string e.g. "python|coding|tutorial"
      F  liked
      G  disliked
      H  hour_of_day
    """

    __tablename__ = "watch_events"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), nullable=False, index=True)

    video_id = db.Column(db.String(64), nullable=False)
    video_title = db.Column(db.String(512), nullable=False, default="")
    video_hashtags = db.Column(db.String(1024), nullable=False, default="")

    watch_time_seconds = db.Column(db.Float, nullable=False, default=0.0)
    video_duration_seconds = db.Column(db.Float, nullable=False, default=1.0)
    session_time_minutes = db.Column(db.Float, nullable=False, default=0.0)

    liked = db.Column(db.Boolean, default=False)
    disliked = db.Column(db.Boolean, default=False)
    hour_of_day = db.Column(db.Integer, nullable=False, default=0)

    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    @property
    def completion_ratio(self) -> float:
        if self.video_duration_seconds <= 0:
            return 0.0
        return min(self.watch_time_seconds / self.video_duration_seconds, 1.0)

    @property
    def hashtag_list(self) -> list[str]:
        if not self.video_hashtags:
            return []
        return [h.strip() for h in self.video_hashtags.split("|") if h.strip()]

    def __repr__(self) -> str:
        return f"<WatchEvent {self.video_id} ratio={self.completion_ratio:.2f}>"


class ParentSettings(db.Model):
    """Per-session parental control overrides."""

    __tablename__ = "parent_settings"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), nullable=False, unique=True)
    break_override_seconds = db.Column(db.Integer, nullable=True)  # None = use default
    pin_hash = db.Column(db.String(256), nullable=True)  # bcrypt hash of parent PIN

    def __repr__(self) -> str:
        return f"<ParentSettings session={self.session_id}>"


class SessionStats(db.Model):
    """
    Rolling daily stats per session.
    Reset at midnight or when a break resets them.
    """

    __tablename__ = "session_stats"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), nullable=False, unique=True, index=True)

    total_watch_minutes = db.Column(db.Float, default=0.0)
    low_attention_minutes = db.Column(db.Float, default=0.0)
    last_reset = db.Column(db.DateTime, default=datetime.utcnow)

    def reset(self):
        self.total_watch_minutes = 0.0
        self.low_attention_minutes = 0.0
        self.last_reset = datetime.utcnow()
