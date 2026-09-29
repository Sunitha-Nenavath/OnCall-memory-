"""
Incident Response Agent Orchestrator for OnCallMemory.
Coordinates Hindsight memory retrieval, prompt construction, LLM diagnosis,
citation validation, and side-by-side Memory ON vs Memory OFF evaluations.
"""

import logging
from typing import List, Dict, Any, Optional

from backend.memory import memory_engine
from backend.llm import llm_client
from backend.schemas import (
    DiagnosisResult,
    RecalledMemoryItem,
    IncidentCitation,
    HindsightCallLog,
    CompareAnalysisResponse
)

logger = logging.getLogger(__name__)


SYSTEM_PROMPT_MEMORY_ON = """
You are an expert Senior Site Reliability Engineer (SRE) and Incident Response Agent named OnCallMemory.
Your primary role is to diagnose production alerts and provide actionable, grounded step-by-step remediation plans.

CRITICAL GROUNDING RULES:
1. You are provided with past incident memories recalled from Hindsight memory.
2. Ground your diagnosis and remediation steps directly on those recalled incidents.
3. For every remediation suggestion or root cause hypothesis derived from a past incident, you MUST include a citation listing the exact past `incident_id` (e.g. INC-1001) and the reason.
4. DO NOT invent or hallucinate incident IDs that are not present in the recalled past incidents list.
5. If the recalled memories list is empty or completely irrelevant to the alert, explicitly state: "No relevant past incidents were found in Hindsight memory." Do NOT fabricate past incidents.

Return your response strictly in valid JSON format with this schema:
{
  "likely_root_cause": "Clear concise root cause explanation",
  "confidence": float between 0.0 and 1.0,
  "remediation_steps": ["Step 1", "Step 2", "Step 3"],
  "citations": [
    {
      "incident_id": "INC-XXXX",
      "date": "YYYY-MM-DD",
      "reason": "Why this past incident applies to the current alert"
    }
  ],
  "raw_explanation": "Detailed grounding narrative explaining how recalled memories informed this diagnosis."
}
"""

SYSTEM_PROMPT_MEMORY_OFF = """
You are an expert Senior Site Reliability Engineer (SRE) and Incident Response Agent named OnCallMemory.
You are currently running in **Memory OFF** mode (Generic Advice Only).

RULES:
1. You do NOT have access to past incident history or corporate memory banks.
2. Provide standard, generic, best-practice SRE troubleshooting advice.
3. Do NOT cite any incident IDs (citations array MUST be empty).

Return your response strictly in valid JSON format with this schema:
{
  "likely_root_cause": "Generic root cause hypothesis",
  "confidence": float between 0.3 and 0.6,
  "remediation_steps": ["Generic Step 1", "Generic Step 2", "Generic Step 3"],
  "citations": [],
  "raw_explanation": "Memory OFF mode: Generic operational troubleshooting recommendations."
}
"""


