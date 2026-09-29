"""
Unit tests for Incident Response Agent orchestrator (backend/agent.py).
"""

import pytest
from backend.agent import agent
from backend.schemas import DiagnosisResult


def test_agent_memory_on_mode():
    """Test agent analysis with Memory ON produces citations grounded in memory."""
    result = agent.analyze_alert(
        alert_text="checkout-api latency spike p99 9200ms HikariPool connection timeout",
        service="checkout-api",
        bank_id="oncall-incidents-team-alpha",
        memory_on=True
    )

    assert isinstance(result, DiagnosisResult)
    assert result.memory_enabled is True
    assert len(result.recalled_memories) > 0
    assert result.confidence > 0.70
    assert len(result.citations) >= 1
    assert "INC-" in result.citations[0].incident_id


def test_agent_memory_off_mode():
    """Test agent analysis with Memory OFF produces generic advice without citations."""
    result = agent.analyze_alert(
        alert_text="checkout-api latency spike p99 9200ms HikariPool connection timeout",
        service="checkout-api",
        bank_id="oncall-incidents-team-alpha",
        memory_on=False
    )

    assert isinstance(result, DiagnosisResult)
    assert result.memory_enabled is False
    assert len(result.recalled_memories) == 0
    assert len(result.citations) == 0


def test_agent_empty_memory_case():
    """Test agent behavior when memory has no relevant past incident (Demo 3)."""
    result = agent.analyze_alert(
        alert_text="Corrupted GeoIP database file /var/data/GeoIP2-City.mmdb unreadable",
        service="auth-service",
        bank_id="oncall-incidents-team-alpha",
        memory_on=True
    )

    assert isinstance(result, DiagnosisResult)
    # Citations should be empty or explicitly match recalled items
    recalled_ids = {m.incident_id for m in result.recalled_memories}
    for cit in result.citations:
        assert cit.incident_id in recalled_ids, "Citation ID must exist in recalled memories set"


def test_agent_compare_mode():
    """Test agent side-by-side comparison mode."""
    compare_res = agent.compare_alert(
        alert_text="payments-gateway pod crashloop OOMKilled exit status 137",
        service="payments-gateway",
        bank_id="oncall-incidents-team-alpha"
    )

    assert compare_res.memory_off.memory_enabled is False
    assert compare_res.memory_on.memory_enabled is True
    assert len(compare_res.memory_off.citations) == 0
    assert len(compare_res.memory_on.recalled_memories) > 0
