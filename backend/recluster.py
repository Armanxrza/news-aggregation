"""Rebuild story assignments using embedding/title clustering."""

from __future__ import annotations

from database import SessionLocal, init_db
from services.clustering import recluster_all


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        result = recluster_all(db)
        print(
            f"Reassigned {result['articles_reassigned']} articles "
            f"into {result['stories']} stories"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
