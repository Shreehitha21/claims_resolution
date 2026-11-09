import time
import uuid
from typing import List, Tuple
from ledger.database import get_db_connection
from ledger.audit import append_audit_record
from server.security import canonical_hash, mint_approval_token

def process_approval(claim_id: str, claim_data: dict, approver_id: str, required_approvals: int) -> Tuple[bool, str, str]:
    """
    Handles approval and mints token if requirements are met.
    Returns (is_fully_approved, token, message).
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check existing approvals
        cursor.execute("SELECT approver_id, timestamp FROM approvals WHERE claim_id = ?", (claim_id,))
        existing = cursor.fetchall()
        
        # REQUIREMENT 5: Four-eyes distinct identity check
        for row in existing:
            if row["approver_id"] == approver_id:
                raise ValueError("Duplicate approval by the same person is forbidden.")
                
        # Record new approval
        current_time = time.time()
        cursor.execute("INSERT INTO approvals (claim_id, approver_id, timestamp) VALUES (?, ?, ?)", 
                       (claim_id, approver_id, current_time))
        conn.commit()
        
        existing.append({"approver_id": approver_id, "timestamp": current_time})
        append_audit_record("APPROVAL_GRANTED", claim_id, approver_id, "APPROVED")
        
        if len(existing) < required_approvals:
            return False, "", f"Approval recorded. {required_approvals - len(existing)} more required."
            
        # REQUIREMENT 6: Detect suspiciously uniform timing (automation/collusion signal)
        if len(existing) > 1:
            times = [r["timestamp"] for r in existing]
            if max(times) - min(times) < 1.0:
                append_audit_record("SUSPICIOUS_TIMING_DETECTED", claim_id, "SYSTEM", "FLAGGED")
                
        # All approvals gathered. Mint payload-bound grant.
        claim_hash = canonical_hash(claim_data)
        grant_id = str(uuid.uuid4())
        
        cursor.execute("INSERT INTO grants (grant_id, claim_id, payload_hash, is_consumed) VALUES (?, ?, ?, 0)",
                       (grant_id, claim_id, claim_hash))
        conn.commit()
        
        token = mint_approval_token(grant_id, claim_hash)
        return True, token, "Fully approved. Execution token generated."