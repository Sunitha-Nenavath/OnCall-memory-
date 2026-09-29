"""
Pydantic schemas for OnCallMemory request/response data validation.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class AlertInput(BaseModel):
    """Input payload for a incoming production alert."""

    alert_id: Optional[str] = Field(None, description="Optional unique alert ID")
    title: str = Field(..., description="Alert title or headline")
    service: str = Field(..., description="Affected service name, e.g. checkout-api")
    severity: str = Field("SEV2", description="Severity level: SEV1, SEV2, or SEV3")
    alert_text: str = Field(..., description="Full raw alert body including logs and metrics")


class IncidentRecord(BaseModel):
    """Full historical or newly resolved incident data model."""

    id: str = Field(..., description="Incident ID, e.g. INC-1024")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    service: str = Field(..., description="Service name")
    severity: str = Field(..., description="SEV1, SEV2, SEV3")
    alert_text: str = Field(..., description="Original alert description and log output")
    root_cause: str = Field(..., description="Detailed root cause explanation")
    fix_steps: List[str] = Field(default_factory=list, description="Remediation steps taken")
    runbook_used: Optional[str] = Field(None, description="URL or name of runbook used")
    engineer_name: str = Field("OnCall Engineer", description="Engineer who resolved it")
    time_to_resolve_minutes: int = Field(..., description="Total resolution duration in minutes")
    postmortem_note: Optional[str] = Field(None, description="Short postmortem takeaway")
    was_fix_effective: Optional[bool] = Field(True, description="Whether the fix worked effectively")


class RecalledMemoryItem(BaseModel):
    """Parsed memory item returned from Hindsight Recall."""

    memory_id: str
    incident_id: str
    timestamp: str
    service: str
    content: str
    root_cause: str
    fix_steps: List[str]
    similarity_score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class HindsightCallLog(BaseModel):
    """Log record of a Hindsight API execution for UI visibility."""

    operation: str  # 'retain', 'recall', or 'reflect'
    bank_id: str
    query_or_content: str
    num_results: int
    latency_ms: float
    status: str = "success"
    details: Optional[str] = None


class IncidentCitation(BaseModel):
    """Citation linking a recommendation to a past incident."""

    incident_id: str
    date: str
    reason: str


class DiagnosisResult(BaseModel):
    """Structured output returned by the Incident Response Agent."""

    likely_root_cause: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    remediation_steps: List[str]
    citations: List[IncidentCitation] = Field(default_factory=list)
    raw_response: str
    recalled_memories: List[RecalledMemoryItem] = Field(default_factory=list)
    hindsight_log: Optional[HindsightCallLog] = None
    memory_enabled: bool = True


class AnalysisRequest(BaseModel):
    """Request payload for diagnosing an alert."""

    alert_text: str
    service: str = "unknown-service"
    bank_id: str = "oncall-incidents-team-alpha"
    memory_on: bool = True


class CompareAnalysisRequest(BaseModel):
    """Request payload for side-by-side comparison mode."""

    alert_text: str
    service: str = "unknown-service"
    bank_id: str = "oncall-incidents-team-alpha"


class CompareAnalysisResponse(BaseModel):
    """Side-by-side response comparing Memory OFF vs Memory ON."""

    memory_off: DiagnosisResult
    memory_on: DiagnosisResult


class ResolveIncidentRequest(BaseModel):
    """Payload to record resolution of an active incident into Hindsight memory."""

    bank_id: str = "oncall-incidents-team-alpha"
    service: str
    severity: str = "SEV2"
    alert_text: str
    root_cause: str
    fix_steps: List[str]
    runbook_used: Optional[str] = "http://runbooks/standard-triage"
    engineer_name: str = "OnCall Engineer"
    time_to_resolve_minutes: int = 30
    postmortem_note: Optional[str] = ""
    worked: bool = True


class PatternsRequest(BaseModel):
    """Request payload for Hindsight reflect patterns feature."""

    bank_id: str = "oncall-incidents-team-alpha"
    question: str = "What are the most frequent root causes and risky deployment patterns across past incidents?"


class PatternsResponse(BaseModel):
    """Result from Hindsight reflect pattern analysis."""

    insights: str
    based_on: List[Dict[str, Any]] = Field(default_factory=list)
    hindsight_log: Optional[HindsightCallLog] = None


class MemoryStats(BaseModel):
    """Stats summary for a memory bank."""

    bank_id: str
    total_incidents: int
    last_updated: Optional[str] = None
