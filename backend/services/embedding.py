"""Multilingual embeddings with graceful TF-IDF fallback for local runs."""

from __future__ import annotations

import hashlib
import json
import logging
import math
import re
from functools import lru_cache
from typing import Any

import numpy as np

from config import EMBEDDING_ENABLED, HF_EMBEDDING_MODEL

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[\w\u0900-\u097f]+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    return [t.casefold() for t in _TOKEN_RE.findall(text or "") if len(t) > 1]


@lru_cache(maxsize=1)
def _st_model() -> Any | None:
    if not EMBEDDING_ENABLED:
        return None
    try:
        from sentence_transformers import SentenceTransformer

        logger.info("Loading embedding model %s", HF_EMBEDDING_MODEL)
        return SentenceTransformer(HF_EMBEDDING_MODEL)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Embedding model unavailable (%s); using hash TF fallback", exc)
        return None


def model_id() -> str:
    if _st_model() is not None:
        return HF_EMBEDDING_MODEL
    return "local-hash-tfidf-fallback-v1"


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    model = _st_model()
    if model is not None:
        vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return [v.astype(float).tolist() for v in np.asarray(vectors)]
    return [_hash_tf_vector(t) for t in texts]


def embed_text(text: str) -> list[float]:
    return embed_texts([text or ""])[0]


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    va = np.asarray(a, dtype=float)
    vb = np.asarray(b, dtype=float)
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


def vector_to_storage(vector: list[float]) -> str:
    return json.dumps(vector)


def storage_to_vector(raw: str | None) -> list[float] | None:
    if not raw:
        return None
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [float(x) for x in data]
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    return None


def _hash_tf_vector(text: str, dim: int = 384) -> list[float]:
    """Deterministic bag-of-hashed-ngrams fallback (not a Nepal-trained model)."""
    vec = np.zeros(dim, dtype=float)
    tokens = _tokenize(text)
    if not tokens:
        return vec.tolist()
    for token in tokens:
        digest = hashlib.md5(token.encode("utf-8")).hexdigest()
        idx = int(digest[:8], 16) % dim
        sign = 1.0 if int(digest[8:10], 16) % 2 == 0 else -1.0
        vec[idx] += sign
    # character bigrams for Devanagari robustness
    compact = "".join(tokens)
    for i in range(len(compact) - 1):
        gram = compact[i : i + 2]
        digest = hashlib.sha1(gram.encode("utf-8")).hexdigest()
        idx = int(digest[:8], 16) % dim
        vec[idx] += 0.5
    norm = math.sqrt(float(np.dot(vec, vec)))
    if norm:
        vec /= norm
    return vec.tolist()
