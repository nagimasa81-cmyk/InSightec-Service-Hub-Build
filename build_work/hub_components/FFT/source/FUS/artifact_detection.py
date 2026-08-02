from __future__ import annotations

from dataclasses import dataclass
import json
import numpy as np


@dataclass
class DetectionResult:
    label: str
    confidence: float
    distance: float
    support: int
    status: str
    alternatives: list[tuple[str, float, float, int]]


def _robust_scale(training: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    median = np.nanmedian(training, axis=0)
    mad = np.nanmedian(np.abs(training - median), axis=0)
    scale = 1.4826 * mad
    std = np.nanstd(training, axis=0)
    scale = np.where(np.isfinite(scale) & (scale > 1e-12), scale, std)
    scale = np.where(np.isfinite(scale) & (scale > 1e-12), scale, 1.0)
    median = np.where(np.isfinite(median), median, 0.0)
    return median, scale


def _impute(matrix: np.ndarray, median: np.ndarray) -> np.ndarray:
    return np.where(np.isfinite(matrix), matrix, median)


def classify_feature_vector(
    vector: np.ndarray,
    training: np.ndarray,
    labels: list[str],
    *,
    minimum_samples_per_class: int = 2,
) -> DetectionResult:
    if training.ndim != 2 or training.shape[0] == 0:
        return DetectionResult(
            label="Insufficient training data",
            confidence=0.0,
            distance=float("inf"),
            support=0,
            status="NO_TRAINING_DATA",
            alternatives=[],
        )

    median, scale = _robust_scale(training)
    train = (_impute(training, median) - median) / scale
    query = (_impute(np.asarray(vector, dtype=float)[None, :], median) - median) / scale
    query = query[0]

    class_scores = []
    unique_labels = sorted(set(labels))
    for label in unique_labels:
        indices = [i for i, value in enumerate(labels) if value == label]
        support = len(indices)
        if support < minimum_samples_per_class:
            continue
        class_vectors = train[indices]
        center = np.median(class_vectors, axis=0)
        distance = float(np.sqrt(np.mean((query - center) ** 2)))
        class_scores.append((label, distance, support))

    if not class_scores:
        return DetectionResult(
            label="Insufficient training data",
            confidence=0.0,
            distance=float("inf"),
            support=0,
            status="INSUFFICIENT_CLASS_SUPPORT",
            alternatives=[],
        )

    class_scores.sort(key=lambda item: item[1])
    best_label, best_distance, support = class_scores[0]
    second_distance = class_scores[1][1] if len(class_scores) > 1 else best_distance + 1.0

    absolute_confidence = 1.0 / (1.0 + best_distance)
    separation = max(0.0, min(1.0, (second_distance - best_distance) / max(second_distance, 1e-12)))
    confidence = float(max(0.0, min(1.0, 0.65 * absolute_confidence + 0.35 * separation)))

    alternatives = [
        (label, float(1.0 / (1.0 + distance)), float(distance), count)
        for label, distance, count in class_scores[:5]
    ]
    status = "OK" if confidence >= 0.45 else "LOW_CONFIDENCE"
    return DetectionResult(
        label=best_label,
        confidence=confidence,
        distance=best_distance,
        support=support,
        status=status,
        alternatives=alternatives,
    )


def features_to_vector(features: dict, keys: list[str]) -> np.ndarray:
    values = []
    for key in keys:
        try:
            values.append(float(features.get(key, np.nan)))
        except Exception:
            values.append(np.nan)
    return np.asarray(values, dtype=float)
