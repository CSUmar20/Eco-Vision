from functools import lru_cache
from io import BytesIO
from typing import Any
from urllib import request as urllib_request

from PIL import Image, ImageOps, UnidentifiedImageError
from transformers import pipeline

from app.config import settings

CANDIDATE_LABELS = [
    "an aluminum beverage can",
    "a metal food can",
    "a clear glass bottle or jar",
    "a cardboard box",
    "a sheet of paper",
    "a clear plastic beverage bottle",
    "an opaque plastic jug or container",
    "a plastic bag or plastic film",
    "a polystyrene foam container",
    "food waste",
    "a household battery",
    "an electronic device",
    "clothing or textile",
    "mixed-material packaging",
    "another type of household object",
]


@lru_cache(maxsize=1)
def get_classifier() -> Any:
    return pipeline(
        task="zero-shot-image-classification",
        model=settings.hf_model,
    )


def classify_image(image: Image.Image | str) -> list[dict[str, str | float]]:
    if isinstance(image, str):
        with urllib_request.urlopen(image) as response:
            image_bytes = response.read()

        image = Image.open(BytesIO(image_bytes))

    try:
        prepared_image = ImageOps.exif_transpose(image).convert("RGB")
    except (UnidentifiedImageError, OSError) as error:
        raise ValueError("The provided image is not a valid image file.") from error

    raw_predictions = get_classifier()(
        prepared_image,
        candidate_labels=CANDIDATE_LABELS,
        hypothesis_template="This is a photo of {}.",
    )

    return [
        {
            "label": str(prediction["label"]),
            "score": float(prediction["score"]),
        }
        for prediction in raw_predictions
    ]
