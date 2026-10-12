"""Fine-tune a small framing classifier on framing_labels.jsonl.

This script is the reproducible path to produce Nepal-specific framing weights
saved under ml/artifacts/framing-nepal. Point FINETUNED_MODEL_PATH at that
directory after training to use the fine-tuned model in production.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from config import DATA_DIR, HF_FRAMING_MODEL, ML_DIR

ARTIFACT_DIR = ML_DIR / "artifacts" / "framing-nepal"
LABEL2ID = {
    "government_supportive": 0,
    "government_critical": 1,
    "government_neutral": 2,
}
ID2LABEL = {v: k for k, v in LABEL2ID.items()}


def _missing_deps_message() -> str:
    return (
        "Optional training dependencies are not installed.\n"
        "Install with:\n"
        "  pip install datasets accelerate scikit-learn\n"
        "Then re-run:\n"
        "  python -m ml.train_framing\n"
    )


def load_rows() -> list[dict]:
    path = DATA_DIR / "framing_labels.jsonl"
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return [r for r in rows if r.get("text") and r.get("label") in LABEL2ID]


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    try:
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
    except ImportError:
        print(_missing_deps_message())
        sys.exit(0)

    rows = load_rows()
    if len(rows) < 6:
        print(f"Need at least 6 labeled rows; found {len(rows)} in framing_labels.jsonl")
        sys.exit(0)

    texts = [r["text"] for r in rows]
    labels = [LABEL2ID[r["label"]] for r in rows]

    train_texts, eval_texts, train_labels, eval_labels = train_test_split(
        texts, labels, test_size=0.25, random_state=42, stratify=labels
    )

    model_name = os.getenv("FRAMING_TRAIN_BASE", "distilbert-base-multilingual-cased")
    if os.getenv("FRAMING_TRAIN_USE_HF_FRAMING", "").lower() == "true":
        model_name = HF_FRAMING_MODEL

    print("SajhaNews framing fine-tune")
    print(f"  Base model: {model_name}")
    print(f"  Train rows: {len(train_texts)}  Eval rows: {len(eval_texts)}")
    print(f"  Output: {ARTIFACT_DIR}")
    print(
        "  Note: This is how Nepal-specific framing weights would be produced; "
        "set FINETUNED_MODEL_PATH to the artifact directory after training."
    )

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=len(LABEL2ID),
        id2label=ID2LABEL,
        label2id=LABEL2ID,
    )

    # Freeze lower layers on CPU to keep training lightweight
    freeze = os.getenv("FRAMING_TRAIN_FREEZE_LAYERS", "true").lower() == "true"
    if freeze and hasattr(model, "distilbert"):
        for param in model.distilbert.parameters():
            param.requires_grad = False
        for param in model.pre_classifier.parameters():
            param.requires_grad = True
        for param in model.classifier.parameters():
            param.requires_grad = True

    def tokenize_batch(batch):
        return tokenizer(
            batch["text"],
            truncation=True,
            padding="max_length",
            max_length=256,
        )

    train_ds = Dataset.from_dict({"text": train_texts, "label": train_labels})
    eval_ds = Dataset.from_dict({"text": eval_texts, "label": eval_labels})
    train_ds = train_ds.map(tokenize_batch, batched=True)
    eval_ds = eval_ds.map(tokenize_batch, batched=True)
    train_ds.set_format("torch", columns=["input_ids", "attention_mask", "label"])
    eval_ds.set_format("torch", columns=["input_ids", "attention_mask", "label"])

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    args = TrainingArguments(
        output_dir=str(ARTIFACT_DIR / "checkpoints"),
        num_train_epochs=int(os.getenv("FRAMING_TRAIN_EPOCHS", "3")),
        per_device_train_batch_size=int(os.getenv("FRAMING_TRAIN_BATCH", "4")),
        per_device_eval_batch_size=4,
        learning_rate=float(os.getenv("FRAMING_TRAIN_LR", "2e-5")),
        eval_strategy="epoch",
        save_strategy="no",
        logging_steps=10,
        report_to=[],
        use_cpu=not torch.cuda.is_available(),
    )

    def compute_metrics(eval_pred):
        logits, y_true = eval_pred
        preds = np.argmax(logits, axis=-1)
        acc = (preds == y_true).mean()
        return {"accuracy": float(acc)}

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        compute_metrics=compute_metrics,
    )
    trainer.train()
    metrics = trainer.evaluate()
    print(f"  Eval accuracy: {metrics.get('eval_accuracy', metrics)}")

    trainer.save_model(str(ARTIFACT_DIR))
    tokenizer.save_pretrained(str(ARTIFACT_DIR))
    (ARTIFACT_DIR / "label_map.json").write_text(
        json.dumps({"label2id": LABEL2ID, "id2label": ID2LABEL}, indent=2),
        encoding="utf-8",
    )
    print(f"Saved fine-tuned model to {ARTIFACT_DIR}")


if __name__ == "__main__":
    main()
