import sqlite3
import os
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DATABASE_URL", "sqlite:///data/claims.db").replace("sqlite:///", "")

@contextmanager
def get_db_connection():
    # Ensure data directory exists
    os.makedirs(os.path.dirname(DB_PATH) or '.', exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Claims state
        cursor.execute('''CREATE TABLE IF NOT EXISTS claims (
            claim_id TEXT PRIMARY KEY, amount REAL, customer_id TEXT, status TEXT)''')
        
        # Approvals
        cursor.execute('''CREATE TABLE IF NOT EXISTS approvals (
            approval_id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_id TEXT, approver_id TEXT, timestamp REAL)''')
            
        # Authorization Grants (REQUIREMENT 4: Single-use)
        cursor.execute('''CREATE TABLE IF NOT EXISTS grants (
            grant_id TEXT PRIMARY KEY, claim_id TEXT, payload_hash TEXT, is_consumed INTEGER DEFAULT 0)''')
            
        # Idempotency (REQUIREMENT 7: Crash-safe)
        cursor.execute('''CREATE TABLE IF NOT EXISTS idempotency_keys (
            idempotency_key TEXT PRIMARY KEY, payload_hash TEXT, result_status TEXT)''')
            
        # Audit Ledger (REQUIREMENT 8: Hash-chain)
        cursor.execute('''CREATE TABLE IF NOT EXISTS audit_ledger (
            record_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL, event_type TEXT, claim_id TEXT, actor TEXT,
            decision TEXT, prev_hash TEXT, curr_hash TEXT)''')
            
        conn.commit()

# Seed database for testing if empty
init_db()