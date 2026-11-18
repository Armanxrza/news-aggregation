# Sajha Intelligence architecture

## Processing flow

```text
Configured RSS feeds
  -> bounded retry + URL validation
  -> HTML-to-text cleanup + content fingerprint
  -> idempotent article upsert
  -> language, topic, entity, and editorial-signal extraction
  -> multilingual event embedding + event frame
  -> recent candidate retrieval
  -> relationship classification + optional English NLI rerank
  -> SAME_EVENT / EVENT_UPDATE merge, or separate related story
  -> attributed story summary, timeline, source diversity, relevance score
  -> public story API + authorized correction endpoints
```

## Event identity

`services/event_intelligence.py` builds a compact frame from actors, locations, action families, objects, event markers, years, and topics. Original headlines and article text stay on each article. Known Nepal names and spellings are normalized alongside the original text; the optional Nepali NER model supplements the curated catalog.

`services/clustering.py` searches recent stories and combines event-frame evidence with multilingual embedding similarity. Lexical overlap and the hash-vector fallback never authorize an automatic merge by themselves. A candidate is assigned only for `SAME_EVENT` or `EVENT_UPDATE`. `DIRECTLY_RELATED_EVENT` is stored as a link to a separate story. Location, action, and year conflicts block a merge.

Embeddings default to `intfloat/multilingual-e5-small` with E5's query/passage prefixes. Stored story vectors include their model id and are regenerated when the configured model changes. The default deployment keeps the model disabled on small instances; when disabled, explicit event-frame evidence remains active.

The optional cross-encoder path uses the existing multilingual mDeBERTa XNLI zero-shot pipeline as a candidate reranker for English pairs only. Devanagari pairs skip this reranker because Nepali was not part of its XNLI fine-tuning languages. The reranker cannot override a hard location or action conflict.

## Article analysis separation

- **Government stance**: Critical / Neutral / Supportive is calculated per article. The English NLI path evaluates unquoted, non-attributed reporting. The Nepali fallback only assigns Critical or Supportive when it finds explicit unquoted evaluative wording tied to a government actor; otherwise it records Neutral with uncertainty. Emotion does not affect this label.
- **Editorial emotion**: records lexical emotion cues, likely speaker attribution, target phrase, tone cues, and possible sensational wording. These are signals, not psychological facts.
- **Entities and event frame**: Nepal lexicon plus optional Nepali token classification; used for event identity, not stance.
- **Importance**: recency, impact, local relevance, novelty, and independent-source diversity. Syndicated copies stay visible but do not increase independent-source counts.
- **Summary**: selected source sentences are clearly attributed; no generative model is configured, and allegations are not rewritten as verified facts.

## Reliability and security

- URL uniqueness plus a normalized content fingerprint make RSS replays idempotent.
- Unchanged articles with a current analysis version are skipped; changed feeds are reanalyzed.
- Feed requests retry transient failures with bounded exponential backoff. Each article is committed independently so an enrichment error does not roll back earlier articles in that feed.
- The RSS fetcher accepts only configured public HTTP(S) endpoints. Article content is reduced to inert text and is never used as a model instruction.
- Admin APIs require `X-Admin-Key` unless a local demo explicitly opts out. The Render blueprint sets authentication on, creates a key, and narrows CORS.
- Corrections are appended to `story_corrections` with before/after metadata where applicable. Feedback is not silently used to train a model.

## Evaluation

`data/story_pairs.jsonl` measures pairwise event match decisions. `data/event_clusters.jsonl` yields all within- and cross-cluster pairs, predicted connected components, pairwise false merge/split rates, B-cubed precision/recall/F1, and adjusted Rand index. Add newsroom-adjudicated examples before changing merge thresholds or enabling a heavier model in production.

## Deployment requirements

SQLite is suitable for local use. Production needs a persistent managed database. The current free Render API process disables model weights and can sleep, so its in-process crawl scheduler is not an always-on ingestion service. Continuous automated ingestion requires an always-on API/worker or a scheduled worker sharing the persistent database. Configure model flags only after measuring warm-start memory on the target instance.
