"""
Feed generation engine.

Implements the hybrid Markov + TF-IDF recommendation system described
in the spec, with the ◇ batch-per-hashtag feature fully implemented.

Flow:
  1. Load weighted watch history (with decay).
  2. Extract disliked signals (words/hashtags to suppress).
  3. Build corpus: title + hashtags for each watch event, weighted.
  4. Train Markov chain on corpus.
  5. Fit TF-IDF on corpus.
  6. Hybrid output: combine top Markov words + top TF-IDF words → 8 words.
  7. For each of the 8 words, run a separate YouTube search (8 batches).  ◇
  8. De-duplicate, suppress disliked signals, return merged feed.
  9. If history is empty, fall back to trending.
"""

from __future__ import annotations

import random
from typing import List, Dict, Any, Set

from algorithm.history import get_weighted_history, get_disliked_signals
from algorithm.markov import MarkovChain
from algorithm.tfidf import TFIDF
from algorithm.trending import get_trending
from video.search import search_videos
from config import FEED_CONFIG


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_corpus(history: List[Dict[str, Any]]) -> List[tuple[str, float]]:
    """
    Convert weighted history entries into (text, weight) documents
    for the language models.

    Each entry produces one document combining title + hashtags.
    """
    corpus = []
    for entry in history:
        tags_str = " ".join(entry["hashtags"])
        text = f"{entry['title']} {tags_str}"
        corpus.append((text, entry["weight"]))
    return corpus


def _hybrid_keywords(
    corpus: List[tuple[str, float]],
    disliked: Dict[str, float],
    n: int = FEED_CONFIG.num_output_words,
) -> List[str]:
    """
    Run both models, merge their top words, filter disliked signals,
    and return the top `n` keywords.

    Hybrid scoring:
      score(word) = markov_weight * markov_score_norm
                  + tfidf_weight  * tfidf_score_norm

    Both score lists are normalised to [0, 1] before combining so that
    neither model dominates due to scale differences.
    """
    # --- Markov ---
    markov = MarkovChain()
    markov.train(corpus)
    markov_top = markov.top_transitions(top_n=40)  # (word, weight) pairs

    # --- TF-IDF ---
    tfidf = TFIDF()
    tfidf.fit(corpus)
    tfidf_top = tfidf.top_words(corpus, top_n=40)

    # --- Normalise ---
    def _normalise(pairs: List[tuple[str, float]]) -> Dict[str, float]:
        if not pairs:
            return {}
        max_score = max(s for _, s in pairs)
        if max_score == 0:
            return {w: 0.0 for w, _ in pairs}
        return {w: s / max_score for w, s in pairs}

    markov_norm = _normalise(markov_top)
    tfidf_norm = _normalise(tfidf_top)

    # --- Combine ---
    all_words: Set[str] = set(markov_norm.keys()) | set(tfidf_norm.keys())
    hybrid_scores: Dict[str, float] = {}
    for word in all_words:
        m_score = markov_norm.get(word, 0.0) * FEED_CONFIG.markov_weight
        t_score = tfidf_norm.get(word, 0.0) * FEED_CONFIG.tfidf_weight
        hybrid_scores[word] = m_score + t_score

    # --- Filter disliked ---
    # Words that appear in the disliked penalty dict with high penalty
    # are suppressed entirely.  Lower-penalty words just get their score
    # reduced proportionally.
    filtered: Dict[str, float] = {}
    max_penalty = max(disliked.values()) if disliked else 1.0
    for word, score in hybrid_scores.items():
        penalty = disliked.get(word, 0.0)
        penalty_norm = penalty / max_penalty if max_penalty > 0 else 0.0
        adjusted = score * (1.0 - min(penalty_norm, 0.99))
        if adjusted > 0.01:     # Hard floor: completely suppressed words dropped
            filtered[word] = adjusted

    # --- Return top n ---
    ranked = sorted(filtered.items(), key=lambda x: x[1], reverse=True)
    return [word for word, _ in ranked[:n]]


# ---------------------------------------------------------------------------
# Batch search  (◇ feature)
# ---------------------------------------------------------------------------

def _batch_search(keywords: List[str]) -> List[Dict[str, Any]]:
    """
    For each keyword, run an independent YouTube search and collect
    `feed_batch_size` results.

    This means the feed is a mosaic of 8 separate topic searches,
    each anchored by one of the hybrid output words, rather than a
    single blended query.  This produces more topic diversity while
    still being personalised.

    Results are de-duplicated by video_id.
    """
    seen_ids: Set[str] = set()
    all_results: List[Dict[str, Any]] = []

    for keyword in keywords:
        batch = search_videos(keyword, max_results=FEED_CONFIG.feed_batch_size)
        for video in batch:
            vid_id = video.get("id", "")
            if vid_id and vid_id not in seen_ids:
                seen_ids.add(vid_id)
                # Tag the result with the keyword that found it
                video["feed_keyword"] = keyword
                all_results.append(video)

    return all_results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_feed(session_id: str) -> List[Dict[str, Any]]:
    """
    Main entry point.  Returns an ordered list of video dicts ready
    to be rendered in the feed template.
    """
    history = get_weighted_history(session_id)

    # Empty history → trending fallback
    if not history:
        return get_trending(max_results=FEED_CONFIG.trending_fallback_count)

    disliked = get_disliked_signals(session_id)
    corpus = _build_corpus(history)
    keywords = _hybrid_keywords(corpus, disliked, n=FEED_CONFIG.num_output_words)

    if not keywords:
        return get_trending(max_results=FEED_CONFIG.trending_fallback_count)

    feed = _batch_search(keywords)

    # Light shuffle within each keyword group to avoid the feed feeling
    # like 8 rigid blocks.  We shuffle in groups of feed_batch_size.
    batch_size = FEED_CONFIG.feed_batch_size
    groups = [feed[i : i + batch_size] for i in range(0, len(feed), batch_size)]
    for group in groups:
        random.shuffle(group)
    feed = [v for group in groups for v in group]

    return feed
