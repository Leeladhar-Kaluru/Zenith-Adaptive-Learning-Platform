import os
import re
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def test_dexie_schema_v3_structure():
    """Feature 22: Dexie v3 offline storage schema defines core tables with owner isolation."""
    # 1. Read real Dexie schema implementation from frontend/src/db/indexedDB.ts
    indexed_db_path = os.path.join(PROJECT_ROOT, "frontend", "src", "db", "indexedDB.ts")
    assert os.path.exists(indexed_db_path), f"indexedDB.ts not found at {indexed_db_path}"
    with open(indexed_db_path, "r", encoding="utf-8") as f:
        idb_source = f.read()

    # Verify SetuDatabase class and database name
    assert "class SetuDatabase extends Dexie" in idb_source
    assert "super('SetuDeskDB')" in idb_source

    # Verify Dexie version 3 declaration and stores
    assert "this.version(3).stores({" in idb_source

    # Extract version 3 stores block
    v3_match = re.search(r"this\.version\(3\)\.stores\(\{([\s\S]*?)\}\);", idb_source)
    assert v3_match is not None, "Dexie version(3).stores({...}) definition must be present"
    v3_block = v3_match.group(1)

    # Assert expected store names are present in Dexie v3
    expected_stores = [
        "lessons",
        "offline_resources",
        "offlineVisuals",
        "offlineAttempts",
        "doubtOutbox",
        "cachedAnswers",
        "syncEvents"
    ]
    for store in expected_stores:
        assert f"{store}:" in v3_block, f"Store '{store}' must be defined in Dexie v3 schema"

    # Assert tenant isolation index 'ownerId' is present on user-scoped stores
    assert "ownerId" in v3_block
    assert "offline_resources: 'lessonId, ownerId" in v3_block
    assert "offlineAttempts: 'clientAttemptId, ownerId" in v3_block
    assert "doubtOutbox: 'clientDoubtId, ownerId" in v3_block


def test_sources_page_upload_flow_preservation(client):
    """Feature 22: The original textbook upload flow and Rule 10 privacy guarantee are preserved under /sources."""
    # 1. Inspect real SourcesPage.tsx implementation from disk
    sources_page_path = os.path.join(PROJECT_ROOT, "frontend", "src", "pages", "SourcesPage.tsx")
    assert os.path.exists(sources_page_path), f"SourcesPage.tsx not found at {sources_page_path}"
    with open(sources_page_path, "r", encoding="utf-8") as f:
        sources_source = f.read()

    # Verify upload workflow integrations
    assert "api.uploadDocument" in sources_source
    assert "api.getDocumentStatus" in sources_source
    assert "api.createLearningPath" in sources_source
    assert "AddSourcePanel" in sources_source
    assert "PlanReviewDialog" in sources_source

    # Verify pipeline steps: Upload -> Extract -> Index -> Ready
    assert "{ id: '1', label: 'Upload' }" in sources_source
    assert "{ id: '2', label: 'Extract Text' }" in sources_source
    assert "{ id: '3', label: 'Index & Chunk' }" in sources_source
    assert "{ id: '4', label: 'Ready for Review' }" in sources_source

    # Verify Rule 10 Privacy Guarantee banner
    assert "Rule 10 Privacy Guarantee" in sources_source
    assert "Your uploaded textbooks and private study notes remain strictly confidential." in sources_source
    assert "No unauthorized rehosting." in sources_source

    # 2. Verify backend root endpoint and health reporting
    res = client.get("/")
    assert res.status_code == 200
    root_data = res.json()
    assert "healthUrl" in root_data

    health_res = client.get("/api/v1/health")
    assert health_res.status_code == 200
    health_data = health_res.json()
    assert health_data.get("components", {}).get("storage", {}).get("bucket") == "setu-documents"


def test_textbook_ingestion_coexists_with_curriculum(client):
    """Feature 22: Uploaded documents do not overwrite or conflict with curriculum library."""
    # 1. Inspect real document model for uploaded textbooks in backend/app/models/documents.py
    doc_model_path = os.path.join(PROJECT_ROOT, "backend", "app", "models", "documents.py")
    assert os.path.exists(doc_model_path), f"documents.py model not found at {doc_model_path}"
    with open(doc_model_path, "r", encoding="utf-8") as f:
        doc_source = f.read()

    assert "class Document(Base):" in doc_source
    assert '__tablename__ = "documents"' in doc_source
    assert 'source_mode = Column(String(50), default="upload")' in doc_source
    assert 'storage_bucket = Column(String(100), default="setu-documents")' in doc_source

    # 2. Inspect real library models in backend/app/models/library.py
    library_model_path = os.path.join(PROJECT_ROOT, "backend", "app", "models", "library.py")
    assert os.path.exists(library_model_path), f"library.py model not found at {library_model_path}"
    with open(library_model_path, "r", encoding="utf-8") as f:
        lib_source = f.read()

    assert "class Concept(Base):" in lib_source
    assert "class LibraryEnrollment(Base):" in lib_source
    assert "class ResourceProgress(Base):" in lib_source

    # 3. Query live curriculum catalogue API
    cat_res = client.get("/api/v1/library/catalogue")
    assert cat_res.status_code == 200
    library_chapters = cat_res.json()["chapters"]
    assert len(library_chapters) >= 4

    # All curriculum chapters are tagged as CBSE Mathematics Class 10
    for ch in library_chapters:
        assert ch["board"] == "cbse"
        assert ch["class"] == "10"
        assert ch["subject"] == "mathematics"
        assert ch["status"] == "published"


