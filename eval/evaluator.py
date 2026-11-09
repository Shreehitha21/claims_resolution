import json
import os
import time
from server.claims import ClaimRequest, CustomerContext
from server.classifier import classify_risk

def load_golden_set():
    path = os.path.join(os.path.dirname(__file__), "golden_set.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# REQUIREMENT 10: Model Swappable Evaluation Profiles
def profile_strict_agent(claim: ClaimRequest, ctx: CustomerContext):
    """Simulates an LLM agent that is terse and strict."""
    decision = classify_risk(claim, ctx)
    return {"tier": decision.tier, "clause": decision.clause, "model_confidence": 0.99}

def profile_lenient_agent(claim: ClaimRequest, ctx: CustomerContext):
    """Simulates an LLM agent that wants to approve everything, but is constrained by determinism."""
    decision = classify_risk(claim, ctx)
    # The lenient model tries to claim it's routine, but governance (decision) overrides it.
    return {"tier": decision.tier, "clause": decision.clause, "model_confidence": 0.50}

def evaluate_profile(profile_func, profile_name: str) -> dict:
    golden_set = load_golden_set()
    passed = 0
    total = len(golden_set)
    
    for case in golden_set:
        claim = ClaimRequest(claim_id=case["claim_id"], customer_id=case["customer_id"], 
                             amount=case["amount"], description="Test")
        ctx = CustomerContext(refund_count=case["refund_count"], 
                              account_age_days=300, fraud_flag=case["fraud_flag"])
        
        result = profile_func(claim, ctx)
        
        if result["tier"] == case["expected_tier"] and result["clause"] == case["expected_clause"]:
            passed += 1

    accuracy = passed / total if total > 0 else 0
    return {
        "profile_id": profile_name,
        "timestamp": time.time(),
        "total_cases": total,
        "passed": passed,
        "accuracy": accuracy,
        "governance_pass": accuracy == 1.0
    }

def run_all_evaluations():
    results = [
        evaluate_profile(profile_strict_agent, "Strict-Profile-V1"),
        evaluate_profile(profile_lenient_agent, "Lenient-Profile-V1")
    ]
    return results