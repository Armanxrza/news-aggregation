"""Backfill soft government-POV scores for every article."""

from __future__ import annotations

import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND))

from database import Article, SessionLocal, _json_dumps, init_db
from services.framing import analyze_government_framing


def main() -> None:
    init_db()
    db = SessionLocal()
    rows = db.query(Article).all()
    updated = 0
    for article in rows:
        text = f"{article.original_headline}\n{article.content_text or ''}"
        result = analyze_government_framing(text, lexical_only=True)
        article.government_framing = result["label"]
        article.framing_confidence = result.get("confidence")
        article.framing_evidence = result.get("evidence")
        article.framing_model = result.get("model")
        article.framing_method = result.get("method")
        article.framing_scores_json = _json_dumps(result.get("scores"))
        updated += 1
        if updated % 100 == 0:
            db.commit()
            print(f"  … {updated}")
    db.commit()
    db.close()
    print(f"Backfilled soft gov-POV scores on {updated} articles")


if __name__ == "__main__":
    main()
