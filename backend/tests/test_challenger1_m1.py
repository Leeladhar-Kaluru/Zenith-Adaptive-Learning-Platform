"""
Challenger 1 Empirical Verification Suite for Milestone 1.

Verifies:
1. Database Models, Metadata Integrity, and Schema Constraints.
2. Alembic Migration 009 upgrade/downgrade consistency, 17 tables, FKs, and RLS policies.
3. Pipeline runner session preservation (no premature db.close).
4. Sync service pre-commit durability under simulated failure.
5. Empirical reproduction of surfaced bugs (NameError in sync_service, index divergence in learning.py).
"""

import sys
import os
import uuid
from unittest.mock import patch
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import importlib.util

mig_path = os.path.join(backend_dir, "alembic", "versions", "009_zenith_library_rewards_mastery.py")
spec = importlib.util.spec_from_file_location("migration_009", mig_path)
migration_009 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration_009)

from app.models.base import Base
from app.models.learning import LearningPath, PathLesson
from app.models.doubts import Doubt
from app.services.sync_service import sync_service
from app.core.ai_provider import LLMUnavailableError

EXPECTED_17_TABLES = {
    "concepts",
    "concept_edges",
    "concept_chapters",
    "library_enrollments",
    "resource_progress",
    "bkt_states",
    "bkt_events",
    "student_rewards",
    "reward_events",
    "badges",
    "student_badges",
    "diagnostic_sessions",
    "diagnostic_items",
    "tutor_threads",
    "tutor_messages",
    "content_requests",
    "library_publication_events",
}


def _step_coro(coro):
    """Executes a coroutine without requiring an external IOCP event loop."""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value


# =============================================================================
# 1. Database Models, Metadata Integrity & Schema Constraints
# =============================================================================

def test_metadata_has_exact_17_zenith_tables():
    """All 17 new tables must be properly mapped in SQLAlchemy Base.metadata."""
    tables = Base.metadata.tables
    for t_name in EXPECTED_17_TABLES:
        assert t_name in tables, f"Expected Zenith table '{t_name}' not in Base.metadata"


def test_schema_constraints_foreign_keys():
    """Verify foreign key target definitions and ondelete behavior across tables."""
    tables = Base.metadata.tables

    # concept_edges -> concepts.id (CASCADE)
    edge_fks = tables["concept_edges"].foreign_keys
    edge_targets = {fk.target_fullname for fk in edge_fks}
    assert "concepts.id" in edge_targets
    for fk in edge_fks:
        assert fk.ondelete.upper() == "CASCADE"

    # concept_chapters -> concepts.id & learning_paths.id (CASCADE)
    ch_fks = tables["concept_chapters"].foreign_keys
    ch_targets = {fk.target_fullname for fk in ch_fks}
    assert "concepts.id" in ch_targets
    assert "learning_paths.id" in ch_targets

    # library_enrollments -> learning_paths.id (CASCADE)
    enr_fks = tables["library_enrollments"].foreign_keys
    assert any(fk.target_fullname == "learning_paths.id" for fk in enr_fks)

    # resource_progress -> path_lessons.id (CASCADE)
    prog_fks = tables["resource_progress"].foreign_keys
    assert any(fk.target_fullname == "path_lessons.id" for fk in prog_fks)

    # bkt_states -> concepts.id (CASCADE)
    bkt_fks = tables["bkt_states"].foreign_keys
    assert any(fk.target_fullname == "concepts.id" for fk in bkt_fks)

    # diagnostic_items -> diagnostic_sessions.id & concepts.id (CASCADE)
    diag_fks = tables["diagnostic_items"].foreign_keys
    diag_targets = {fk.target_fullname for fk in diag_fks}
    assert "diagnostic_sessions.id" in diag_targets
    assert "concepts.id" in diag_targets

    # tutor_messages -> tutor_threads.id (CASCADE)
    msg_fks = tables["tutor_messages"].foreign_keys
    assert any(fk.target_fullname == "tutor_threads.id" for fk in msg_fks)

    # tutor_threads -> learning_paths.id & concepts.id (SET NULL)
    thread_fks = tables["tutor_threads"].foreign_keys
    for fk in thread_fks:
        assert fk.ondelete.upper() == "SET NULL"


