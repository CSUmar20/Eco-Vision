from io import BytesIO
from typing import Annotated

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_database_session
from app.models import Scan
from app.schemas import PredictionResponse, ScanResponse
from app.services.classifier import classify_image

app = FastAPI(
    title="EcoVision API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["POST"],
    allow_headers=["*"],
)


ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}


DatabaseSession = Annotated[
    Session,
    Depends(get_database_session),
]

UploadedImage = Annotated[
    UploadFile,
    File(description="A photograph of one item to classify"),
]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/classify",
    response_model=ScanResponse,
    status_code=status.HTTP_201_CREATED,
)
def classify_uploaded_image(
    file: UploadedImage,
    database: DatabaseSession,
) -> ScanResponse:
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only JPEG, PNG, and WebP images are supported.",
        )

    image_bytes = file.file.read(settings.max_image_bytes + 1)

    if len(image_bytes) > settings.max_image_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="The uploaded image exceeds the 10 MB limit.",
        )

    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded image is empty.",
        )

    try:
        with Image.open(BytesIO(image_bytes)) as image:
            predictions = classify_image(image)
    except (UnidentifiedImageError, OSError) as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is not a valid image.",
        ) from error

    if not predictions:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The classifier returned no predictions.",
        )

    top_prediction = predictions[0]

    scan = Scan(
        model_id=settings.hf_model,
        top_label=str(top_prediction["label"]),
        confidence=float(top_prediction["score"]),
        predictions=predictions,
    )

    try:
        database.add(scan)
        database.commit()
        database.refresh(scan)
    except SQLAlchemyError as error:
        database.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The scan result could not be saved.",
        ) from error

    return ScanResponse(
        scan_id=scan.id,
        created_at=scan.created_at,
        model_id=scan.model_id,
        top_prediction=PredictionResponse(
            label=scan.top_label,
            score=scan.confidence,
        ),
        alternatives=[
            PredictionResponse(
                label=str(prediction["label"]),
                score=float(prediction["score"]),
            )
            for prediction in predictions[1:5]
        ],
    )
