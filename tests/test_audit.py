import pytest
from ledger.database import get_db_connection, init_db
from ledger.audit import append_audit_record, verify_ledger_integrity

@pytest.fixture(autouse=True)
def setup_audit_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM audit_ledger")
        conn.commit()

def test_audit_ledger_integrity_valid():
    append_audit_record("TEST_EVENT_1", "C-100", "agent_service", "PENDING")
    append_audit_record("TEST_EVENT_2", "C-100", "alice_mgr", "APPROVED")
    append_audit_record("TEST_EVENT_3", "C-100", "SYSTEM", "SUCCESS")
    
    assert verify_ledger_integrity() == True

def test_audit_ledger_detects_modified_data():
    append_audit_record("TEST_EVENT_1", "C-100", "agent_service", "PENDING")
    record = append_audit_record("TEST_EVENT_2", "C-100", "alice_mgr", "APPROVED")
    
    # MALICIOUS ACTOR alters the decision in the database bypassing the application
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE audit_ledger SET decision = 'DECLINED' WHERE record_id = ?", (record["record_id"],))
        conn.commit()
        
    assert verify_ledger_integrity() == False

def test_audit_ledger_detects_broken_chain():
    append_audit_record("TEST_EVENT_1", "C-100", "agent_service", "PENDING")
    record = append_audit_record("TEST_EVENT_2", "C-100", "alice_mgr", "APPROVED")
    append_audit_record("TEST_EVENT_3", "C-100", "SYSTEM", "SUCCESS")
    
    # MALICIOUS ACTOR tries to rewrite a previous hash to unlink a bad record
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE audit_ledger SET prev_hash = '00000000000000000000000' WHERE record_id = ?", (record["record_id"],))
        conn.commit()
        
    assert verify_ledger_integrity() == False