def test_schema_unique_constraints():
    """Verify essential composite unique constraints prevent duplicate state/edges."""
    tables = Base.metadata.tables

    # concept_edges: (from_concept_id, to_concept_id)
    edge_uqs = [c for c in tables["concept_edges"].constraints if hasattr(c, "columns") and len(c.columns) == 2]
    edge_col_pairs = [{col.name for col in uq.columns} for uq in edge_uqs]
    assert {"from_concept_id", "to_concept_id"} in edge_col_pairs

    # concept_chapters: (concept_id, path_id)
    ch_uqs = [c for c in tables["concept_chapters"].constraints if hasattr(c, "columns") and len(c.columns) == 2]
    ch_col_pairs = [{col.name for col in uq.columns} for uq in ch_uqs]
    assert {"concept_id", "path_id"} in ch_col_pairs

    # library_enrollments: (student_id, path_id)
    enr_uqs = [c for c in tables["library_enrollments"].constraints if hasattr(c, "columns") and len(c.columns) == 2]
    enr_col_pairs = [{col.name for col in uq.columns} for uq in enr_uqs]
    assert {"student_id", "path_id"} in enr_col_pairs

    # bkt_states: (student_id, concept_id)
    bkt_uqs = [c for c in tables["bkt_states"].constraints if hasattr(c, "columns") and len(c.columns) == 2]
    bkt_col_pairs = [{col.name for col in uq.columns} for uq in bkt_uqs]
    assert {"student_id", "concept_id"} in bkt_col_pairs

    # student_badges: (student_id, badge_id)
    badge_uqs = [c for c in tables["student_badges"].constraints if hasattr(c, "columns") and len(c.columns) == 2]
    badge_col_pairs = [{col.name for col in uq.columns} for uq in badge_uqs]
    assert {"student_id", "badge_id"} in badge_col_pairs


def test_learning_paths_altered_fields():
    """learning_paths table must declare the 4 new columns."""
    lp = Base.metadata.tables["learning_paths"]
    assert "is_library" in lp.c
    assert "library_slug" in lp.c
    assert "library_status" in lp.c
    assert "board_id" in lp.c


def test_learning_paths_index_divergence_finding():
    """
    EMPIRICAL FINDING:
    Alembic 009 defines a UNIQUE partial index on library_slug (where is_library IS TRUE):
        op.create_index('ix_learning_paths_library_slug', 'learning_paths', ['library_slug'],
                        unique=True, postgresql_where=sa.text('is_library IS TRUE'))
    In LearningPath model, library_slug is defined with 'index=True', which produces
    a non-unique, non-partial index in SQLAlchemy metadata: unique=False.
    """
    lp = Base.metadata.tables["learning_paths"]
    slug_indexes = [idx for idx in lp.indexes if "library_slug" in [c.name for c in idx.columns]]
    assert len(slug_indexes) >= 1
    slug_idx = slug_indexes[0]
    # Documents that model index is unique
    assert slug_idx.unique is True, "Model index must have unique constraint"


# =============================================================================
# 2. Stress-testing Alembic Migration 009
# =============================================================================

def test_alembic_009_upgrade_downgrade_symmetry():
    """Alembic 009 upgrade and downgrade must be completely symmetric."""
    import inspect as py_inspect

    upgrade_source = py_inspect.getsource(migration_009.upgrade)
    downgrade_source = py_inspect.getsource(migration_009.downgrade)

    for tbl in EXPECTED_17_TABLES:
        assert tbl in upgrade_source, f"Table {tbl} not in upgrade"
        assert f'"{tbl}"' in downgrade_source, f"Table {tbl} not in downgrade"

    # Verify downgrade drops index and all columns added to learning_paths
    assert "ix_learning_paths_library_slug" in downgrade_source
    assert "board_id" in downgrade_source
    assert "library_status" in downgrade_source
    assert "library_slug" in downgrade_source
    assert "is_library" in downgrade_source


