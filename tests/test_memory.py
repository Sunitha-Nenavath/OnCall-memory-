"""
Unit tests for Hindsight Memory Engine wrapper (backend/memory.py).
"""

import pytest
from backend.memory import HindsightMemoryEngine
from backend.schemas import RecalledMemoryItem, HindsightCallLog


def test_memory_engine_fallback_initialization():
    """Test that memory engine initializes local fallback data correctly."""
    engine = HindsightMemoryEngine(base_url="http://localhost:9999")
    stats = engine.get_memory_stats("oncall-incidents-team-alpha")
    assert stats > 0, "Fallback memory bank should contain seed incidents"


def test_memory_engine_recall_similar():
    """Test recall_similar returns relevant memory items and timing logs."""
    engine = HindsightMemoryEngine(base_url="http://localhost:9999")
    items, log = engine.recall_similar(
        bank_id="oncall-incidents-team-alpha",
        query="checkout-api connection pool timeout HikariPool",
        top_k=3
    )

    assert isinstance(items, list)
    assert len(items) > 0
    assert isinstance(log, HindsightCallLog)
    assert log.operation == "recall"
    assert log.latency_ms >= 0.0

    # Top result should match checkout or connection pool scenario
    top_item = items[0]
    assert isinstance(top_item, RecalledMemoryItem)
    assert "INC-" in top_item.incident_id
    assert top_item.similarity_score > 0.0


def test_memory_engine_retain_incident():
    """Test retain_incident adds a new incident to the bank."""
    engine = HindsightMemoryEngine(base_url="http://localhost:9999")
    initial_count = engine.get_memory_stats("test-bank")

    incident_data = {
        "id": "INC-TEST-99",
        "service": "auth-service",
        "severity": "SEV2",
        "alert_text": "Test alert text for memory retain",
        "root_cause": "Test root cause",
        "fix_steps": ["Test fix step 1"],
        "engineer_name": "Test Engineer",
        "time_to_resolve_minutes": 15
    }

    log = engine.retain_incident(
        bank_id="test-bank",
        incident=incident_data,
        worked=True
    )

    assert log.operation == "retain"
    new_count = engine.get_memory_stats("test-bank")
    assert new_count == initial_count + 1


def test_memory_engine_reflect_patterns():
    """Test reflect_patterns generates pattern synthesis."""
    engine = HindsightMemoryEngine(base_url="http://localhost:9999")
    insights, based_on, log = engine.reflect_patterns(
        bank_id="oncall-incidents-team-alpha",
        query="What keeps breaking on Fridays?"
    )

    assert isinstance(insights, str)
    assert len(insights) > 50
    assert log.operation == "reflect"
