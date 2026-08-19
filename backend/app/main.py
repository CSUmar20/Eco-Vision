from io import BytesIO
from typing import Annotated
from uuid import UUID

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_database_session
from app.models import DisposalRule, Jurisdiction, Scan
from app.schemas import (
    DisposalRuleResponse,
    JurisdictionResponse,
    JurisdictionRulesResponse,
    PredictionResponse,
    ScanConfirmationRequest,
    ScanConfirmationResponse,
    ScanResponse,
)
from app.services.classifier import classify_image
from app.services.jurisdictions import (
    get_disposal_rules,
    get_jurisdiction,
    search_jurisdictions,
)

app = FastAPI(
    title="EcoVision API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["GET", "POST", "PATCH"],
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

SelectedJurisdiction = Annotated[
    UUID | None,
    Form(description="The recycling jurisdiction selected for this scan"),
]


def jurisdiction_response(jurisdiction: Jurisdiction) -> JurisdictionResponse:
    return JurisdictionResponse(
        id=jurisdiction.id,
        slug=jurisdiction.slug,
        name=jurisdiction.name,
        display_name=jurisdiction.display_name,
        jurisdiction_type=jurisdiction.jurisdiction_type,
        country_code=jurisdiction.country_code,
        state_code=jurisdiction.state_code,
        county_name=jurisdiction.county_name,
        waste_provider=jurisdiction.waste_provider,
        parent_id=jurisdiction.parent_id,
        postal_codes=[postal_code.postal_code for postal_code in jurisdiction.postal_codes],
    )


def disposal_rule_response(rule: DisposalRule) -> DisposalRuleResponse:
    return DisposalRuleResponse(
        material_key=rule.material_key,
        status=rule.status,
        instructions=rule.instructions,
        source_title=rule.source_title,
        source_url=rule.source_url,
        verified_at=rule.verified_at,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get(
    "/jurisdictions",
    response_model=list[JurisdictionResponse],
)
def search_jurisdiction_options(
    query: Annotated[str, Query(min_length=2, max_length=100)],
    database: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=20)] = 10,
) -> list[JurisdictionResponse]:
    normalized_query = query.strip()

    if len(normalized_query) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The jurisdiction search must contain at least two characters.",
        )

    try:
        jurisdictions = search_jurisdictions(database, normalized_query, limit)
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Jurisdictions could not be searched.",
        ) from error

    return [jurisdiction_response(jurisdiction) for jurisdiction in jurisdictions]


@app.get(
    "/jurisdictions/{jurisdiction_id}/rules",
    response_model=JurisdictionRulesResponse,
)
def read_jurisdiction_rules(
    jurisdiction_id: UUID,
    database: DatabaseSession,
) -> JurisdictionRulesResponse:
    try:
        jurisdiction = get_jurisdiction(database, jurisdiction_id)

        if jurisdiction is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The recycling jurisdiction could not be found.",
            )

        rules = get_disposal_rules(database, jurisdiction_id)
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Disposal rules could not be loaded.",
        ) from error

    return JurisdictionRulesResponse(
        jurisdiction=jurisdiction_response(jurisdiction),
        coverage_status="available" if rules else "unavailable",
        rules=[disposal_rule_response(rule) for rule in rules],
    )


@app.post(
    "/classify",
    response_model=ScanResponse,
    status_code=status.HTTP_201_CREATED,
)
def classify_uploaded_image(
    file: UploadedImage,
    database: DatabaseSession,
    jurisdiction_id: SelectedJurisdiction = None,
) -> ScanResponse:
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only JPEG, PNG, and WebP images are supported.",
        )

    if jurisdiction_id is not None:
        try:
            jurisdiction = get_jurisdiction(database, jurisdiction_id)
        except SQLAlchemyError as error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="The recycling jurisdiction could not be checked.",
            ) from error

        if jurisdiction is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Select an active recycling jurisdiction.",
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
        jurisdiction_id=jurisdiction_id,
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
        jurisdiction_id=scan.jurisdiction_id,
    )


@app.patch(
    "/scans/{scan_id}/confirmation",
    response_model=ScanConfirmationResponse,
)
def confirm_scan_prediction(
    scan_id: UUID,
    confirmation: ScanConfirmationRequest,
    database: DatabaseSession,
) -> ScanConfirmationResponse:
    scan = database.get(Scan, scan_id)

    if scan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The scan could not be found.",
        )

    confirmed_label = confirmation.confirmed_label.strip()
    prediction_labels = {
        str(prediction["label"])
        for prediction in scan.predictions
        if isinstance(prediction, dict) and "label" in prediction
    }

    if confirmed_label not in prediction_labels:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The confirmed label must be one of the scan predictions.",
        )

    scan.confirmed_label = confirmed_label

    try:
        database.commit()
    except SQLAlchemyError as error:
        database.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The scan confirmation could not be saved.",
        ) from error

    return ScanConfirmationResponse(
        scan_id=scan.id,
        confirmed_label=scan.confirmed_label,
    )
