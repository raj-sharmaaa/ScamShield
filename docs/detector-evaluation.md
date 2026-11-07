# Detector Evaluation Plan

ScamShield currently uses a deterministic heuristic rules engine. This document defines how to evaluate changes to that engine without implying that a benchmark has already been run.

## Goals

- Measure how often the detector identifies labeled suspicious and benign examples.
- Make false positives and false negatives visible before changing scoring rules.
- Keep evaluation data reproducible, reviewable, and safe to share.
- Avoid publishing an accuracy claim without a versioned dataset and recorded run.

## Dataset format

Store fixtures as JSONL (one JSON object per line). A fixture should use this schema:

```json
{
  "id": "synthetic-0001",
  "scan_type": "message",
  "content": "Synthetic example content using reserved example domains",
  "expected_label": "suspicious",
  "source_type": "synthetic",
  "reviewed_at": "2026-01-15",
  "notes": "Reason for the expected label"
}
```

Allowed `expected_label` values should be documented by the evaluator and mapped consistently to the detector's output categories. Keep examples synthetic where possible. If real-world samples are ever used, record provenance and permission, remove personal information, and defang URLs so a fixture cannot accidentally trigger a visit.

Do not commit private messages, credentials, live malicious payloads, or personal data. Never fetch or execute URLs as part of offline evaluation.

## Dataset splits and versioning

- Keep a stable, versioned evaluation set separate from examples used to tune rules.
- If a future ML model is trained, split data before training and keep the held-out test set untouched until final evaluation.
- Record dataset version, commit SHA, evaluator version, and date for every run.
- Review duplicate or near-duplicate examples to reduce leakage between splits.

## Metrics

For the suspicious class, report:

- **Precision:** true positives / (true positives + false positives).
- **Recall:** true positives / (true positives + false negatives).
- **F1:** harmonic mean of precision and recall.
- **False-positive rate:** benign examples incorrectly flagged / all benign examples.

Also publish the confusion matrix and counts for every label. Include a short qualitative review of false positives and false negatives; aggregate scores alone can hide harmful failure modes.

## Change review

Before changing detector rules:

1. Run the same versioned fixtures against the base and proposed revisions.
2. Compare per-class metrics and the confusion matrix.
3. Inspect newly introduced false positives and false negatives.
4. Document intentional trade-offs and any known blind spots.
5. Add regression fixtures for confirmed bugs using synthetic or safely defanged examples.

## Reporting results

Do not state that the detector is "X% accurate" unless the dataset, label definitions, evaluation command, commit, and results are published together. A small or synthetic dataset is useful for regression testing, but it is not evidence of real-world performance.
