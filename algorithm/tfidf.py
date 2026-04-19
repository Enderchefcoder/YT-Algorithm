"""
TF-IDF model for the hybrid recommendation engine.

The "documents" are weighted watch-history entries.
TF-IDF extracts the words that are most characteristic of
this user's taste (high TF) while penalising extremely common
words across the whole corpus (high IDF = rare globally = distinctive).
"""

from __future__ import annotations

import math
import re
from collections import defaultdict, Counter
from typing import Dict, List, Tuple


# A small English stopword list.  We intentionally keep it tight so that
# meaningful short words (e.g. "art", "war", "how") are not removed.
STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
    "for", "of", "with", "is", "it", "this", "that", "was", "are",
    "be", "as", "by", "from", "have", "has", "had", "not", "they",
    "he", "she", "we", "you", "i", "my", "your", "his", "her", "its",
    "do", "did", "will", "would", "could", "should", "may", "might",
    "can", "been", "being", "their", "our", "all", "more", "so", "if",
    "than", "then", "there", "when", "where", "which", "who", "what",
    "how", "just", "up", "out", "about", "into", "through", "also",
    "very", "much", "many", "some", "any", "one", "two", "new", "get",
    "no", "yes", "hi", "me",
}


def _tokenize(text: str) -> List[str]:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return [w for w in text.split() if len(w) > 2 and w not in STOPWORDS]


class TFIDF:
    """
    Lightweight TF-IDF without scikit-learn, so we can do weighted
    document frequencies natively.

    Each 'document' is a (text, weight) pair.
    """

    def __init__(self):
        self._idf: Dict[str, float] = {}
        self._corpus_size: int = 0

    def fit(self, documents: List[Tuple[str, float]]) -> None:
        """
        Compute IDF from the corpus.
        document_frequency is accumulated by weight so that heavily-weighted
        documents (recent / liked) push their words' IDF down (more common
        in *this* user's corpus) meaning TF-IDF will score them higher.
        """
        df: Dict[str, float] = defaultdict(float)
        total_weight = 0.0

        for text, weight in documents:
            tokens = set(_tokenize(text))
            for token in tokens:
                df[token] += weight
            total_weight += weight

        self._corpus_size = max(total_weight, 1.0)
        self._idf = {
            word: math.log((self._corpus_size + 1.0) / (freq + 1.0)) + 1.0
            for word, freq in df.items()
        }

    def score_document(self, text: str, weight: float = 1.0) -> Dict[str, float]:
        """
        Return {word: tfidf_score} for a single document.
        The weight scales TF so heavier documents score higher.
        """
        tokens = _tokenize(text)
        if not tokens:
            return {}

        tf_raw = Counter(tokens)
        max_freq = max(tf_raw.values())

        scores = {}
        for word, freq in tf_raw.items():
            tf = (freq / max_freq) * weight
            idf = self._idf.get(word, 1.0)
            scores[word] = tf * idf

        return scores

    def top_words(
        self,
        documents: List[Tuple[str, float]],
        top_n: int = 4,
    ) -> List[Tuple[str, float]]:
        """
        Given a list of (text, weight) pairs, compute the aggregate
        TF-IDF across all documents and return the top_n words.
        """
        aggregate: Dict[str, float] = defaultdict(float)
        for text, weight in documents:
            scores = self.score_document(text, weight)
            for word, score in scores.items():
                aggregate[word] += score

        return sorted(aggregate.items(), key=lambda x: x[1], reverse=True)[:top_n]
