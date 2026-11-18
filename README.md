# Sajha Intelligence

Sajha aggregates Nepal-focused RSS coverage and groups articles by event identity. Its pipeline combines multilingual retrieval, Nepali named-entity extraction, structured event frames, time and location checks, and conservative relationship decisions. Emotion signals and government stance are stored separately per article and publisher.

## Architecture

| Layer | Implementation |
| --- | --- |
| API | FastAPI in `backend/main.py` |
| Storage | SQLAlchemy; SQLite for local work, persistent PostgreSQL recommended for deployment |
| Ingestion | Configured RSS allowlist, per-article transactions, bounded feed retries, URL and content fingerprints |
| Event retrieval | `intfloat/multilingual-e5-small` when the optional model runtime is available |
| Nepali entities | Curated Nepal entity catalog plus optional `SynapseHQ/Finetuned-NER-NepBertA` token classifier |
| Event decisions | Event identity frames, named entities, action families, dates, locations, and optional English NLI reranking |
| Government stance | Article-level Critical / Neutral / Supportive with evidence; Nepali uses a conservative rule fallback until a Nepali stance checkpoint is validated |
| Editorial tone | Separate attributed emotion and sensational-headline signals |
| UI | Next.js 16 App Router |

The E5 model card reports 100 supported languages and explicitly cautions that low-resource languages can perform worse. E5 therefore improves cross-language retrieval but is not treated as a final event decision. The model is not Nepal-fine-tuned. A local Nepali NER checkpoint is optional; its predictions are combined with the curated entity catalog and should be reviewed on Sajha's own feed. No fine-tuning has been run as part of this change.

## Local setup

### Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python -m scripts.seed
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

For multilingual embeddings, NLI stance analysis, and Nepali NER, install the optional model dependencies:

```powershell
pip install -r requirements-ml.txt
```

The first model-backed analysis downloads weights and needs additional memory. If the optional package or model is unavailable, the service logs the fallback and keeps the conservative event-frame path active.

### Frontend

```powershell
cd frontend
copy .env.example .env.local
npm install
npm run dev
```

Backend docs are at `http://127.0.0.1:8000/docs`; the UI is at `http://localhost:3000`.

### Crawl

Set `ADMIN_API_KEY` in `backend/.env`, then use the Admin page or send `X-Admin-Key` to `POST /api/crawl`. For a local-only demo, `ADMIN_AUTH_DISABLED=true` can be set while binding the API to localhost. Keep it false on any shared or public service.

## Evaluation and regression tests

```powershell
cd backend
pytest tests/ -q
python ml/evaluate_clustering.py
python ml/evaluate_framing.py
```

`data/story_pairs.jsonl` contains bilingual positive and hard-negative pairs. `data/event_clusters.jsonl` covers cluster quality, including the Kavre/Tihar tipper restrictions, different districts, same-actor different-event cases, follow-up coverage, and cross-language reporting. The evaluator prints pairwise precision, recall, F1, false-merge and false-split rates, B-cubed cluster scores, and adjusted Rand index. These fixtures are curated acceptance cases; newsroom review should continue adding adjudicated examples.

## Corrections and review

Authorized admins can merge stories, split articles, move an article, correct a story title or summary, and correct an article's stance. Each action is saved to `story_corrections` for audit and future evaluation. Feedback is recorded; no model training or fine-tuning is performed automatically.

## Deployment notes

- Set `ADMIN_AUTH_DISABLED=false`, use a generated `ADMIN_API_KEY`, and restrict `CORS_ORIGINS` to the frontend origin.
- Configure `DATABASE_URL` to a persistent managed database. SQLite on an ephemeral web-service filesystem can lose articles on restart.
- The current Render blueprint disables model weights on the free-sized API process to avoid memory exhaustion. That deployment still runs event-frame matching and uses embeddings only when enabled on a suitably sized instance.
- The in-process scheduler runs only while the API process is alive. A sleeping free web service is not an always-on crawler; reliable continuous collection needs an always-on worker or scheduled job and shared persistent storage.
- RSS article text is stored as inert text, and no arbitrary page-scraping URL or article-provided prompt is sent to a generative model.
- Story summaries are extractive and attributed to their source. Claim statuses are cross-outlet consistency assistance, not independent fact-checker verdicts.

## Current limits

- Cross-language event matching depends on model-backed multilingual embeddings for the broadest paraphrase coverage. The conservative fallback can match explicit structured event anchors, but does not promise reliable matching for every unseen paraphrase.
- Nepali C/N/S is deliberately conservative and does not use the current XNLI checkpoint, whose NLI fine-tuning does not include Nepali. A Nepali stance model needs a labeled evaluation set before it should replace this path.
- Emotion and sensationalism outputs are language cues with attribution, not verified psychological states or claims about editorial intent.
- Story titles use supported event-frame templates when the frame is strong; summaries quote selected source sentences and do not synthesize disputed facts.
