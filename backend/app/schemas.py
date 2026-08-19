from datetime import datetime
from enum import StrEnum
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
    jurisdiction_id: UUID | None = None


class ScanConfirmationRequest(BaseModel):
    confirmed_label: str = Field(min_length=1, max_length=255)


class ScanConfirmationResponse(BaseModel):
    scan_id: UUID
    confirmed_label: str


class JurisdictionType(StrEnum):
    STATE = "state"
    COUNTY = "county"
    MUNICIPALITY = "municipality"
    WASTE_PROVIDER = "waste_provider"


class DisposalStatus(StrEnum):
    ACCEPTED_CURBSIDE = "accepted_curbside"
    NOT_ACCEPTED_CURBSIDE = "not_accepted_curbside"
    DROP_OFF_REQUIRED = "drop_off_required"
    UNAVAILABLE_OR_UNCLEAR = "unavailable_or_unclear"


class JurisdictionResponse(BaseModel):
    id: UUID
    slug: str
    name: str
    display_name: str
    jurisdiction_type: JurisdictionType
    country_code: str
    state_code: str | None
    county_name: str | None
    waste_provider: str | None
    parent_id: UUID | None
    postal_codes: list[str]


class DisposalRuleResponse(BaseModel):
    material_key: str
    status: DisposalStatus
    instructions: str | None
    source_title: str
    source_url: str
    verified_at: datetime


class JurisdictionRulesResponse(BaseModel):
    jurisdiction: JurisdictionResponse
    coverage_status: Literal["available", "unavailable"]
    rules: list[DisposalRuleResponse]
