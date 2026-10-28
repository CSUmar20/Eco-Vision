from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from PIL import Image, UnidentifiedImageError

from app.config import settings
from app.services.classifier import CANDIDATE_LABELS, classify_image

EVALUATION_DIR = Path(__file__).resolve().parent
DEFAULT_MANIFEST_PATH = EVALUATION_DIR / "household_items.json"
DEFAULT_CACHE_DIR = EVALUATION_DIR / ".cache" / "household-items"
DEFAULT_RESULTS_PATH = EVALUATION_DIR / "results" / "household-items.json"
DEFAULT_REPORT_PATH = EVALUATION_DIR / "results" / "household-items.md"
ALLOWED_IMAGE_HOSTS = {"thumb.wikimedia.org", "upload.wikimedia.org"}
MAX_IMAGE_BYTES = 20 * 1024 * 1024
FAILURE_CONTEXT = {
    "aluminum_can_02": "The can is heavily crushed, so its normal cylindrical silhouette is absent.",
    "plastic_bottle_01": "The clear PET bottle has the transparency and outline of a glass bottle.",
    "plastic_jug_01": "The compact square jug resembles a lidded takeout container.",
    "foam_container_01": "The closed foam clamshell is also visually a generic takeout container.",
    "electronic_phone_01": "The dark rectangular phone resembles a flat rechargeable battery.",
    "mixed_packaging_01": "The opened chip bag exposes food and reflective layers instead of a clean package silhouette.",
    "foil_tray_01": "The image contains a pile of crushed tray fragments rather than one intact tray.",
    "yard_trimmings_01": "The grass clippings sit inside a concrete drain whose rectangular shape dominates the frame.",
    "other_toothbrush_01": "The translucent, elongated toothbrush overlaps visually with bottles, straws, and medical sharps.",
}


