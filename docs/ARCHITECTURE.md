# SajhaNews Architecture (v2)

## Problems fixed

1. **Fake bias analytics** — Removed public left/center/right synthesis; political orientation is never invented.
2. **Weak clustering** — Multilingual embeddings + title heuristics with time windows; admin merge/split corrections.
3. **Opaque framing** — Government-framing labels store model id, confidence, evidence text, method, and uncertainty.
4. **No observability** — `crawl_runs`, per-source `last_crawl_*`, analysis runs.
5. **Incomplete product surface** — Search, sources, analytics, bias explorer, claims, admin auth header.
6. **Ops drift** — Single FastAPI app is the source of truth for local runs.

## Runtime topology

```
Next.js (UI) ──HTTP──► FastAPI (main.py)
                          │
                          ├─ SQLAlchemy (SQLite default)
                          ├─ crawler.py (RSS allowlist)
                          └─ services/
                               language, nepal, embedding,
                               clustering, framing, claims, bias_signals
```

## Data model

- `sources` — publishers + curated perspective (nullable / not_independently_rated)
- `stories` — event clusters with embedding + cluster metadata
- `articles` — normalized items with language, topics, entities, signals, framing
- `claims` — extracted claims + cross-outlet status
- `crawl_runs` / `analysis_runs` / `story_corrections` / `eval_pairs`

## AI honesty

| Capability | Default model | Nepal-finetuned? |
|------------|---------------|------------------|
| Framing | mDeBERTa MNLI-XNLI zero-shot | Only if `FINETUNED_MODEL_PATH` set after `ml/train_framing.py` |
| Embeddings | paraphrase-multilingual-MiniLM-L12-v2 | No (general multilingual) |
| Fallback | lexical / hash-TF | Explicitly labeled in API |

Labeled evaluation data lives in `backend/data/story_pairs.jsonl` and `framing_labels.jsonl`.

## Ingestion pipeline

fetch → parse → URL canonicalize → near-dup → language → topics/entities/signals → embed → story assign → optional framing/claims → crawl metrics

## Security

- Admin mutations require `X-Admin-Key` unless `ADMIN_AUTH_DISABLED=true`
- CORS restricted to configured origins
- Crawl is not an open URL fetcher — registry allowlist only
