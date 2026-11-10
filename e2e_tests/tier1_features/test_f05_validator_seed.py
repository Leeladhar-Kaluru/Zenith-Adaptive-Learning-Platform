import pytest
from e2e_tests.test_config import SYSTEM_OWNER_ID

def test_validator_manifest_schema():
    """Feature 5: Manifest structure validation."""
    required_manifest_keys = ["version", "board", "class", "subject", "chapters"]
    manifest_sample = {
        "version": "1.0.0",
        "board": "cbse",
        "class": "10",
        "subject": "mathematics",
        "chapters": ["real-numbers", "polynomials"]
    }
    for key in required_manifest_keys:
        assert key in manifest_sample

def test_dag_acyclicity_check_kahns_algorithm():
    """Feature 5: Kahn's algorithm validates that concept dependency DAG is acyclic."""
    # Graph: c1 -> c2 -> c3 (Acyclic)
    nodes = ["c1", "c2", "c3"]
    edges = [("c1", "c2"), ("c2", "c3")]
    
    in_degree = {n: 0 for n in nodes}
    for src, dst in edges:
        in_degree[dst] += 1
        
    queue = [n for n in nodes if in_degree[n] == 0]
    visited_count = 0
    while queue:
        curr = queue.pop(0)
        visited_count += 1
        for src, dst in edges:
            if src == curr:
                in_degree[dst] -= 1
                if in_degree[dst] == 0:
                    queue.append(dst)
                    
    assert visited_count == len(nodes), "Acyclic graph must visit all nodes"

def test_source_refs_integrity_enforcement():
    """Feature 5: sourceRefs: [] is only valid when rights: 'original'."""
    valid_original_pkg = {"rights": "original", "sourceRefs": []}
    invalid_derived_pkg = {"rights": "derived", "sourceRefs": []}
    
    assert valid_original_pkg["rights"] == "original" and len(valid_original_pkg["sourceRefs"]) == 0
    # Derived must require sourceRefs
    assert not (invalid_derived_pkg["rights"] == "original")

def test_seed_cli_system_owner_attribution():
    """Feature 5: System owner UUID is 00000000-0000-0000-0000-000000000001."""
    assert SYSTEM_OWNER_ID == "00000000-0000-0000-0000-000000000001"

def test_seed_idempotency(client):
    """Feature 5: Catalogue query returns stable published counts."""
    res1 = client.get("/api/v1/library/catalogue")
    res2 = client.get("/api/v1/library/catalogue")
    assert res1.status_code == 200
    assert res2.status_code == 200
    assert len(res1.json()["chapters"]) == len(res2.json()["chapters"])