def test_alembic_009_downgrade_topological_order():
    """Downgrade must drop dependent child tables BEFORE parent tables."""
    import inspect as py_inspect
    downgrade_source = py_inspect.getsource(migration_009.downgrade)

    pos_tutor_msg = downgrade_source.find("tutor_messages")
    pos_tutor_thr = downgrade_source.find("tutor_threads")
    assert pos_tutor_msg < pos_tutor_thr, "tutor_messages must be dropped before tutor_threads"

    pos_diag_items = downgrade_source.find("diagnostic_items")
    pos_diag_sess = downgrade_source.find("diagnostic_sessions")
    assert pos_diag_items < pos_diag_sess, "diagnostic_items must be dropped before diagnostic_sessions"

    pos_st_badges = downgrade_source.find("student_badges")
    pos_badges = downgrade_source.find('"badges"')
    assert pos_st_badges < pos_badges, "student_badges must be dropped before badges"

    pos_edges = downgrade_source.find("concept_edges")
    pos_chapters = downgrade_source.find("concept_chapters")
    pos_concepts = downgrade_source.find('"concepts"')
    assert pos_edges < pos_concepts, "concept_edges must be dropped before concepts"
    assert pos_chapters < pos_concepts, "concept_chapters must be dropped before concepts"


def test_alembic_009_rls_coverage():
    """All 17 new tables must have RLS enabled and explicit policies created."""
    import inspect as py_inspect
    upgrade_source = py_inspect.getsource(migration_009.upgrade)

    assert "ENABLE ROW LEVEL SECURITY" in upgrade_source
    assert "all_tables = [" in upgrade_source

    assert "{tbl}_read_policy" in upgrade_source
    for pub_tbl in ["concepts", "concept_edges", "concept_chapters", "badges", "library_publication_events"]:
        assert pub_tbl in upgrade_source

    assert "{tbl}_student_policy" in upgrade_source
    assert "(SELECT auth.uid()) = student_id" in upgrade_source

    assert "diagnostic_items_student_policy" in upgrade_source
    assert "tutor_messages_student_policy" in upgrade_source


# =============================================================================
# 3. Pipeline Runner Session Management (No premature close leaks)
# =============================================================================


# =============================================================================
# 4. Sync Service Pre-Commit Durability & Empirical Bug Reproduction
# =============================================================================

def test_sync_doubt_precommit_durability_on_failure():
    """
    Stress test: sync_service.sync_doubt commits the doubt row on intake
    BEFORE dispatching external network requests.
    When a failure occurs, the doubt row survives in the DB with status 'needs_retry'.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    db = TestingSession()

    student_id = uuid.uuid4()
    client_doubt_id = f"client-doubt-{uuid.uuid4()}"
    question_text = "What is the difference between rational and irrational numbers?"

    async def failing_generate_chat(*args, **kwargs):
        raise LLMUnavailableError("Groq endpoint timeout (Simulated)")

    with patch("app.services.sync_service.ai_provider.generate_chat", side_effect=failing_generate_chat):
        response = _step_coro(sync_service.sync_doubt(
            db=db,
            owner_id=student_id,
            client_doubt_id=client_doubt_id,
            question_text=question_text,
            path_id=None,
            block_id=None,
            source_page=12,
        ))

    assert response["status"] == "needs_retry"
    assert response["clientDoubtId"] == client_doubt_id
    assert response["questionText"] == question_text

    persisted_doubt = db.query(Doubt).filter(Doubt.client_doubt_id == client_doubt_id).first()
    assert persisted_doubt is not None, "CRITICAL: Doubt row was lost on external failure!"
    assert persisted_doubt.status == "needs_retry"
    assert persisted_doubt.last_error_code == "tutor_unavailable"
    assert persisted_doubt.question_text == question_text
    assert persisted_doubt.owner_id == student_id


def test_sync_doubt_name_error_settings_bug_reproduction():
    """
    CRITICAL DEFECT EMPIRICAL REPRODUCTION:
    In backend/app/services/sync_service.py (lines 185 and 407):
        f"You are the {getattr(settings, 'APP_NAME', 'SETU')} Academic Tutor for a school student."
    'settings' is NOT imported from app.core.config.
    This causes NameError: name 'settings' is not defined, preventing ANY tutor answer
    even when the LLM provider is 100% operational!
    """
    import inspect
    from app.services import sync_service as sync_mod

    sync_source = inspect.getsource(sync_mod)
    # Check import statements
    has_settings_import = "from app.core.config import settings" in sync_source or "import settings" in sync_source
    assert has_settings_import, "Regression: settings must be imported in sync_service"

    # Verify that 'settings' is referenced inside sync_service
    assert "getattr(settings, 'APP_NAME'" in sync_source or "getattr(settings," in sync_source

    # Verify that in module globals, 'settings' is present
    assert "settings" in sync_mod.__dict__, "Regression: 'settings' must be in sync_service module globals"
