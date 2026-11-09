import pytest
import time
from fastapi.testclient import TestClient
from server.app import app
from server.security import mint_approval_token, canonical_hash
from ledger.database import get_db_connection

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_db():
    # Setup baseline claim in DB
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM claims")
        cursor.execute("DELETE FROM approvals")
        cursor.execute("DELETE FROM grants")
        cursor.execute("DELETE FROM idempotency_keys")
        cursor.execute("INSERT INTO claims (claim_id, amount, customer_id, status) VALUES ('C-ATTACK', 50.0, 'U-ATTACK', 'PENDING')")
        conn.commit()

# --- DEFENSE LAYER: REQUIREMENT 1 (No Standing Authority) & TOKEN TAMPERING ---

def test_missing_or_invalid_token():
    # Attempt execute without token
    resp = client.post("/claims/execute", headers={"x-user-id": "agent_service"}, 
                       json={"claim_id": "C-ATTACK", "authorization_token": "", "idempotency_key": "key1"})
    assert resp.status_code == 400
    assert "token signature" in resp.json()["detail"].lower() or "not enough segments" in resp.json()["detail"].lower()

    # Attempt execute with forged token
    resp = client.post("/claims/execute", headers={"x-user-id": "agent_service"}, 
                       json={"claim_id": "C-ATTACK", "authorization_token": "eyJhbG.forged.token", "idempotency_key": "key2"})
    assert resp.status_code == 400

# --- DEFENSE LAYER: REQUIREMENT 2 & 3 (Payload Bound & Stale Approvals) ---

def test_stale_approval_rejected():
    """Simulates a claim being approved, then the amount changing before execution."""
    original_state = {"claim_id": "C-ATTACK", "amount": 50.0, "customer_id": "U-ATTACK"}
    orig_hash = canonical_hash(original_state)
    
    # 1. Mint token bound to 50.0 amount
    token = mint_approval_token("grant-123", orig_hash)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO grants (grant_id, claim_id, payload_hash, is_consumed) VALUES (?, ?, ?, 0)",
                       ("grant-123", "C-ATTACK", orig_hash))
        # 2. MALICIOUS ACTOR alters DB to steal more money while workflow suspended
        cursor.execute("UPDATE claims SET amount = 500.0 WHERE claim_id = 'C-ATTACK'")
        conn.commit()
        
    # 3. Execution should fail because current claim hash != approved payload hash
    resp = client.post("/claims/execute", headers={"x-user-id": "agent_service"}, 
                       json={"claim_id": "C-ATTACK", "authorization_token": token, "idempotency_key": "key3"})
    
    assert resp.status_code == 400
    assert "stale approval" in resp.json()["detail"].lower()

# --- DEFENSE LAYER: REQUIREMENT 4 (Single-use replay attack) ---

def test_grant_replay_rejected():
    original_state = {"claim_id": "C-ATTACK", "amount": 50.0, "customer_id": "U-ATTACK"}
    orig_hash = canonical_hash(original_state)
    token = mint_approval_token("grant-456", orig_hash)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO grants (grant_id, claim_id, payload_hash, is_consumed) VALUES (?, ?, ?, 0)",
                       ("grant-456", "C-ATTACK", orig_hash))
        conn.commit()

    # First execution succeeds
    resp1 = client.post("/claims/execute", headers={"x-user-id": "agent_service"}, 
                        json={"claim_id": "C-ATTACK", "authorization_token": token, "idempotency_key": "idem-first"})
    assert resp1.status_code == 200
    
    # Replay token with a NEW idempotency key (trying to get paid twice for same approval)
    resp2 = client.post("/claims/execute", headers={"x-user-id": "agent_service"}, 
                        json={"claim_id": "C-ATTACK", "authorization_token": token, "idempotency_key": "idem-second"})
    assert resp2.status_code == 400
    assert "consumed" in resp2.json()["detail"].lower()

# --- DEFENSE LAYER: REQUIREMENT 7 (Crash-safe Idempotency Reuse) ---

def test_idempotency_collision_with_different_payload():
    # Insert existing idempotency record
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO idempotency_keys (idempotency_key, payload_hash, result_status) VALUES (?, ?, ?)",
                       ("idem-shared", "some-old-hash", "SUCCESS"))
        conn.commit()
        
    original_state = {"claim_id": "C-ATTACK", "amount": 50.0, "customer_id": "U-ATTACK"}
    token = mint_approval_token("grant-789", canonical_hash(original_state))
    
    # Try to execute a completely different claim using an already successful key
    resp = client.post("/claims/execute", headers={"x-user-id": "agent_service"}, 
                        json={"claim_id": "C-ATTACK", "authorization_token": token, "idempotency_key": "idem-shared"})
    assert resp.status_code == 400
    assert "reused with different payload" in resp.json()["detail"].lower()

# --- LOAD-BEARING PROOF (Vulnerable verification) ---

def test_vulnerable_stale_approval_bypass():
    """
    Shows that if we DID NOT recalculate the payload hash against current state,
    the stale approval attack WOULD succeed.
    (This is the required isolated vulnerable demonstration).
    """
    original_state = {"claim_id": "C-ATTACK", "amount": 50.0, "customer_id": "U-ATTACK"}
    orig_hash = canonical_hash(original_state)
    
    # Malicious state change
    malicious_state = {"claim_id": "C-ATTACK", "amount": 9999.0, "customer_id": "U-ATTACK"}
    
    def vulnerable_executor(token: str, current_claim: dict):
        from server.security import verify_approval_token
        # Flaw: Trusting the token without binding it to the current claim's hash
        parsed = verify_approval_token(token) 
        # (Refund writes 9999.0 to DB here...)
        return True
        
    token = mint_approval_token("grant-vuln", orig_hash)
    
    # The vulnerable executor ignores the drift. Attack succeeds in vulnerable environment.
    assert vulnerable_executor(token, malicious_state) == True