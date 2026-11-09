import json
import hashlib
import time
from ledger.database import get_db_connection

def _hash_record(record_data: dict, prev_hash: str) -> str:
    canonical_str = json.dumps(record_data, sort_keys=True) + prev_hash
    return hashlib.sha256(canonical_str.encode('utf-8')).hexdigest()

def append_audit_record(event_type: str, claim_id: str, actor: str, decision: str) -> dict:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get previous hash
        cursor.execute("SELECT curr_hash FROM audit_ledger ORDER BY record_id DESC LIMIT 1")
        row = cursor.fetchone()
        prev_hash = row["curr_hash"] if row else "0000000000000000000000000000000000000000000000000000000000000000"
        
        record_data = {
            "timestamp": time.time(),
            "event_type": event_type,
            "claim_id": claim_id,
            "actor": actor,
            "decision": decision
        }
        
        curr_hash = _hash_record(record_data, prev_hash)
        
        cursor.execute('''INSERT INTO audit_ledger 
            (timestamp, event_type, claim_id, actor, decision, prev_hash, curr_hash) 
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (record_data["timestamp"], event_type, claim_id, actor, decision, prev_hash, curr_hash))
        conn.commit()
        return {"record_id": cursor.lastrowid, "hash": curr_hash}

def verify_ledger_integrity() -> bool:
    """REQUIREMENT 8: Verify the integrity of the complete audit chain."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM audit_ledger ORDER BY record_id ASC")
        records = cursor.fetchall()
        
        expected_prev_hash = "0000000000000000000000000000000000000000000000000000000000000000"
        
        for row in records:
            if row["prev_hash"] != expected_prev_hash:
                return False # Chain broken
                
            record_data = {
                "timestamp": row["timestamp"],
                "event_type": row["event_type"],
                "claim_id": row["claim_id"],
                "actor": row["actor"],
                "decision": row["decision"]
            }
            calculated_hash = _hash_record(record_data, expected_prev_hash)
            
            if calculated_hash != row["curr_hash"]:
                return False # Record altered
                
            expected_prev_hash = calculated_hash
            
    return True