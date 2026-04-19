"""
Tests for the guardrail system.
Runs without a database by mocking the ORM calls.
"""

import pytest
from unittest.mock import MagicMock, patch
from config import GuardrailConfig


@pytest.fixture
def cfg():
    return GuardrailConfig()


class TestBreakLengthForHour:
    """Break length should scale smoothly with hour of day."""

    def test_daytime_returns_base(self, cfg):
        assert cfg.break_length_for_hour(10) == cfg.break_base_seconds

    def test_midnight_returns_max(self, cfg):
        assert cfg.break_length_for_hour(23) == cfg.break_max_seconds

    def test_evening_is_between(self, cfg):
        length = cfg.break_length_for_hour(20)
        assert cfg.break_base_seconds < length < cfg.break_max_seconds

    def test_parent_override_takes_priority(self, cfg):
        override = 1800
        assert cfg.break_length_for_hour(10, parent_override=override) == override
        assert cfg.break_length_for_hour(23, parent_override=override) == override

    def test_scaling_is_monotonic(self, cfg):
        """Later hours should never have shorter breaks than earlier ones."""
        lengths = [cfg.break_length_for_hour(h)
                   for h in range(cfg.evening_start_hour, cfg.night_end_hour + 1)]
        for i in range(len(lengths) - 1):
            assert lengths[i] <= lengths[i + 1]


class TestRecordWatch:
    """record_watch should correctly classify events and set break flags."""

    def _make_stats(self, total_min=0.0, low_att_min=0.0):
        stats = MagicMock()
        stats.total_watch_minutes   = total_min
        stats.low_attention_minutes = low_att_min
        stats.last_reset = __import__("datetime").datetime(2024, 1, 1)
        return stats

    @patch("algorithm.guardrails._get_or_create_stats")
    @patch("algorithm.guardrails._reset_if_new_day")
    @patch("algorithm.guardrails._get_parent_override", return_value=None)
    @patch("algorithm.guardrails.db")
    def test_short_watch_is_discarded(self, mock_db, mock_po, mock_reset, mock_stats):
        from algorithm.guardrails import record_watch
        result = record_watch(
            "sess1", "vidA", "Title", "tag1",
            watch_time_seconds=3,       # < 5 sec
            video_duration_seconds=120,
        )
        assert result["recorded"] is False
        assert result["break_needed"] is False

    @patch("algorithm.guardrails._get_or_create_stats")
    @patch("algorithm.guardrails._reset_if_new_day")
    @patch("algorithm.guardrails._get_parent_override", return_value=None)
    @patch("algorithm.guardrails.db")
    def test_hard_limit_triggers_break(self, mock_db, mock_po, mock_reset, mock_stats_fn):
        from algorithm.guardrails import record_watch
        stats = self._make_stats(total_min=21.0)  # Already over 20 min
        mock_stats_fn.return_value = stats

        result = record_watch(
            "sess1", "vidA", "Title", "tag1",
            watch_time_seconds=60,
            video_duration_seconds=120,
        )
        assert result["recorded"] is True
        assert result["break_needed"] is True

    @patch("algorithm.guardrails._get_or_create_stats")
    @patch("algorithm.guardrails._reset_if_new_day")
    @patch("algorithm.guardrails._get_parent_override", return_value=None)
    @patch("algorithm.guardrails.db")
    def test_low_attention_triggers_break(self, mock_db, mock_po, mock_reset, mock_stats_fn):
        from algorithm.guardrails import record_watch
        # 9 minutes of low-attention already accumulated
        stats = self._make_stats(total_min=10.0, low_att_min=9.0)
        mock_stats_fn.return_value = stats

        # Watch 20% of a video (below 25% threshold)
        result = record_watch(
            "sess1", "vidB", "Title", "tag1",
            watch_time_seconds=24,      # 20% of 120s
            video_duration_seconds=120,
        )
        assert result["recorded"] is True
        assert result["break_needed"] is True

    @patch("algorithm.guardrails._get_or_create_stats")
    @patch("algorithm.guardrails._reset_if_new_day")
    @patch("algorithm.guardrails._get_parent_override", return_value=None)
    @patch("algorithm.guardrails.db")
    def test_normal_watch_no_break(self, mock_db, mock_po, mock_reset, mock_stats_fn):
        from algorithm.guardrails import record_watch
        stats = self._make_stats(total_min=5.0, low_att_min=0.0)
        mock_stats_fn.return_value = stats

        result = record_watch(
            "sess1", "vidC", "Title", "tag1",
            watch_time_seconds=90,      # 75% of 120s — good attention
            video_duration_seconds=120,
        )
        assert result["recorded"] is True
        assert result["break_needed"] is False
