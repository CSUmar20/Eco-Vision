from pathlib import Path

import pytest

from app.services.classifier import CANDIDATE_LABELS
from evaluation.evaluate import calculate_metrics, load_manifest

MANIFEST_PATH = Path(__file__).parents[1] / "evaluation" / "household_items.json"


def test_household_item_manifest_covers_every_classifier_label() -> None:
    manifest = load_manifest(MANIFEST_PATH)
    samples = manifest["samples"]

    assert len(samples) == 30
    assert len({sample["id"] for sample in samples}) == len(samples)
    assert {sample["expected_label"] for sample in samples} == set(CANDIDATE_LABELS)
    assert all(
        sample["source_page_url"].startswith("https://commons.wikimedia.org/")
        for sample in samples
    )
    assert all(sample["author"] for sample in samples)
    assert all(sample["license"] for sample in samples)


def test_calculate_metrics_reports_accuracy_and_confusions() -> None:
    predictions = [
        {
            "expected_label": "a cardboard box",
            "predicted_label": "a cardboard box",
            "correct": True,
        },
        {
            "expected_label": "a sheet of paper",
            "predicted_label": "a cardboard box",
            "correct": False,
        },
        {
            "expected_label": "a sheet of paper",
            "predicted_label": "a cardboard box",
            "correct": False,
        },
    ]

    metrics = calculate_metrics(predictions)

    assert metrics["top_1_accuracy"] == pytest.approx(1 / 3)
    assert metrics["correct_count"] == 1
    assert metrics["incorrect_count"] == 2
    assert metrics["confusions"] == [
        {
            "expected_label": "a sheet of paper",
            "predicted_label": "a cardboard box",
            "count": 2,
        }
    ]
