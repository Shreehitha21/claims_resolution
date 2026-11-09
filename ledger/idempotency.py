from ledger.database import get_db_connection

def check_idempotency(idempotency_key: str) -> dict:
    """Read-only check for existing idempotency records."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT payload_hash, result_status FROM idempotency_keys WHERE idempotency_key = ?", (idempotency_key,))
        row = cursor.fetchone()
        if row:
            return {"payload_hash": row["payload_hash"], "status": row["result_status"]}
    return None