"""Uniform scoring interface for every citation method under comparison.

Every scorer maps (sentences, documents, ctx) -> score matrix of shape
(n_sentences, n_documents).  Assignment and calibration are shared, so no method
gets a hand-tuned advantage.  This is the fix for the fairness problem recorded
in rebuttal_plan.md: the released citation.py runs the proposed method at
softmax(/0.05) + threshold 0.2 and the full-token baseline at softmax(/0.7) +
threshold 0, which is not a like-for-like comparison.

Experiment IDs refer to the table in rebuttal_plan.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer

_PS = PorterStemmer()
_STOP = set(stopwords.words("english"))


@dataclass
class Context:
    """Everything a scorer may need beyond the raw text."""

    query: str | None = None
    # Keywords produced by the BERT/BioBERT extractor, already stemmed.
    keyword_sentences: list[set[str]] | None = None
    keyword_documents: list[set[str]] | None = None
    # r(q, d) from the retriever, needed by CiteFix KSC (E3).
    retrieval_scores: np.ndarray | None = None
    extras: dict = field(default_factory=dict)


# --------------------------------------------------------------------------
# tokenisation


def content_tokens(text: str) -> set[str]:
    """Stopword-filtered, stemmed tokens.

    Deliberately replicates citation.py:88 (`split(' ')`, no punctuation
    stripping) so that E1 reproduces the existing `jaccard_output` column
    rather than a cleaner variant of it.
    """
    return {_PS.stem(t) for t in text.lower().split(" ") if t not in _STOP}


def raw_tokens(text: str) -> list[str]:
    """Plain lowercase whitespace tokens, no stemming, no stopword removal.

    CiteFix §3.1 defines its score over "the tokens in x_i" with no further
    processing, so E2/E3 stay faithful to that.
    """
    return text.lower().split()


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


# --------------------------------------------------------------------------
# scorers


def keyword_jaccard(sentences, documents, ctx: Context) -> np.ndarray:
    """Proposed method: Jaccard over extracted keywords."""
    if ctx.keyword_sentences is None or ctx.keyword_documents is None:
        raise ValueError("keyword_jaccard needs precomputed keywords in ctx")
    ks, kd = ctx.keyword_sentences, ctx.keyword_documents
    return np.array([[jaccard(s, d) for d in kd] for s in ks], dtype=float)


def full_token_jaccard(sentences, documents, ctx: Context) -> np.ndarray:
    """E1 - the control for Point 2. Same scoring, no keyword extraction."""
    ts = [content_tokens(s) for s in sentences]
    td = [content_tokens(d) for d in documents]
    return np.array([[jaccard(s, d) for d in td] for s in ts], dtype=float)


def citefix_intersection(sentences, documents, ctx: Context) -> np.ndarray:
    """E2 - CiteFix §3.1: size of the token intersection, no normalisation."""
    ts = [set(raw_tokens(s)) for s in sentences]
    td = [set(raw_tokens(d)) for d in documents]
    return np.array([[float(len(s & d)) for d in td] for s in ts], dtype=float)


def citefix_ksc(sentences, documents, ctx: Context, lam: float = 0.8) -> np.ndarray:
    """E3 - CiteFix §3.2: lam * keyword score + (1 - lam) * retrieval score.

    The two terms live on different scales, so each is min-max normalised per
    sentence before blending; CiteFix does not specify a normalisation.
    """
    base = _minmax_rows(citefix_intersection(sentences, documents, ctx))
    if ctx.retrieval_scores is None:
        # No retriever scores available: fall back to rank-implied scores, with
        # documents assumed to arrive in retrieval order.
        n = len(documents)
        r = np.linspace(1.0, 0.0, n) if n > 1 else np.ones(1)
    else:
        r = _minmax(np.asarray(ctx.retrieval_scores, dtype=float))
    return lam * base + (1.0 - lam) * r[None, :]


def tfidf_cosine(sentences, documents, ctx: Context) -> np.ndarray:
    """E7 - TF-IDF cosine, matching processing_time.ipynb's implementation."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    vec = TfidfVectorizer()
    matrix = vec.fit_transform(list(sentences) + list(documents))
    n = len(sentences)
    return cosine_similarity(matrix[:n], matrix[n:]).astype(float)


def bm25(sentences, documents, ctx: Context) -> np.ndarray:
    """E8 - BM25 with each sentence as the query over the retrieved set."""
    from rank_bm25 import BM25Okapi

    index = BM25Okapi([raw_tokens(d) for d in documents])
    return np.array([index.get_scores(raw_tokens(s)) for s in sentences], dtype=float)


SCORERS = {
    "keyword_jaccard": keyword_jaccard,   # proposed
    "full_token_jaccard": full_token_jaccard,  # E1
    "citefix_intersection": citefix_intersection,  # E2
    "citefix_ksc": citefix_ksc,  # E3
    "tfidf": tfidf_cosine,  # E7
    "bm25": bm25,  # E8
}


# --------------------------------------------------------------------------
# shared calibration and assignment


def _minmax(v: np.ndarray) -> np.ndarray:
    lo, hi = float(v.min()), float(v.max())
    return np.zeros_like(v) if hi - lo < 1e-12 else (v - lo) / (hi - lo)


def _minmax_rows(m: np.ndarray) -> np.ndarray:
    lo = m.min(axis=1, keepdims=True)
    hi = m.max(axis=1, keepdims=True)
    span = np.where(hi - lo < 1e-12, 1.0, hi - lo)
    return np.where(hi - lo < 1e-12, 0.0, (m - lo) / span)


def softmax(m: np.ndarray, temperature: float) -> np.ndarray:
    z = m / temperature
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def assign(m: np.ndarray, threshold: float = 0.0) -> np.ndarray:
    """Argmax citation per sentence; -1 means "cite nothing"."""
    if m.size == 0:
        return np.zeros(0, dtype=int)
    best = m.argmax(axis=1)
    top = m[np.arange(m.shape[0]), best]
    return np.where(top > threshold, best, -1)


def score_and_assign(name, sentences, documents, ctx, temperature, threshold):
    """One call path for every method, so comparisons stay like-for-like."""
    raw = SCORERS[name](sentences, documents, ctx)
    return assign(softmax(raw, temperature), threshold), raw
