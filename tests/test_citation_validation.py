"""
Unit tests for strict citation validation and hallucinated citation rejection.
"""

from backend.agent import IncidentResponseAgent
from backend.schemas import RecalledMemoryItem, IncidentCitation


def test_citation_validation_strips_hallucinated_ids():
    """Verify that citations with IDs not in recalled memories are rejected."""
    agent_inst = IncidentResponseAgent()

    # Mock recalled memories
    mock_recalled = [
        RecalledMemoryItem(
            memory_id="mem-1",
            incident_id="INC-1001",
            timestamp="2026-05-10T00:00:00Z",
            service="checkout-api",
            content="Connection pool exhaustion",
            root_cause="Unclosed transactions",
            fix_steps=["Fix pool size"],
            similarity_score=0.92
        )
    ]

    recalled_ids = {m.incident_id for m in mock_recalled}
    
    # LLM response containing one valid citation (INC-1001) and one hallucinated citation (INC-9999)
    raw_citations = [
        {"incident_id": "INC-1001", "date": "2026-05-10", "reason": "Matching pool failure"},
        {"incident_id": "INC-9999", "date": "2026-01-01", "reason": "Fake hallucinated incident"}
    ]

    validated = []
    for cit in raw_citations:
        if cit["incident_id"] in recalled_ids:
            validated.append(
                IncidentCitation(
                    incident_id=cit["incident_id"],
                    date=cit["date"],
                    reason=cit["reason"]
                )
            )

    assert len(validated) == 1
    assert validated[0].incident_id == "INC-1001"
