"""Esquemas Pydantic para validacion de requests/responses."""
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class TelemetryRecordSchema(BaseModel):
    record_id: Optional[str] = None
    kpi_code: str = Field(..., pattern="^(GSPI|SHPD|LTCR|CFBR|UOR)$")
    timestamp: datetime
    raw_value: Decimal = Field(..., decimal_places=4)
    normalized_score: Optional[Decimal] = Field(None, decimal_places=2)
    data_source: Optional[str] = None
    freshness_flag: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class RiskIndexSchema(BaseModel):
    index_id: Optional[str] = None
    timestamp: datetime
    cri_score: Decimal = Field(..., decimal_places=2)
    risk_zone: str = Field(..., pattern="^(LOW|MODERATE|CRITICAL)$")
    alerts_triggered: bool
    component_scores: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

class CalculateCRIResponse(BaseModel):
    status: str
    data: RiskIndexSchema

class IngestRequest(BaseModel):
    records: list

class IngestResponse(BaseModel):
    status: str
    inserted: int
    message: str

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str = "1.0.0"
