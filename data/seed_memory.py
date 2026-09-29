"""
Memory Seeding Script for OnCallMemory.
Loads synthetic incident records from data/incidents.json into Hindsight memory.
"""

import sys
import json
import time
from pathlib import Path

# Add parent dir to path to import backend modules
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.config import settings

try:
    from hindsight_client import Hindsight
except ImportError:
    Hindsight = None


def format_incident_memory(inc: dict) -> str:
    """Formats an incident dict into a structured memory text representation."""
    fix_str = "\n".join([f"  - {step}" for step in inc.get("fix_steps", [])])
    return (
        f"INCIDENT REPORT [{inc['id']}]\n"
        f"Date: {inc['timestamp']}\n"
        f"Service: {inc['service']}\n"
        f"Severity: {inc['severity']}\n"
        f"Engineer: {inc.get('engineer_name', 'OnCall SRE')}\n"
        f"Resolution Time: {inc.get('time_to_resolve_minutes', 30)} minutes\n"
        f"Alert Symptoms & Logs:\n{inc['alert_text']}\n\n"
        f"Root Cause:\n{inc['root_cause']}\n\n"
        f"Effective Remediation Steps:\n{fix_str}\n\n"
        f"Runbook Reference: {inc.get('runbook_used', 'N/A')}\n"
        f"Postmortem Takeaway: {inc.get('postmortem_note', 'N/A')}\n"
        f"Outcome Feedback: Fix worked effectively."
    )


def seed_memory(bank_id: str = None, json_file: Path = None) -> dict:
    """Seeds incidents from JSON file into Hindsight memory bank."""
    bank_id = bank_id or settings.DEFAULT_BANK_ID
    json_file = json_file or (Path(__file__).resolve().parent / "incidents.json")

    if not json_file.exists():
        raise FileNotFoundError(f"Seed file not found: {json_file}")

    with open(json_file, "r", encoding="utf-8") as f:
        incidents = json.load(f)

    print(f"Loaded {len(incidents)} incidents from {json_file.name}")
    print(f"Connecting to Hindsight at {settings.HINDSIGHT_BASE_URL} for bank: '{bank_id}'...")

    if not Hindsight:
        print("Warning: hindsight-client module is not installed. Unable to seed to Hindsight.")
        return {"retained_count": 0, "status": "failed", "error": "hindsight-client not installed"}

    client = Hindsight(
        base_url=settings.HINDSIGHT_BASE_URL,
        api_key=settings.HINDSIGHT_API_KEY
    )

    retained_count = 0
    errors = 0
    start_time = time.time()

    for idx, inc in enumerate(incidents, start=1):
        content = format_incident_memory(inc)
        metadata = {
            "incident_id": inc["id"],
            "service": inc["service"],
            "severity": inc["severity"],
            "timestamp": inc["timestamp"],
            "time_to_resolve_minutes": str(inc.get("time_to_resolve_minutes", 30))
        }

        try:
            response = client.retain(
                bank_id=bank_id,
                content=content,
                metadata=metadata,
                document_id=inc["id"]
            )
            retained_count += 1
            if idx % 5 == 0 or idx == len(incidents):
                print(f"  [{idx}/{len(incidents)}] Retained {inc['id']} ({inc['service']})")
        except Exception as e:
            errors += 1
            print(f"  [ERROR] Failed to retain {inc['id']}: {e}")

    elapsed = round(time.time() - start_time, 2)
    print(f"\nSeeding complete: {retained_count}/{len(incidents)} incidents retained in {elapsed}s.")
    if errors > 0:
        print(f"Note: {errors} incidents encountered connection or server errors during retention.")

    return {
        "bank_id": bank_id,
        "total_incidents": len(incidents),
        "retained_count": retained_count,
        "errors": errors,
        "elapsed_seconds": elapsed,
        "status": "success" if retained_count > 0 else "failed"
    }


if __name__ == "__main__":
    target_bank = sys.argv[1] if len(sys.argv) > 1 else settings.DEFAULT_BANK_ID
    seed_memory(bank_id=target_bank)
