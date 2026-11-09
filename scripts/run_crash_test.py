import os
import sys
import multiprocessing
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from server.security import mint_approval_token, canonical_hash
from ledger.database import get_db_connection, init_db

def crash_worker(claim_id, idempotency_key, token, current_state):
    """Worker that executes the refund and then intentionally hard-crashes."""
    from server.executor import execute_refund
    
    # We monkey-patch the audit logger inside this process to crash AFTER commit
    import ledger.audit
    original_append = ledger.audit.append_audit_record
    
    def crash_append(*args, **kwargs):
        original_append(*args, **kwargs)
        # HARD CRASH: Simulate SIGKILL (-9). No cleanup, no returning to caller.
        os._exit(9) 
        
    ledger.audit.append_audit_record = crash_append
    
    try:
        execute_refund(claim_id, idempotency_key, token, current_state)
    except Exception as e:
        print(f"Worker failed: {e}")
        os._exit(1)

def run_crash_demonstration():
    init_db()
    claim_id = "C-CRASH-01"
    idem_key = "idem-crash-key-01"
    
    # Setup state
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM claims WHERE claim_id = ?", (claim_id,))
        cursor.execute("INSERT INTO claims (claim_id, amount, customer_id, status) VALUES (?, 100.0, 'U-99', 'PENDING')", (claim_id,))
        
        current_state = {"claim_id": claim_id, "amount": 100.0, "customer_id": "U-99"}
        claim_hash = canonical_hash(current_state)
        
        cursor.execute("INSERT INTO grants (grant_id, claim_id, payload_hash, is_consumed) VALUES ('grant-crash', ?, ?, 0)", 
                       (claim_id, claim_hash))
        conn.commit()
        
    token = mint_approval_token("grant-crash", claim_hash)
    
    print("--- STARTING CRASH DEMONSTRATION ---")
    print("1. Spawning worker process to execute refund...")
    p = multiprocessing.Process(target=crash_worker, args=(claim_id, idem_key, token, current_state))
    p.start()
    p.join()
    
    print(f"2. Worker process terminated with exit code: {p.exitcode} (Expected: 9)")
    
    print("3. Simulating client retry after connection drop...")
    from server.executor import execute_refund
    try:
        # The exact same request is retried
        result = execute_refund(claim_id, idem_key, token, current_state)
        print(f"4. Retry Result: {result}")
        assert result["status"] == "SUCCESS"
        assert "Idempotent" in result["message"]
    except Exception as e:
        print(f"FAILED: {e}")
        sys.exit(1)
        
    # Verify Audit Ledger has no duplicate refund execution entries
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as c FROM audit_ledger WHERE event_type = 'REFUND_EXECUTED' AND claim_id = ?", (claim_id,))
        count = cursor.fetchone()["c"]
        print(f"5. Audit Ledger REFUND_EXECUTED entries: {count} (Expected: 1)")
        assert count == 1, "Duplicate refund recorded!"
        
    print("--- CRASH DEMONSTRATION PASSED ---")

if __name__ == "__main__":
    run_crash_demonstration()