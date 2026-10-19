from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class GeneralDisposalAction(StrEnum):
    REUSE_OR_DONATE = "reuse_or_donate"
    RECYCLE = "recycle"
    COMPOST = "compost"
    SPECIAL_DROP_OFF = "special_drop_off"
    TRASH = "trash"
    CHECK_LOCALLY = "check_locally"


class DisposalStatus(StrEnum):
    ACCEPTED_CURBSIDE = "accepted_curbside"
    NOT_ACCEPTED_CURBSIDE = "not_accepted_curbside"
    DROP_OFF_REQUIRED = "drop_off_required"
    UNAVAILABLE_OR_UNCLEAR = "unavailable_or_unclear"


class PredictionResponse(BaseModel):
    label: str
    score: float = Field(ge=0.0, le=1.0)
    material_key: str | None = None
    material_display_name: str | None = None


class GeneralDisposalGuidanceResponse(BaseModel):
    scope: Literal["general"] = "general"
    material_key: str
    country_code: str
    action: GeneralDisposalAction
    headline: str
    instructions: str
    preparation: str | None
    warning: str | None
    source_title: str
    source_url: str
    verified_at: datetime


class JurisdictionDisposalGuidanceResponse(BaseModel):
    scope: Literal["jurisdiction"] = "jurisdiction"
    material_key: str
    jurisdiction_id: UUID
    status: DisposalStatus
    instructions: str | None
    source_title: str
    source_url: str
    verified_at: datetime


DisposalGuidanceResponse = Annotated[
    GeneralDisposalGuidanceResponse | JurisdictionDisposalGuidanceResponse,
    Field(discriminator="scope"),
]


class ScanResponse(BaseModel):
    scan_id: UUID
    created_at: datetime
    model_id: str
    top_prediction: PredictionResponse
    alternatives: list[PredictionResponse]
    disposal_guidance: DisposalGuidanceResponse | None
    jurisdiction_id: UUID | None = None


class ScanConfirmationRequest(BaseModel):
    confirmed_label: str = Field(min_length=1, max_length=255)


class ScanConfirmationResponse(BaseModel):
    scan_id: UUID
    confirmed_label: str
    confirmed_prediction: PredictionResponse
    disposal_guidance: DisposalGuidanceResponse | None


class JurisdictionType(StrEnum):
    STATE = "state"
    COUNTY = "county"
    MUNICIPALITY = "municipality"
    WASTE_PROVIDER = "waste_provider"


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
