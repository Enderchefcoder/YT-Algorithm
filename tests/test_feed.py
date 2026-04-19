"""
Tests for the feed building pipeline.
Heavy mocking because we don't want to hit YouTube in unit tests.
"""

import pytest
from unittest.mock import patch, MagicMock


MOCK_HISTORY = [
    {
        "video_id": "abc123",
        "title": "Advanced Python Tutorial",
        "hashtags": ["python", "coding", "tutorial"],
        "liked": True,
        "weight": 0.9,
        "completion": 0.85,
    },
    {
        "video_id": "def456",
        "title": "Python Data Science Guide",
        "hashtags": ["python", "datascience", "pandas"],
        "liked": False,
        "weight": 0.6,
        "completion": 0.60,
    },
]

MOCK_VIDEO = {
    "id": "xyz789",
    "title": "Mock Video",
    "uploader": "Test Channel",
    "duration": 300,
    "view_count": 1000,
    "thumbnail": "https://example.com/thumb.jpg",
    "hashtags": ["python"],
    "hashtags_pipe": "python",
    "description": "A test video",
}


@patch("algorithm.feed.search_videos", return_value=[MOCK_VIDEO])
@patch("algorithm.feed.get_disliked_signals", return_value={})
@patch("algorithm.feed.get_weighted_history", return_value=MOCK_HISTORY)
def test_build_feed_returns_videos(mock_hist, mock_dis, mock_search):
    from algorithm.feed import build_feed
    feed = build_feed("test_session")
    assert isinstance(feed, list)
    assert len(feed) > 0


@patch("algorithm.feed.get_trending", return_value=[MOCK_VIDEO])
@patch("algorithm.feed.get_weighted_history", return_value=[])
def test_empty_history_falls_back_to_trending(mock_hist, mock_trending):
    from algorithm.feed import build_feed
    feed = build_feed("empty_session")
    assert feed == [MOCK_VIDEO]
    mock_trending.assert_called_once()


@patch("algorithm.feed.search_videos", return_value=[MOCK_VIDEO])
@patch("algorithm.feed.get_disliked_signals", return_value={})
@patch("algorithm.feed.get_weighted_history", return_value=MOCK_HISTORY)
def test_batch_search_called_per_keyword(mock_hist, mock_dis, mock_search):
    """search_videos should be called once per keyword batch (◇)."""
    from algorithm.feed import build_feed
    from config import FEED_CONFIG
    build_feed("test_session")
    # Should be called num_output_words times (one batch per keyword)
    assert mock_search.call_count == FEED_CONFIG.num_output_words


@patch("algorithm.feed.search_videos", return_value=[MOCK_VIDEO])
@patch("algorithm.feed.get_disliked_signals",
       return_value={"python": 99.0, "coding": 99.0})
@patch("algorithm.feed.get_weighted_history", return_value=MOCK_HISTORY)
def test_disliked_signals_suppress_words(mock_hist, mock_dis, mock_search):
    """High-penalty disliked words should be filtered from keywords."""
    from algorithm.feed import _hybrid_keywords, _build_corpus
    corpus = _build_corpus(MOCK_HISTORY)
    # With huge penalties on python/coding, they should not be in top results
    from algorithm.feed import get_disliked_signals
    disliked = {"python": 99.0, "coding": 99.0, "tutorial": 99.0}
    keywords = _hybrid_keywords(corpus, disliked, n=8)
    assert "python" not in keywords
