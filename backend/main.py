"""
FastAPI Server Application for OnCallMemory.
Provides API endpoints for alert diagnosis, side-by-side evaluation,
incident resolution retention, pattern reflection, and seed data access.
"""

import json
from pathlib import Path
from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.agent import agent
from backend.memory import memory_engine
from backend.schemas import (
    AnalysisRequest,
    DiagnosisResult,
    CompareAnalysisRequest,
    CompareAnalysisResponse,
    ResolveIncidentRequest,
    PatternsRequest,
    PatternsResponse,
    MemoryStats,
    HindsightCallLog
)
from data.seed_memory import seed_memory

app = FastAPI(
    title="OnCallMemory API",
    description="Incident Response Agent powered by Hindsight Persistent Memory Layer",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    """Service health check endpoint."""
    return {
        "status": "healthy",
        "hindsight_base_url": settings.HINDSIGHT_BASE_URL,
        "default_bank_id": settings.DEFAULT_BANK_ID,
        "llm_model": settings.GROQ_MODEL
    }


@app.post("/api/analyze", response_model=DiagnosisResult)
def analyze_alert_endpoint(req: AnalysisRequest):
    """Diagnoses a production alert with Memory ON or Memory OFF."""
    try:
        result = agent.analyze_alert(
            alert_text=req.alert_text,
            service=req.service,
            bank_id=req.bank_id,
            memory_on=req.memory_on
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze alert: {str(e)}")


@app.post("/api/compare", response_model=CompareAnalysisResponse)
def compare_alert_endpoint(req: CompareAnalysisRequest):
    """Executes side-by-side analysis: Memory OFF vs Memory ON."""
    try:
        result = agent.compare_alert(
            alert_text=req.alert_text,
            service=req.service,
            bank_id=req.bank_id
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compare alert: {str(e)}")


@app.post("/api/resolve")
def resolve_incident_endpoint(req: ResolveIncidentRequest):
    """Retains a newly resolved incident and its outcome feedback into Hindsight memory."""
    try:
        incident_data = {
            "service": req.service,
            "severity": req.severity,
            "alert_text": req.alert_text,
            "root_cause": req.root_cause,
            "fix_steps": req.fix_steps,
            "runbook_used": req.runbook_used,
            "engineer_name": req.engineer_name,
            "time_to_resolve_minutes": req.time_to_resolve_minutes,
            "postmortem_note": req.postmortem_note,
            "timestamp": "2026-09-28T22:00:00Z"
        }
        
        call_log = memory_engine.retain_incident(
            bank_id=req.bank_id,
            incident=incident_data,
            worked=req.worked
        )
        new_stats = memory_engine.get_memory_stats(req.bank_id)
        
        return {
            "status": "success",
            "message": "Incident and outcome feedback retained in Hindsight memory.",
            "total_incidents": new_stats,
            "hindsight_log": call_log
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retain incident: {str(e)}")


@app.post("/api/patterns", response_model=PatternsResponse)
def reflect_patterns_endpoint(req: PatternsRequest):
    """Calls Hindsight reflect to discover recurring failure patterns."""
    try:
        insights, based_on, call_log = memory_engine.reflect_patterns(
            bank_id=req.bank_id,
            query=req.question
        )
        return PatternsResponse(
            insights=insights,
            based_on=based_on,
            hindsight_log=call_log
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pattern analysis failed: {str(e)}")


@app.post("/api/seed")
def seed_memory_endpoint(bank_id: str = settings.DEFAULT_BANK_ID):
    """Triggers memory seeding from data/incidents.json into Hindsight."""
    try:
        result = seed_memory(bank_id=bank_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Seeding failed: {str(e)}")


@app.get("/api/demo-alerts")
def get_demo_alerts():
    """Returns the 3 pre-scripted demo alerts for UI one-click loading."""
    demo_file = Path(__file__).resolve().parent.parent / "data" / "demo_alerts.json"
    if not demo_file.exists():
        raise HTTPException(status_code=404, detail="demo_alerts.json file not found")
    with open(demo_file, "r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/stats")
def get_stats(bank_id: str = settings.DEFAULT_BANK_ID):
    """Returns memory bank stats and telemetry call logs."""
    count = memory_engine.get_memory_stats(bank_id)
    return {
        "bank_id": bank_id,
        "total_incidents": count,
        "recent_call_logs": [log.model_dump() for log in memory_engine.call_logs[-10:]]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=True)
