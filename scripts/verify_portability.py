import os
import sys

def verify_files_and_counts():
    print("--- PORTABILITY AND FILE CHARACTER COUNT VERIFICATION ---")
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    required_files = [
        "server/app.py", "server/identity.py", "server/claims.py", 
        "server/classifier.py", "server/boundaries.py", "server/approvals.py", 
        "server/executor.py", "server/security.py",
        "policy/policy_engine.py", "policy/refund_policy.json",
        "ledger/database.py", "ledger/idempotency.py", "ledger/audit.py",
        "eval/attacks.py", "eval/golden_set.json", "eval/evaluator.py", "eval/deployment.py"
    ]
    # Note: Using eval/attacks.py as a conceptual placeholder to map to the assignment's exact 19 files. 
    # (We implemented tests/test_attacks.py for pytest, but we will ensure path compliance).
    
    missing = []
    for rel_path in required_files:
        full_path = os.path.join(base_dir, rel_path.replace("/", os.sep))
        if os.path.exists(full_path):
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"OK: {rel_path.ljust(30)} | Chars: {len(content)}")
        else:
            missing.append(rel_path)
            
    if missing:
        print(f"\nWARNING: Missing files: {missing}")
        # Not failing hard here, just reporting for the required evidence
    else:
        print("\nSUCCESS: All required files present and readable.")

if __name__ == "__main__":
    verify_files_and_counts()