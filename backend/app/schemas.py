from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class PredictionResponse(BaseModel):
    label: str
    score: float = Field(ge=0.0, le=1.0)


class ScanResponse(BaseModel):
    scan_id: UUID
    created_at: datetime
    model_id: str
    top_prediction: PredictionResponse
    alternatives: list[PredictionResponse]
    disposal_status: Literal["local_rules_not_checked"] = "local_rules_not_checked"


class ScanConfirmationRequest(BaseModel):
    confirmed_label: str = Field(min_length=1, max_length=255)


class ScanConfirmationResponse(BaseModel):
    scan_id: UUID
    confirmed_label: str
