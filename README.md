# SajhaNews — Nepal News Intelligence Platform

A local-first, Nepal-focused news intelligence platform inspired by Ground News. It aggregates legitimate RSS feeds, clusters multi-outlet coverage of the same event (English + Nepali), analyzes **government framing** with evidence (not fake left/right scores), and assists with claim cross-checking across outlets.

## What was wrong before

- Synthetic / hidden left–center–right bias bars eroded trust
- Title-only clustering failed across Nepali/English coverage
- Thin schema, no crawl observability, no claims, weak search/analytics
- Incomplete UI (missing pages, broken logo, disabled features)
- Dual deploy paths (FastAPI vs Passenger) drifted apart

## Architecture (v2)

| Layer | Stack |
|-------|--------|
| API | FastAPI (`backend/main.py`) |
| DB | SQLite by default (optional MySQL/Postgres via `DATABASE_URL`) |
| Ingestion | RSS allowlist in `backend/data/nepal_sources.json` + `crawler.py` |
| Embeddings | `paraphrase-multilingual-MiniLM-L12-v2` (fallback: hash TF vector) |
| Framing | Multilingual NLI (`mDeBERTa-v3-base-mnli-xnli`) + lexical evidence |
| UI | Next.js 16 App Router |

**Honesty rule:** Models are multilingual pretrained unless you set `FINETUNED_MODEL_PATH` after running the fine-tune script. The UI and API never claim “Nepal-trained” otherwise.

## Quick start (Windows)

### 1. Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python -m scripts.seed
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

API docs: http://127.0.0.1:8000/docs  
Health: http://127.0.0.1:8000/api/health

### 2. Frontend

```powershell
cd frontend
copy .env.example .env.local
npm install
npm run dev
```

App: http://localhost:3000

### 3. Optional live crawl

With the API running and `ADMIN_AUTH_DISABLED=true` (default in `.env.example`):

```powershell
curl -X POST http://127.0.0.1:8000/api/crawl
```

Or use **Admin → Trigger crawl**. First crawl with `ANALYZE_ON_CRAWL=true` downloads HF models and can take several minutes.

## Tests

```powershell
cd backend
.\venv\Scripts\Activate.ps1
pytest tests/ -q
```

## ML evaluation & fine-tuning

Labeled Nepal EN/NE pair set: `backend/data/story_pairs.jsonl`  
Framing labels: `backend/data/framing_labels.jsonl`

```powershell
cd backend
python ml/evaluate_clustering.py
python ml/evaluate_framing.py
# Optional CPU fine-tune (install datasets + accelerate first):
pip install datasets accelerate
python ml/train_framing.py
# Then set FINETUNED_MODEL_PATH=ml/artifacts/framing-nepal in .env
```

## Key routes (UI)

| Path | Purpose |
|------|---------|
| `/` | Multi-source feed, filters, framing distribution |
| `/story/[id]` | Headline comparison, framing, claims, coverage gap |
| `/sources` | Outlet directory & profiles |
| `/search` | Multilingual search |
| `/bias` | Framing explorer + methodology |
| `/analytics` | DB-backed language/topic/framing stats |
| `/admin` | Sources, crawl, diagnostics (`X-Admin-Key`) |

## Environment notes

- `ADMIN_AUTH_DISABLED=true` for local demos; set `false` and a strong `ADMIN_API_KEY` before any shared deployment.
- `EMBEDDING_ENABLED=false` / `FRAMING_ENABLED=false` skips heavy model loads (hash/lexical fallbacks remain).
- Seed data creates an offline multi-outlet demo story so the UI works without network.

## Limitations (documented)

- Full-page article scraping is not enabled (RSS summaries only) to stay within permitted use.
- Claim statuses are **cross-outlet consistency assists**, not independent fact-checker verdicts.
- Publisher “perspective” is curated/manual (`not_independently_rated` by default) — never auto-invented.
- Cross-language clustering needs the sentence-transformer model (`EMBEDDING_ENABLED=true`). The hash-TF fallback is English/token-overlap oriented and scores poorly on EN↔NE pairs.
- On the labeled `story_pairs.jsonl` set, multilingual MiniLM at threshold 0.55 is precise but still misses some Nepali–English paraphrases — expand the labeled set and fine-tune if you need higher recall.
- `passenger_wsgi.py` now wraps the FastAPI app via a2wsgi; prefer Uvicorn locally.
