import json
import os

def load_policies() -> dict:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    policy_path = os.path.join(base_dir, 'refund_policy.json')
    with open(policy_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_policy_text(clause_id: str) -> str:
    policies = load_policies()
    return policies.get(clause_id, "Unknown Policy")