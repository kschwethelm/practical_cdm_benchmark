from __future__ import annotations

from typing import Any

import cdm.eval.acc_metrics as acc_metrics

ALLOWED_DIAGNOSES = ("appendicitis", "cholecystitis", "diverticulitis", "pancreatitis")


class BenchmarkEvaluator:
    def __init__(self):
        self.total = 0
        self.correct = 0
        self.unknown = 0
        self.per_diag_counts = {dx: 0 for dx in ALLOWED_DIAGNOSES}
        self.per_diag_correct = {dx: 0 for dx in ALLOWED_DIAGNOSES}

    def record(self, gt_dx: str | None, pred_dx: str | None) -> tuple[str, bool]:
        self.total += 1
        normalized_gt = acc_metrics.normalize_diagnosis(gt_dx or "")

        is_correct = acc_metrics.diagnoses_match(gt_dx, pred_dx or "")
        self.correct += bool(is_correct)
        self.unknown += pred_dx not in ALLOWED_DIAGNOSES

        if normalized_gt in ALLOWED_DIAGNOSES:
            self.per_diag_counts[normalized_gt] += 1
            self.per_diag_correct[normalized_gt] += bool(is_correct)

        return normalized_gt, is_correct

    def summary(self) -> dict[str, Any]:
        per_diag = {}
        for diag in sorted(ALLOWED_DIAGNOSES):
            cases = self.per_diag_counts.get(diag, 0)
            correct = self.per_diag_correct.get(diag, 0)
            per_diag[diag] = {
                "cases": cases,
                "correct": correct,
                "accuracy": correct / cases if cases else 0.0,
            }

        return {
            "processed_cases": self.total,
            "correct": self.correct,
            "unknown": self.unknown,
            "accuracy": self.correct / self.total if self.total else 0.0,
            "per_diagnosis": per_diag,
        }
