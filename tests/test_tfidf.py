"""Tests for the TF-IDF model."""

import pytest
from algorithm.tfidf import TFIDF


def test_top_words_returns_correct_count():
    tfidf = TFIDF()
    docs = [
        ("python coding tutorial advanced", 1.0),
        ("python beginner guide", 1.0),
        ("cooking recipe pasta easy", 1.0),
    ]
    tfidf.fit(docs)
    result = tfidf.top_words(docs, top_n=3)
    assert len(result) == 3


def test_high_weight_words_score_higher():
    tfidf = TFIDF()
    docs = [
        ("astronomy space telescope nebula", 10.0),  # High weight
        ("cooking baking bread flour", 0.1),         # Low weight
    ]
    tfidf.fit(docs)
    result = tfidf.top_words(docs, top_n=10)
    top_words = [w for w, _ in result]
    # astronomy-related words should dominate
    astro_words = {"astronomy", "space", "telescope", "nebula"}
    assert any(w in astro_words for w in top_words[:4])


def test_stopwords_excluded():
    tfidf = TFIDF()
    docs = [("the a an and or but is it this that", 1.0)]
    tfidf.fit(docs)
    result = tfidf.top_words(docs, top_n=10)
    top_words = {w for w, _ in result}
    stopwords = {"the", "a", "an", "and", "or", "but", "is", "it", "this", "that"}
    assert top_words.isdisjoint(stopwords)


def test_empty_docs_returns_empty():
    tfidf = TFIDF()
    tfidf.fit([])
    result = tfidf.top_words([], top_n=5)
    assert result == []
