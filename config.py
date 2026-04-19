"""
Central configuration for YT-Safe.
All tuneable constants live here so nothing is magic-numbered
across the codebase.
"""

import os
from dataclasses import dataclass, field
from typing import List


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'ytsafe.db')}"
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")

# ---------------------------------------------------------------------------
# Guardrail settings
# ---------------------------------------------------------------------------

@dataclass
class GuardrailConfig:
    # Attention span guardrail
    min_watch_seconds: int = 5          # Shorter watches are discarded
    low_attention_threshold: float = 0.25   # <25 % completion = low attention
    low_attention_session_minutes: int = 8  # Trigger break after 8 min of low-attention
    hard_session_limit_minutes: int = 20    # Always break after 20 min regardless

    # Break length (seconds)
    break_base_seconds: int = 180       # 3 minutes base
    break_max_seconds: int = 600        # 10 minutes maximum
    # Hour at which break scaling begins ramping up (24h)
    evening_start_hour: int = 18        # 6 PM
    night_end_hour: int = 23            # 11 PM

    # Parent overrides (seconds)
    parent_break_presets: List[int] = field(
        default_factory=lambda: [600, 1800, 3600]  # 10 min, 30 min, 60 min
    )

    def break_length_for_hour(self, hour: int, parent_override: int | None = None) -> int:
        """
        Scales break length based on time of day.
        Before evening_start_hour  -> base
        Between evening and night  -> linear scale base → max
        After night_end_hour       -> max
        Parent override replaces everything if set.
        """
        if parent_override is not None:
            return parent_override

        if hour < self.evening_start_hour:
            return self.break_base_seconds

        if hour >= self.night_end_hour:
            return self.break_max_seconds

        # Linear interpolation between evening_start and night_end
        span = self.night_end_hour - self.evening_start_hour
        progress = (hour - self.evening_start_hour) / span
        scaled = self.break_base_seconds + progress * (
            self.break_max_seconds - self.break_base_seconds
        )
        return int(scaled)


# ---------------------------------------------------------------------------
# Feed / algorithm settings
# ---------------------------------------------------------------------------

@dataclass
class FeedConfig:
    feed_batch_size: int = 8        # Results per hashtag batch
    num_output_words: int = 8       # Words the hybrid model outputs
    num_batches: int = 8            # One batch per output word/hashtag
    trending_fallback_count: int = 20   # Videos to fetch when history is empty

    # Decay settings  (○ resolved here)
    # Half-life in days: a watch N days ago has weight 0.5^(N/half_life)
    # 3 days feels right — last night still matters, last week matters less,
    # two weeks ago is mostly noise.
    watch_half_life_days: float = 3.0

    # Markov chain
    markov_order: int = 2           # Bigram context

    # TF-IDF
    tfidf_max_features: int = 500
    tfidf_top_n: int = 4            # Words from TF-IDF side of hybrid

    # Hybrid split: markov_weight + tfidf_weight should sum to 1.0
    markov_weight: float = 0.5
    tfidf_weight: float = 0.5


GUARDRAIL_CONFIG = GuardrailConfig()
FEED_CONFIG = FeedConfig()
