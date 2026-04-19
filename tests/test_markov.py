"""Tests for the Markov chain."""

import pytest
from algorithm.markov import MarkovChain


def test_train_and_generate_returns_words():
    mc = MarkovChain(order=2)
    corpus = [
        ("python tutorial for beginners", 1.0),
        ("python coding tips and tricks", 1.0),
        ("coding tutorial advanced python", 0.5),
    ]
    mc.train(corpus)
    result = mc.generate(length=8)
    assert isinstance(result, list)
    assert len(result) > 0
    assert all(isinstance(w, str) for w in result)


def test_empty_corpus_returns_empty():
    mc = MarkovChain()
    mc.train([])
    assert mc.generate() == []


def test_higher_weight_words_appear_more():
    """Words in higher-weighted documents should appear more often in top_transitions."""
    mc = MarkovChain(order=1)
    mc.train([
        ("cat cat cat", 10.0),   # Very high weight
        ("dog dog dog", 0.1),    # Very low weight
    ])
    top = mc.top_transitions(top_n=5)
    top_words = [w for w, _ in top]
    assert "cat" in top_words
    # cat should rank above dog
    if "dog" in top_words:
        cat_rank = top_words.index("cat")
        dog_rank = top_words.index("dog")
        assert cat_rank < dog_rank


def test_short_document_handled_gracefully():
    mc = MarkovChain(order=2)
    mc.train([("one", 1.0)])  # Too short for bigram
    result = mc.generate(length=5)
    assert isinstance(result, list)
