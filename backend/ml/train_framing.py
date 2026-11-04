"""Train the desk framing classifier.

The shipped model is a character-and-word logistic regression. It is the
strongest classifier this CPU desk can run on the curated English and Nepali
labels in data/framing_labels.jsonl. A transformer fine-tune remains available
with FRAMING_TRAIN_TRANSFORMER=1 when torch and datasets are installed; that
path is not the default because the labeled set is small and there is no GPU.

Outputs:
  ml/artifacts/framing-desk/model.joblib
  ml/artifacts/framing-desk/metrics.json
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from config import DATA_DIR, ML_DIR

ARTIFACT_DIR = ML_DIR / "artifacts" / "framing-desk"
LABELS = ("government_critical", "government_neutral", "government_supportive")


def load_rows() -> list[dict]:
    path = DATA_DIR / "framing_labels.jsonl"
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if row.get("text") and row.get("label") in LABELS:
            rows.append(row)
    return rows


def make_desk_pipeline():
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import FeatureUnion, Pipeline
    from sklearn.preprocessing import MaxAbsScaler

    from ml.features import LexiconFeatures

    return Pipeline(
        [
            (
                "features",
                FeatureUnion(
                    [
                        (
                            "char",
                            TfidfVectorizer(
                                analyzer="char_wb",
                                ngram_range=(3, 5),
                                min_df=1,
                                sublinear_tf=True,
                            ),
                        ),
                        (
                            "lex",
                            Pipeline(
                                [
                                    ("cues", LexiconFeatures()),
                                    ("scale", MaxAbsScaler()),
                                ]
                            ),
                        ),
                    ]
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    max_iter=2000,
                    class_weight="balanced",
                    C=1.0,
                    solver="lbfgs",
                ),
            ),
        ]
    )


def train_desk(rows: list[dict]) -> dict:
    import joblib
    from sklearn.metrics import accuracy_score, f1_score
    from sklearn.model_selection import cross_val_predict

    texts = [r["text"] for r in rows]
    labels = [r["label"] for r in rows]
    holdout = make_desk_pipeline()
    pred = cross_val_predict(holdout, texts, labels, cv=5)
    per_label = {}
    for label in LABELS:
        gold = [y == label for y in labels]
        hats = [y == label for y in pred]
        tp = sum(g and h for g, h in zip(gold, hats))
        fp = sum((not g) and h for g, h in zip(gold, hats))
        fn = sum(g and (not h) for g, h in zip(gold, hats))
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        per_label[label] = round((2 * prec * rec / (prec + rec)) if prec + rec else 0.0, 4)

    metrics = {
        "model": "framing-desk-v1",
        "task": "government_framing",
        "labels": list(LABELS),
        "rows": len(rows),
        "eval_rows": len(rows),
        "holdout_accuracy": round(float(accuracy_score(labels, pred)), 4),
        "holdout_macro_f1": round(float(f1_score(labels, pred, average="macro", labels=list(LABELS))), 4),
        "cv_folds": 5,
        "per_label_f1": per_label,
        "note": (
            "Scores are 5-fold cross-validation on framing_labels.jsonl before the saved "
            "model is refit on every row. The file mixes 12 hand-checked gold lines with "
            "curated desk examples in English and Nepali. It is not a model of every story."
        ),
    }

    shipped = make_desk_pipeline()
    shipped.fit(texts, labels)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(shipped, ARTIFACT_DIR / "model.joblib")
    (ARTIFACT_DIR / "metrics.json").write_text(
        json.dumps(metrics, indent=2),
        encoding="utf-8",
    )
    return metrics


def _train_transformer(rows: list[dict]) -> None:
    """Optional DistilBERT fine-tune. Not used unless FRAMING_TRAIN_TRANSFORMER=1."""
    import numpy as np
    import torch
    from datasets import Dataset
    from sklearn.model_selection import train_test_split
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        Trainer,
        TrainingArguments,
    )

    label2id = {label: i for i, label in enumerate(LABELS)}
    id2label = {i: label for label, i in label2id.items()}
    texts = [r["text"] for r in rows]
    y = [label2id[r["label"]] for r in rows]
    train_x, eval_x, train_y, eval_y = train_test_split(
        texts, y, test_size=0.25, random_state=42, stratify=y
    )
    model_name = os.getenv("FRAMING_TRAIN_BASE", "distilbert-base-multilingual-cased")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=len(LABELS),
        id2label=id2label,
        label2id=label2id,
    )
    out = ML_DIR / "artifacts" / "framing-transformer"

    def tokenize_batch(batch):
        return tokenizer(batch["text"], truncation=True, padding="max_length", max_length=192)

    train_ds = Dataset.from_dict({"text": train_x, "label": train_y}).map(tokenize_batch, batched=True)
    eval_ds = Dataset.from_dict({"text": eval_x, "label": eval_y}).map(tokenize_batch, batched=True)
    train_ds.set_format("torch", columns=["input_ids", "attention_mask", "label"])
    eval_ds.set_format("torch", columns=["input_ids", "attention_mask", "label"])
    args = TrainingArguments(
        output_dir=str(out / "checkpoints"),
        num_train_epochs=int(os.getenv("FRAMING_TRAIN_EPOCHS", "3")),
        per_device_train_batch_size=4,
        learning_rate=2e-5,
        eval_strategy="epoch",
        save_strategy="no",
        report_to=[],
        use_cpu=not torch.cuda.is_available(),
    )

    def compute_metrics(eval_pred):
        logits, y_true = eval_pred
        preds = np.argmax(logits, axis=-1)
        return {"accuracy": float((preds == y_true).mean())}

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        compute_metrics=compute_metrics,
    )
    trainer.train()
    trainer.save_model(str(out))
    tokenizer.save_pretrained(str(out))
    print(f"Saved transformer checkpoint to {out}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rows = load_rows()
    if len(rows) < 12:
        print(f"Need at least 12 labeled rows; found {len(rows)}")
        sys.exit(1)
    print("SajhaNews framing desk train")
    print(f"  Rows: {len(rows)}")
    metrics = train_desk(rows)
    print(f"  Hold-out accuracy: {metrics['holdout_accuracy']}")
    print(f"  Hold-out macro F1: {metrics['holdout_macro_f1']}")
    print(f"  Saved: {ARTIFACT_DIR / 'model.joblib'}")
    if os.getenv("FRAMING_TRAIN_TRANSFORMER", "").lower() in {"1", "true", "yes"}:
        _train_transformer(rows)


if __name__ == "__main__":
    main()
