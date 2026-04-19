"""
Markov chain language model for the hybrid recommendation engine.

Trained on the weighted corpus of titles + hashtags from watch history.
Produces candidate next-words given a seed context.
"""

from __future__ import annotations

import random
import re
from collections import defaultdict
from typing import Dict, List, Tuple

from config import FEED_CONFIG


def _tokenize(text: str) -> List[str]:
    """Lowercase, strip punctuation, split into words."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return [w for w in text.split() if len(w) > 1]


class MarkovChain:
    """
    Variable-order Markov chain.
    order=2 means we use bigram (2-word) contexts.

    The chain is weighted: adding a document with weight W
    increments transition counts by W rather than 1.
    This naturally makes recent / liked videos dominate.
    """

    def __init__(self, order: int = FEED_CONFIG.markov_order):
        self.order = order
        # {context_tuple: {next_word: accumulated_weight}}
        self._transitions: Dict[Tuple, Dict[str, float]] = defaultdict(
            lambda: defaultdict(float)
        )
        self._start_tokens: List[str] = []

    def train(self, documents: List[Tuple[str, float]]) -> None:
        """
        documents: list of (text, weight) pairs.
        """
        self._transitions.clear()
        self._start_tokens.clear()

        for text, weight in documents:
            tokens = _tokenize(text)
            if len(tokens) < self.order + 1:
                continue

            # Record starting context tokens (weighted)
            for _ in range(max(1, int(weight * 10))):
                self._start_tokens.append(tokens[0])

            # Build transition table
            for i in range(len(tokens) - self.order):
                context = tuple(tokens[i : i + self.order])
                next_word = tokens[i + self.order]
                self._transitions[context][next_word] += weight

    def generate(self, length: int = FEED_CONFIG.num_output_words) -> List[str]:
        """
        Generate `length` words by random walk through the chain.
        Falls back to shorter contexts if the current context is unseen.
        """
        if not self._transitions:
            return []

        # Pick a starting word weighted by frequency
        if self._start_tokens:
            current = [random.choice(self._start_tokens)]
        else:
            current = [random.choice(list(self._transitions.keys()))[0]]

        result = list(current)

        for _ in range(length - 1):
            # Try longest context first, then back off
            generated = False
            for ctx_len in range(self.order, 0, -1):
                context = tuple(result[-ctx_len:])
                if context in self._transitions:
                    candidates = self._transitions[context]
                    words = list(candidates.keys())
                    weights = list(candidates.values())
                    chosen = random.choices(words, weights=weights, k=1)[0]
                    result.append(chosen)
                    generated = True
                    break

            if not generated:
                # Total fallback: pick any known next word
                all_nexts = [
                    w for nexts in self._transitions.values() for w in nexts
                ]
                if all_nexts:
                    result.append(random.choice(all_nexts))
                else:
                    break

        return result

    def top_transitions(self, top_n: int = 20) -> List[Tuple[str, float]]:
        """
        Return the (word, total_weight) pairs across all transitions,
        sorted by total weight descending.  Used by the hybrid model
        to extract strong signals.
        """
        totals: Dict[str, float] = defaultdict(float)
        for nexts in self._transitions.values():
            for word, weight in nexts.items():
                totals[word] += weight

        return sorted(totals.items(), key=lambda x: x[1], reverse=True)[:top_n]
