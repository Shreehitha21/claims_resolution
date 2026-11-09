from ledger.database import get_db_connection
from ledger.audit import append_audit_record
from server.security import canonical_hash, verify_approval_token
import sqlite3

def execute_refund(claim_id: str, idempotency_key: str, token: str, current_claim_state: dict) -> dict:
    """
    REQUIREMENT 3: Reverify after workflow suspension.
    REQUIREMENT 4: Single-use approval grants.
    REQUIREMENT 7: Crash-safe idempotency.
    """
    # 1. Re-calculate current state hash
    curr_hash = canonical_hash(current_claim_state)
    
    # 2. Verify Token Authenticity and expiration
    token_data = verify_approval_token(token)
    
    # 3. Verify Payload Binding (Payload Drift Check)
    if token_data["payload_hash"] != curr_hash:
        append_audit_record("EXECUTION_REJECTED", claim_id, "SYSTEM", "STALE_APPROVAL_DRIFT")
        raise ValueError("Stale approval: Claim data has changed since approval.")
        
    grant_id = token_data["grant_id"]
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 4. Check Idempotency First (Return early if already processed)
        cursor.execute("SELECT payload_hash, result_status FROM idempotency_keys WHERE idempotency_key = ?", (idempotency_key,))
        idem_row = cursor.fetchone()
        
        if idem_row:
            if idem_row["payload_hash"] != curr_hash:
                raise ValueError("Idempotency key reused with different payload.")
            return {"status": idem_row["result_status"], "message": "Idempotent response returned."}
            
        try:
            # BEGIN EXCLUSIVE TRANSACTION for atomic check-and-consume
            cursor.execute("BEGIN EXCLUSIVE")
            
            # 5. Check Grant consumption
            cursor.execute("SELECT is_consumed FROM grants WHERE grant_id = ?", (grant_id,))
            grant_row = cursor.fetchone()
            
            if not grant_row:
                raise ValueError("Grant not found.")
            if grant_row["is_consumed"] == 1:
                # We raise the error here, but write the audit log AFTER rolling back the lock
                raise ValueError("Approval grant has already been consumed.")
                
            # 6. Consume Grant & Record Idempotency
            cursor.execute("UPDATE grants SET is_consumed = 1 WHERE grant_id = ?", (grant_id,))
            cursor.execute("INSERT INTO idempotency_keys (idempotency_key, payload_hash, result_status) VALUES (?, ?, ?)",
                           (idempotency_key, curr_hash, "SUCCESS"))
            
            # 7. Execute actual refund (update claim status)
            cursor.execute("UPDATE claims SET status = 'REFUNDED' WHERE claim_id = ?", (claim_id,))
            
            conn.commit()
            # Audit runs safely after commit (lock released)
            append_audit_record("REFUND_EXECUTED", claim_id, "SYSTEM", "SUCCESS")
            return {"status": "SUCCESS", "message": "Refund processed successfully."}
            
        except Exception as e:
            conn.rollback() # Release the EXCLUSIVE lock
            
            # Now it's safe to write the audit record since the lock is gone
            if "consumed" in str(e):
                append_audit_record("EXECUTION_REJECTED", claim_id, "SYSTEM", "GRANT_REPLAY")
                
            raise e