def test_offline_doubts_and_attempts_queue_schema():
    """Feature 22: Offline doubts and attempts outbox schemas enforce serialization and retry lifecycle."""
    # 1. Inspect real indexedDB.ts schema interfaces and queue methods
    indexed_db_path = os.path.join(PROJECT_ROOT, "frontend", "src", "db", "indexedDB.ts")
    with open(indexed_db_path, "r", encoding="utf-8") as f:
        idb_source = f.read()

    # Verify OfflineDoubt interface
    assert "export interface OfflineDoubt" in idb_source
    assert "clientDoubtId: string;" in idb_source
    assert "ownerId: string;" in idb_source
    assert "questionText: string;" in idb_source
    assert "status: 'queued' | 'syncing' | 'answered' | 'failed' | 'needs_retry' | 'rejected';" in idb_source
    assert "synced: boolean;" in idb_source
    assert "answerPayload?:" in idb_source

    # Verify OfflineAttempt interface
    assert "export interface OfflineAttempt" in idb_source
    assert "clientAttemptId: string;" in idb_source
    assert "questionKey: string;" in idb_source
    assert "hintLevel: number;" in idb_source
    assert "hintsUsed: string[];" in idb_source
    assert "synced: boolean;" in idb_source

    # Verify queueing functions require ownerId
    assert "export async function queueDoubtOffline" in idb_source
    assert "export async function queuePracticeAttemptOffline" in idb_source
    assert "requireOwnerId(params.ownerId);" in idb_source

    # 2. Inspect real syncManager.ts sync payload serialization
    sync_manager_path = os.path.join(PROJECT_ROOT, "frontend", "src", "services", "syncManager.ts")
    assert os.path.exists(sync_manager_path), f"syncManager.ts not found at {sync_manager_path}"
    with open(sync_manager_path, "r", encoding="utf-8") as f:
        sync_source = f.read()

    assert "class SyncManager" in sync_source
    assert "public async syncPendingData()" in sync_source
    assert "${API_BASE}/sync/doubts" in sync_source
    assert "${API_BASE}/practice/submit" in sync_source
    assert "sync_idempotency_key: attempt.clientAttemptId" in sync_source
    assert "status: 'answered'" in sync_source


def test_tenant_isolated_cache_purging_on_account_switch():
    """Feature 22: Switching accounts or logging out purges previous student's offline cache."""
    # 1. Inspect clearOfflineData in indexedDB.ts
    indexed_db_path = os.path.join(PROJECT_ROOT, "frontend", "src", "db", "indexedDB.ts")
    with open(indexed_db_path, "r", encoding="utf-8") as f:
        idb_source = f.read()

    assert "export async function clearOfflineData(): Promise<void>" in idb_source
    assert "db.lessons.clear()" in idb_source
    assert "db.offlineAttempts.clear()" in idb_source
    assert "db.doubtOutbox.clear()" in idb_source
    assert "db.syncEvents.clear()" in idb_source

    # 2. Inspect account switch detection in AuthContext.tsx
    auth_context_path = os.path.join(PROJECT_ROOT, "frontend", "src", "context", "AuthContext.tsx")
    assert os.path.exists(auth_context_path), f"AuthContext.tsx not found at {auth_context_path}"
    with open(auth_context_path, "r", encoding="utf-8") as f:
        auth_source = f.read()

    # Verify that account switch detects mismatch and purges offline cache
    assert "const active = getActiveUserId();" in auth_source
    assert "if (active && active !== profile.id) {" in auth_source
    assert "await clearOfflineData();" in auth_source
    assert "setActiveUserId(profile.id);" in auth_source

    # Verify logout clears offline cache and active user
    assert "const logout = async () => {" in auth_source
    assert "clearActiveUserId();" in auth_source

    # 3. Inspect session storage tracking in session.ts
    session_path = os.path.join(PROJECT_ROOT, "frontend", "src", "services", "session.ts")
    assert os.path.exists(session_path)
    with open(session_path, "r", encoding="utf-8") as f:
        session_source = f.read()

    assert "ACTIVE_USER_KEY = 'setu_active_user_id';" in session_source
    assert "export function getActiveUserId(): string | null" in session_source
    assert "export function clearActiveUserId(): void" in session_source
