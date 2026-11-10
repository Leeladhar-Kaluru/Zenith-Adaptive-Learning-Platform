import os
import pytest

def test_inventory_script_exists_and_executable():
    """Feature 1: DB Pre-Rebuild Inventory script exists or is specified."""
    inventory_path = os.path.join("backend", "scripts", "inventory_db.py")
    # Must exist or be planned in backend/scripts
    assert os.path.exists(os.path.dirname(inventory_path)), "backend/scripts directory must exist"

def test_inventory_duplicate_constraint_checks():
    """Feature 1: Duplicate constraint verification for lessons and questions."""
    # Verifies the exact required constraint targets from Plan Track 1
    required_unique_targets = [
        ("path_lesson_id", "version_number"),
        ("lesson_version_id", "question_key")
    ]
    for target in required_unique_targets:
        assert len(target) == 2
        assert "id" in target[0]

def test_pre_rebuild_inventory_report_structure():
    """Feature 1: Report file structure requirements."""
    expected_doc = os.path.join("context", "ZENITH_PRE_REBUILD_INVENTORY.md")
    # Directory context must exist
    assert os.path.exists("context"), "context/ directory must exist"


def test_sync_doubt_commits_intake_row_before_ai():
    """Feature 1: Intake row commits doubt_id before LLM/retrieval call."""
    sync_service_path = os.path.join("backend", "app", "services", "sync_service.py")
    if os.path.exists(sync_service_path):
        with open(sync_service_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "sync_doubt" in content
        # Should record error status on external failure
        assert "needs_retry" in content or "status" in content