class EvaluationError(RuntimeError):
    """Raised when the evaluation dataset cannot be validated or evaluated."""


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise EvaluationError(
            f"Could not read evaluation manifest {path}: {error}"
        ) from error

    samples = manifest.get("samples")
    if not isinstance(samples, list) or not samples:
        raise EvaluationError(
            "The evaluation manifest must contain a non-empty samples list."
        )

    sample_ids: set[str] = set()
    for sample in samples:
        if not isinstance(sample, dict):
            raise EvaluationError("Every evaluation sample must be an object.")

        sample_id = sample.get("id")
        expected_label = sample.get("expected_label")
        if not isinstance(sample_id, str) or not sample_id:
            raise EvaluationError("Every evaluation sample must have a non-empty id.")
        if sample_id in sample_ids:
            raise EvaluationError(f"Duplicate evaluation sample id: {sample_id}")
        sample_ids.add(sample_id)

        if expected_label not in CANDIDATE_LABELS:
            raise EvaluationError(
                f"Sample {sample_id} has a label not used by the classifier: {expected_label}"
            )

        image_url = sample.get("image_url")
        parsed_url = urllib_parse.urlparse(
            image_url if isinstance(image_url, str) else ""
        )
        if (
            parsed_url.scheme != "https"
            or parsed_url.hostname not in ALLOWED_IMAGE_HOSTS
        ):
            raise EvaluationError(
                f"Sample {sample_id} must use an HTTPS Wikimedia image URL."
            )

        sha256 = sample.get("sha256")
        if not isinstance(sha256, str) or len(sha256) != 64:
            raise EvaluationError(f"Sample {sample_id} must have a SHA-256 checksum.")

        filename = sample.get("filename")
        if not isinstance(filename, str) or Path(filename).name != filename:
            raise EvaluationError(f"Sample {sample_id} has an invalid cache filename.")

    return manifest


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as image_file:
        for chunk in iter(lambda: image_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download_image(url: str, destination: Path, timeout: float) -> None:
    request = urllib_request.Request(
        url,
        headers={
            "User-Agent": "EcoVisionEvaluation/1.0 (https://github.com/CSUmar20/Eco-Vision)"
        },
    )
    temporary_path = destination.with_suffix(f"{destination.suffix}.part")
    total_bytes = 0

    try:
        with urllib_request.urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get_content_type()
            if not content_type.startswith("image/"):
                raise EvaluationError(
                    f"Expected an image from {url}, but received {content_type}."
                )

            with temporary_path.open("wb") as image_file:
                while chunk := response.read(1024 * 1024):
                    total_bytes += len(chunk)
                    if total_bytes > MAX_IMAGE_BYTES:
                        raise EvaluationError(
                            f"Image at {url} exceeds the {MAX_IMAGE_BYTES}-byte limit."
                        )
                    image_file.write(chunk)
    except (OSError, urllib_error.URLError) as error:
        temporary_path.unlink(missing_ok=True)
        raise EvaluationError(f"Could not download {url}: {error}") from error
    except EvaluationError:
        temporary_path.unlink(missing_ok=True)
        raise

    temporary_path.replace(destination)


def cache_sample(
    sample: dict[str, Any],
    cache_dir: Path,
    *,
    offline: bool,
    refresh: bool,
    timeout: float,
) -> Path:
    destination = cache_dir / sample["filename"]
    expected_sha256 = sample["sha256"]

    if destination.exists() and not refresh:
        if _sha256(destination) == expected_sha256:
            return destination
        if offline:
            raise EvaluationError(
                f"Cached image checksum mismatch for {sample['id']} while in offline mode."
            )

    if offline:
        raise EvaluationError(
            f"Image is not cached for {sample['id']} while in offline mode."
        )

    cache_dir.mkdir(parents=True, exist_ok=True)
    _download_image(sample["image_url"], destination, timeout)
    actual_sha256 = _sha256(destination)
    if actual_sha256 != expected_sha256:
        destination.unlink(missing_ok=True)
        raise EvaluationError(
            f"Checksum mismatch for {sample['id']}: expected {expected_sha256}, "
            f"received {actual_sha256}."
        )

    return destination


def calculate_metrics(samples: list[dict[str, Any]]) -> dict[str, Any]:
    if not samples:
        raise EvaluationError("Cannot calculate metrics without predictions.")

    correct_count = sum(sample["correct"] for sample in samples)
    confusion_counts = Counter(
        (sample["expected_label"], sample["predicted_label"])
        for sample in samples
        if not sample["correct"]
    )
    label_support = Counter(sample["expected_label"] for sample in samples)
    label_correct = Counter(
        sample["expected_label"] for sample in samples if sample["correct"]
    )
    predicted_counts = Counter(sample["predicted_label"] for sample in samples)
    incorrect_predicted_counts = Counter(
        sample["predicted_label"] for sample in samples if not sample["correct"]
    )

    return {
        "sample_count": len(samples),
        "correct_count": correct_count,
        "incorrect_count": len(samples) - correct_count,
        "top_1_accuracy": correct_count / len(samples),
        "confusions": [
            {"expected_label": expected, "predicted_label": predicted, "count": count}
            for (expected, predicted), count in sorted(
                confusion_counts.items(), key=lambda item: (-item[1], item[0])
            )
        ],
        "per_label": [
            {
                "label": label,
                "support": label_support[label],
                "correct": label_correct[label],
                "accuracy": label_correct[label] / label_support[label],
            }
            for label in CANDIDATE_LABELS
            if label_support[label]
        ],
        "predicted_label_counts": [
            {"label": label, "count": count}
            for label, count in sorted(
                predicted_counts.items(), key=lambda item: (-item[1], item[0])
            )
        ],
        "incorrect_destination_counts": [
            {"label": label, "count": count}
            for label, count in sorted(
                incorrect_predicted_counts.items(), key=lambda item: (-item[1], item[0])
            )
        ],
    }


def _expected_prediction(
    predictions: list[dict[str, str | float]], expected_label: str
) -> tuple[int, float]:
    for rank, prediction in enumerate(predictions, start=1):
        if prediction["label"] == expected_label:
            return rank, float(prediction["score"])
    raise EvaluationError(
        f"Classifier did not return the expected candidate label: {expected_label}"
    )


def evaluate_manifest(
    manifest: dict[str, Any],
    cache_dir: Path,
    *,
    offline: bool,
    refresh: bool,
    timeout: float,
) -> dict[str, Any]:
    evaluated_samples: list[dict[str, Any]] = []

    for index, sample in enumerate(manifest["samples"], start=1):
        print(f"[{index:02d}/{len(manifest['samples'])}] {sample['id']}", flush=True)
        image_path = cache_sample(
            sample,
            cache_dir,
            offline=offline,
            refresh=refresh,
            timeout=timeout,
        )
        try:
            with Image.open(image_path) as image:
                predictions = classify_image(image)
        except (OSError, UnidentifiedImageError) as error:
            raise EvaluationError(
                f"Could not open cached image {image_path}: {error}"
            ) from error

        expected_rank, expected_score = _expected_prediction(
            predictions, sample["expected_label"]
        )
        evaluated_samples.append(
            {
                "id": sample["id"],
                "expected_label": sample["expected_label"],
                "predicted_label": predictions[0]["label"],
                "top_1_score": predictions[0]["score"],
                "correct": predictions[0]["label"] == sample["expected_label"],
                "expected_rank": expected_rank,
                "expected_score": expected_score,
                "top_5": predictions[:5],
                "failure_context": FAILURE_CONTEXT.get(sample["id"]),
            }
        )

    serialized_samples = json.dumps(
        manifest["samples"], ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "model": settings.hf_model,
        "hypothesis_template": "This is a photo of {}.",
        "candidate_labels": CANDIDATE_LABELS,
        "dataset": {
            "name": manifest["name"],
            "version": manifest["version"],
            "sample_count": len(manifest["samples"]),
            "manifest_sha256": hashlib.sha256(serialized_samples.encode()).hexdigest(),
        },
        "metrics": calculate_metrics(evaluated_samples),
        "samples": evaluated_samples,
    }


def render_report(results: dict[str, Any]) -> str:
    metrics = results["metrics"]
    accuracy_percent = metrics["top_1_accuracy"] * 100
    lines = [
        "# EcoVision household-item classifier evaluation",
        "",
        f"- Model: `{results['model']}`",
        f"- Dataset: {results['dataset']['name']} v{results['dataset']['version']}",
        f"- Evaluated: {results['generated_at']}",
        f"- Images: {metrics['sample_count']} real, human-labeled household-item photographs",
        "",
        "## Result",
        "",
        (
            f"Top-1 accuracy was **{accuracy_percent:.1f}%** "
            f"({metrics['correct_count']}/{metrics['sample_count']})."
        ),
        "",
        (
            "This is a small diagnostic baseline, not a production acceptance threshold. "
            "It covers every current candidate label at least once, but most labels have only "
            "one example. Beverage cans, food cans, plastic beverage bottles, and electronic "
            "devices have two examples each."
        ),
        "",
        "## Confused categories",
        "",
    ]

    if metrics["confusions"]:
        lines.extend(
            [
                "| Known label | Predicted label | Count |",
                "|---|---|---:|",
                *[
                    f"| {row['expected_label']} | {row['predicted_label']} | {row['count']} |"
                    for row in metrics["confusions"]
                ],
            ]
        )
        highest_count = metrics["incorrect_destination_counts"][0]["count"]
        common_destinations = [
            row["label"]
            for row in metrics["incorrect_destination_counts"]
            if row["count"] == highest_count
        ]
        lines.extend(
            [
                "",
                (
                    "No exact known-label → predicted-label pair occurred more than once. The "
                    f"most common incorrect destination labels were {', '.join(common_destinations)} "
                    f"({highest_count} errors each)."
                ),
            ]
        )
    else:
        lines.append("No top-1 category confusions occurred in this run.")

    lines.extend(
        [
            "",
            "## Specific failures",
            "",
        ]
    )
    failures = [sample for sample in results["samples"] if not sample["correct"]]
    if failures:
        lines.extend(
            [
                "| Image ID | Known label | Predicted label | Top-1 score | Known-label rank | Image characteristic |",
                "|---|---|---|---:|---:|---|",
                *[
                    f"| `{sample['id']}` | {sample['expected_label']} | "
                    f"{sample['predicted_label']} | {sample['top_1_score']:.3f} | "
                    f"{sample['expected_rank']} | {sample['failure_context']} |"
                    for sample in failures
                ],
            ]
        )
    else:
        lines.append("No top-1 failures occurred in this run.")

    lines.extend(
        [
            "",
            "## Per-label results",
            "",
            "| Known label | Correct | Support | Accuracy |",
            "|---|---:|---:|---:|",
            *[
                f"| {row['label']} | {row['correct']} | {row['support']} | "
                f"{row['accuracy'] * 100:.1f}% |"
                for row in metrics["per_label"]
            ],
            "",
            "## Reproduce",
            "",
            "From `backend/`, with the existing virtual environment activated:",
            "",
            "```bash",
            "python -m evaluation.evaluate",
            "```",
            "",
            (
                "The first run downloads the exact, checksummed Wikimedia Commons thumbnails "
                "listed in `evaluation/household_items.json`. Later runs reuse the ignored local "
                "cache. Use `--offline` to prohibit downloads or `--refresh` to download and "
                "verify every image again."
            ),
            "",
            (
                "The JSON result beside this report contains each image's top five predictions, "
                "the known label's rank, and the raw confidence-like CLIP scores. These scores "
                "are useful for ranking but are not calibrated probabilities."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _write_outputs(
    results: dict[str, Any], results_path: Path, report_path: Path
) -> None:
    results_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    report_path.write_text(render_report(results), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate EcoVision's production classifier on real household-item photos."
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument(
        "--offline", action="store_true", help="Never access the network."
    )
    parser.add_argument(
        "--refresh", action="store_true", help="Download and verify every image again."
    )
    parser.add_argument("--download-timeout", type=float, default=30.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.offline and args.refresh:
        raise SystemExit("--offline and --refresh cannot be used together.")
    if args.download_timeout <= 0:
        raise SystemExit("--download-timeout must be greater than zero.")
    if args.offline:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"

    try:
        manifest = load_manifest(args.manifest)
        results = evaluate_manifest(
            manifest,
            args.cache_dir,
            offline=args.offline,
            refresh=args.refresh,
            timeout=args.download_timeout,
        )
        _write_outputs(results, args.results, args.report)
    except EvaluationError as error:
        raise SystemExit(f"Evaluation failed: {error}") from error

    print(
        f"Top-1 accuracy: {results['metrics']['correct_count']}/"
        f"{results['metrics']['sample_count']} "
        f"({results['metrics']['top_1_accuracy'] * 100:.1f}%)"
    )
    print(f"Results: {args.results}")
    print(f"Report: {args.report}")


if __name__ == "__main__":
    main()
