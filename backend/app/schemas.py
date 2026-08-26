from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, field_validator

ScanType = Literal['URL', 'Email', 'Message']
Severity = Literal['high', 'medium', 'low']
Verdict = Literal['Safe', 'Caution', 'High risk']

class AnalyzeRequest(BaseModel):
    content: str = Field(min_length=1, max_length=50_000)
    scan_type: ScanType = Field(alias='type')
    save_result: bool = True

    @field_validator('content')
    @classmethod
    def strip_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError('Content cannot be blank')
        return value

class Finding(BaseModel):
    rule_id: str
    label: str
    detail: str
    severity: Severity
    evidence: str | None = None
    recommendation: str

class Analysis(BaseModel):
    id: str
    score: int = Field(ge=0, le=100)
    verdict: Verdict
    summary: str
    scan_type: ScanType = Field(serialization_alias='type')
    findings: list[Finding]
    confidence: int = Field(ge=0, le=100)
    created_at: datetime
    engine: str

class HistoryItem(BaseModel):
    id: str
    preview: str
    scan_type: ScanType = Field(serialization_alias='type')
    score: int
    verdict: Verdict
    created_at: datetime

class Stats(BaseModel):
    total_scans: int
    high_risk: int
    caution: int
    safe: int
    average_score: float

class TestCase(BaseModel):
    id: str
    title: str
    scan_type: ScanType = Field(serialization_alias='type')
    content: str
    expected_verdict: Verdict
    tags: list[str]

class ReportRequest(BaseModel):
    content: str = Field(min_length=1, max_length=50_000)
    reason: Literal['missed_scam', 'false_positive', 'other']
    notes: str | None = Field(default=None, max_length=2_000)
