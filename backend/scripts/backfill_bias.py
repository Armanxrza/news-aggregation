"""Backfill political_bias for existing articles (lexical, fast)."""

from __future__ import annotations

import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND))

from database import Article, SessionLocal, init_db
from services.bias import analyze_political_bias


def main() -> None:
    init_db()
    db = SessionLocal()
    rows = db.query(Article).filter(
        (Article.political_bias.is_(None)) | (Article.political_bias == "")
    ).all()
    updated = 0
    for article in rows:
        text = f"{article.original_headline}\n{article.content_text or ''}"
        result = analyze_political_bias(text, lexical_only=True)
        article.political_bias = result["label"]
        article.bias_confidence = result.get("confidence")
        article.bias_evidence = result.get("evidence")
        article.bias_model = result.get("model")
        article.ai_bias_score = result.get("score")
        updated += 1
        if updated % 100 == 0:
            db.commit()
            print(f"  … {updated}")
    db.commit()
    db.close()
    print(f"Backfilled bias on {updated} articles")


if __name__ == "__main__":
    main()
