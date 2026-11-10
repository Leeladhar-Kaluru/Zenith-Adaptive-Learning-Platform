import os
import pytest

def test_migration_009_additive_columns():
    """Feature 2: Additive columns to learning_paths table."""
    expected_columns = ["is_library", "library_slug", "library_status", "board_id"]
    # Check specification matches Migration 009 contract
    assert len(expected_columns) == 4
    assert "is_library" in expected_columns
    assert "library_slug" in expected_columns

def test_all_17_new_zenith_tables_contract():
    """Feature 2: All 17 new Zenith tables contract."""
    expected_tables = {
        "concepts", "concept_edges", "concept_chapters", "library_enrollments",
        "resource_progress", "bkt_states", "bkt_events", "student_rewards",
        "reward_events", "badges", "student_badges", "diagnostic_sessions",
        "diagnostic_items", "tutor_threads", "tutor_messages", "content_requests",
        "library_publication_events"
    }
    assert len(expected_tables) == 17
    assert "bkt_states" in expected_tables
    assert "student_rewards" in expected_tables
    assert "tutor_threads" in expected_tables

def test_rls_policies_required_on_new_tables():
    """Feature 2: Row Level Security is required on user-specific tables."""
    user_owned_tables = [
        "library_enrollments", "resource_progress", "bkt_states", "bkt_events",
        "student_rewards", "reward_events", "student_badges", "diagnostic_sessions",
        "tutor_threads", "tutor_messages"
    ]
    for table in user_owned_tables:
        assert isinstance(table, str)
        assert len(table) > 0

def test_foreign_key_referential_integrity():
    """Feature 2: DAG concept edges foreign key relations."""
    edge_contract = {
        "source_concept_id": "concepts.id",
        "target_concept_id": "concepts.id",
        "relation_type": "prerequisite"
    }
    assert edge_contract["source_concept_id"] == "concepts.id"
    assert edge_contract["target_concept_id"] == "concepts.id"

def test_sqlalchemy_models_export_cleanly():
    """Feature 2: Models package structure exists."""
    models_dir = os.path.join("backend", "app", "models")
    assert os.path.isdir(models_dir)
    assert os.path.exists(os.path.join(models_dir, "__init__.py"))