class IncidentResponseAgent:
    """
    Agent orchestrator running alert triage with optional Hindsight memory grounding.
    """

    def __init__(self):
        self.memory = memory_engine
        self.llm = llm_client

    def analyze_alert(
        self,
        alert_text: str,
        service: str = "unknown-service",
        bank_id: str = "oncall-incidents-team-alpha",
        memory_on: bool = True
    ) -> DiagnosisResult:
        """
        Main entry point to analyze an alert with Memory ON or Memory OFF.
        """
        recalled_memories: List[RecalledMemoryItem] = []
        call_log: Optional[HindsightCallLog] = None

        if memory_on:
            # 1. Recall similar past incidents from Hindsight memory
            recalled_memories, call_log = self.memory.recall_similar(
                bank_id=bank_id,
                query=alert_text,
                top_k=3
            )

            # Format recalled context for LLM prompt
            if recalled_memories:
                memory_str_list = []
                for idx, mem in enumerate(recalled_memories, start=1):
                    memory_str_list.append(
                        f"--- RECALLED INCIDENT #{idx} ---\n"
                        f"ID: {mem.incident_id}\n"
                        f"Date: {mem.timestamp}\n"
                        f"Service: {mem.service}\n"
                        f"Similarity Score: {mem.similarity_score}\n"
                        f"Symptoms/Logs: {mem.content[:300]}\n"
                        f"Past Root Cause: {mem.root_cause}\n"
                        f"Past Fix Steps: {', '.join(mem.fix_steps)}\n"
                        f"Engineer Notes: {mem.metadata.get('postmortem_note', 'N/A')}\n"
                    )
                recalled_context = "\n\n".join(memory_str_list)
            else:
                recalled_context = "NO RELEVANT PAST INCIDENTS FOUND IN HINDSIGHT MEMORY."

            user_prompt = (
                f"CURRENT PRODUCTION ALERT:\n"
                f"Service: {service}\n"
                f"Alert Body:\n{alert_text}\n\n"
                f"RECALLED PAST INCIDENTS FROM HINDSIGHT MEMORY:\n{recalled_context}\n\n"
                f"Diagnose the root cause, provide ordered remediation steps, and cite past incidents."
            )

            raw_json = self.llm.generate_json(
                system_prompt=SYSTEM_PROMPT_MEMORY_ON,
                user_prompt=user_prompt,
                temperature=0.2
            )

            # 2. Strict Citation Validation against recalled memory set
            recalled_incident_ids = {m.incident_id for m in recalled_memories}
            validated_citations: List[IncidentCitation] = []

            for cit_data in raw_json.get("citations", []):
                if isinstance(cit_data, dict):
                    inc_id = cit_data.get("incident_id")
                    if inc_id in recalled_incident_ids:
                        validated_citations.append(
                            IncidentCitation(
                                incident_id=inc_id,
                                date=cit_data.get("date", "2026-05-15"),
                                reason=cit_data.get("reason", "Recalled matching failure pattern")
                            )
                        )
                    else:
                        logger.warning(f"Rejected hallucinated citation ID: {inc_id}")

            return DiagnosisResult(
                likely_root_cause=raw_json.get("likely_root_cause", "Unspecified root cause"),
                confidence=float(raw_json.get("confidence", 0.85)),
                remediation_steps=raw_json.get("remediation_steps", ["Inspect service logs"]),
                citations=validated_citations,
                raw_response=raw_json.get("raw_explanation", ""),
                recalled_memories=recalled_memories,
                hindsight_log=call_log,
                memory_enabled=True
            )

        else:
            # Memory OFF Mode
            user_prompt = (
                f"CURRENT PRODUCTION ALERT:\n"
                f"Service: {service}\n"
                f"Alert Body:\n{alert_text}\n\n"
                f"Provide generic SRE troubleshooting advice without using past memory."
            )

            raw_json = self.llm.generate_json(
                system_prompt=SYSTEM_PROMPT_MEMORY_OFF,
                user_prompt=user_prompt,
                temperature=0.3
            )

            dummy_log = HindsightCallLog(
                operation="recall",
                bank_id=bank_id,
                query_or_content="[Memory OFF - Hindsight bypassed]",
                num_results=0,
                latency_ms=0.0,
                status="bypassed"
            )

            return DiagnosisResult(
                likely_root_cause=raw_json.get("likely_root_cause", "Generic system degradation"),
                confidence=float(raw_json.get("confidence", 0.45)),
                remediation_steps=raw_json.get("remediation_steps", ["Check server metrics", "Review logs"]),
                citations=[],
                raw_response=raw_json.get("raw_explanation", "Memory OFF mode: Generic advice provided."),
                recalled_memories=[],
                hindsight_log=dummy_log,
                memory_enabled=False
            )

    def compare_alert(
        self,
        alert_text: str,
        service: str = "unknown-service",
        bank_id: str = "oncall-incidents-team-alpha"
    ) -> CompareAnalysisResponse:
        """
        Executes alert analysis twice: Memory OFF vs Memory ON for side-by-side comparison.
        """
        mem_off_res = self.analyze_alert(
            alert_text=alert_text,
            service=service,
            bank_id=bank_id,
            memory_on=False
        )
        mem_on_res = self.analyze_alert(
            alert_text=alert_text,
            service=service,
            bank_id=bank_id,
            memory_on=True
        )
        return CompareAnalysisResponse(
            memory_off=mem_off_res,
            memory_on=mem_on_res
        )


agent = IncidentResponseAgent()
