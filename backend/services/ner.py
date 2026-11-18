"""Optional Nepali news NER, with the curated Nepal entity lexicon as fallback."""

from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import Any

import config
from services.nepal import extract_entities

logger = logging.getLogger(__name__)
_DEVANAGARI = re.compile(r"[\u0900-\u097f]")


@lru_cache(maxsize=1)
def _nepali_ner() -> Any | None:
    if not config.NEPALI_NER_ENABLED:
        return None
    try:
        from transformers import pipeline

        logger.info("Loading Nepali NER model %s", config.HF_NEPALI_NER_MODEL)
        return pipeline(
            "token-classification",
            model=config.HF_NEPALI_NER_MODEL,
            aggregation_strategy="simple",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Nepali NER model unavailable; using the curated entity lexicon: %s", exc)
        return None


def _chunks(text: str, limit: int = 850) -> list[str]:
    sentences = [part.strip() for part in re.split(r"(?<=[.!?।])\s+|\n+", text or "") if part.strip()]
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) + 1 > limit and current:
            chunks.append(current)
            current = ""
        current = f"{current} {sentence}".strip()
    if current:
        chunks.append(current)
    return chunks


def extract_news_entities(text: str) -> tuple[list[dict[str, Any]], str]:
    """Use Nepali token classification when available and preserve lexicon hits."""
    rows = list(extract_entities(text or ""))
    model = "nepal-entity-lexicon-v2"
    if not _DEVANAGARI.search(text or ""):
        return rows, model
    ner = _nepali_ner()
    if ner is None:
        return rows, model

    labels = {"PER": "person", "PERSON": "person", "ORG": "organization", "LOC": "place", "LOCATION": "place"}
    seen = {str(row.get("name", "")).casefold() for row in rows}
    for chunk in _chunks((text or "")[:10000]):
        try:
            predictions = ner(chunk, truncation=True)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Nepali NER inference failed for one article: %s", exc)
            break
        for item in predictions:
            score = float(item.get("score") or 0.0)
            entity_type = labels.get(str(item.get("entity_group") or item.get("entity") or "").upper())
            value = re.sub(r"\s+", " ", str(item.get("word") or "")).strip()
            key = value.casefold()
            if not entity_type or len(value) < 2 or score < 0.60 or key in seen:
                continue
            seen.add(key)
            rows.append({
                "name": value,
                "type": entity_type,
                "matched_alias": value,
                "confidence": round(score, 3),
                "model": config.HF_NEPALI_NER_MODEL,
            })
    return rows, config.HF_NEPALI_NER_MODEL if len(rows) > len(extract_entities(text or "")) else model
