"""Claim extraction and cross-outlet verification assistance."""

from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy.orm import Session

from database import Article, Claim
from services.embedding import cosine, embed_text

CLAIM_CUES = re.compile(
    r"(?i)\b("
    r"said|claimed|announced|alleged|reported|confirmed|denied|"
    r"according to|stated|accused|revealed|"
    r"भने|दाबी|घोषणा|पुष्टि|खण्डन|आरोप|अनुसार"
    r")\b"
)

NUMBER_FACT = re.compile(
    r"(?i)(\b\d[\d,]*(?:\.\d+)?\s*(?:percent|%|million|billion|जना|प्रतिशत|करोड|लाख)\b)"
)


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[।.!?])\s+", text or "")
    return [p.strip() for p in parts if len(p.strip()) > 25]


def extract_claims_from_text(text: str, limit: int = 5) -> list[str]:
    sentences = _split_sentences(text)
    claims: list[str] = []
    for sentence in sentences:
        if CLAIM_CUES.search(sentence) or NUMBER_FACT.search(sentence):
            claims.append(sentence[:500])
        if len(claims) >= limit:
            break
    if not claims and sentences:
        claims.append(sentences[0][:500])
    return claims


def _status_from_similarity(best: float, second: float | None, contradict_hint: bool) -> tuple[str, float]:
    if contradict_hint and best >= 0.55:
        return "disputed", round(min(0.75, best), 4)
    if best >= 0.78:
        return "supported", round(best, 4)
    if best >= 0.62 and second is not None and second >= 0.58:
        return "supported", round((best + second) / 2, 4)
    if contradict_hint:
        return "contradicted", round(max(0.4, best), 4)
    return "unverified", round(best if best else 0.2, 4)


NEGATION = re.compile(r"(?i)\b(not|no|never|false|deny|denied|खण्डन|होइन|छैन|नभएको)\b")


def verify_claim_against_articles(claim_text: str, peers: list[Article]) -> dict[str, Any]:
    claim_vec = embed_text(claim_text)
    scored: list[dict[str, Any]] = []
    for peer in peers:
        peer_text = f"{peer.original_headline}. {(peer.content_text or '')[:1200]}"
        sim = cosine(claim_vec, embed_text(peer_text))
        contradict = bool(NEGATION.search(peer_text)) and sim >= 0.5
        scored.append({
            "article_id": peer.id,
            "source": peer.source.name if peer.source else None,
            "url": peer.url,
            "headline": peer.original_headline,
            "similarity": round(sim, 4),
            "contradiction_cue": contradict,
        })
    scored.sort(key=lambda x: x["similarity"], reverse=True)
    best = scored[0]["similarity"] if scored else 0.0
    second = scored[1]["similarity"] if len(scored) > 1 else None
    contradict_hint = any(s["contradiction_cue"] and s["similarity"] >= 0.5 for s in scored[:3])
    # If top peer strongly similar but another peer has negation + moderate sim → disputed
    if scored and scored[0]["similarity"] >= 0.7 and contradict_hint:
        status, conf = "disputed", round(scored[0]["similarity"], 4)
    else:
        status, conf = _status_from_similarity(best, second, contradict_hint)

    citations = [
        {
            "article_id": s["article_id"],
            "url": s["url"],
            "headline": s["headline"],
            "source": s["source"],
            "similarity": s["similarity"],
        }
        for s in scored[:5]
        if s["similarity"] >= 0.45
    ]
    return {
        "status": status,
        "confidence": conf,
        "evidence": citations,
        "model": "embedding-crosscheck-v1",
        "note": (
            "Statuses reflect overlap with other outlets in the same story cluster, "
            "not independent fact-checker verdicts."
        ),
    }


def analyze_article_claims(db: Session, article: Article, replace: bool = True) -> list[Claim]:
    if replace:
        db.query(Claim).filter(Claim.article_id == article.id).delete()
        db.commit()

    text = f"{article.original_headline}. {article.content_text or ''}"
    claim_texts = extract_claims_from_text(text)
    peers: list[Article] = []
    if article.story_id:
        peers = (
            db.query(Article)
            .filter(Article.story_id == article.story_id, Article.id != article.id)
            .all()
        )

    created: list[Claim] = []
    for claim_text in claim_texts:
        verification = verify_claim_against_articles(claim_text, peers) if peers else {
            "status": "unverified",
            "confidence": 0.25,
            "evidence": [],
            "model": "embedding-crosscheck-v1",
            "note": "No peer articles in cluster for cross-check.",
        }
        row = Claim(
            article_id=article.id,
            story_id=article.story_id,
            claim_text=claim_text,
            status=verification["status"],
            confidence=verification["confidence"],
            evidence_json=json.dumps(
                {"citations": verification["evidence"], "note": verification["note"]},
                ensure_ascii=False,
            ),
            model=verification["model"],
        )
        db.add(row)
        created.append(row)
    db.commit()
    for row in created:
        db.refresh(row)
    return created
