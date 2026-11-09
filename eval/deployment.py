import json
import os

DEPLOYMENT_RECORD_FILE = os.path.join(os.path.dirname(__file__), "deployment_state.json")

def initialize_deployment_state():
    if not os.path.exists(DEPLOYMENT_RECORD_FILE):
        with open(DEPLOYMENT_RECORD_FILE, 'w') as f:
            json.dump({"current_stage": "CANDIDATE", "approved_by": None, "evidence": None}, f)

def read_state():
    initialize_deployment_state()
    with open(DEPLOYMENT_RECORD_FILE, 'r') as f:
        return json.load(f)

def write_state(state):
    with open(DEPLOYMENT_RECORD_FILE, 'w') as f:
        json.dump(state, f, indent=4)

def promote(eval_report: dict, approver: str):
    """Promotes deployment ONLY if evaluation accuracy is 1.0 (100%)."""
    state = read_state()
    
    if not eval_report or not eval_report.get("governance_pass"):
        raise ValueError("Promotion rejected: Missing or failing evaluation evidence.")
        
    stages = ["CANDIDATE", "CANARY", "STAGED", "PRODUCTION"]
    current_index = stages.index(state["current_stage"])
    
    if current_index < len(stages) - 1:
        state["current_stage"] = stages[current_index + 1]
        state["approved_by"] = approver
        state["evidence"] = eval_report
        write_state(state)
        return {"status": "SUCCESS", "new_stage": state["current_stage"]}
    return {"status": "NO_CHANGE", "message": "Already at PRODUCTION"}

def automatic_demotion(reason: str):
    """Demotes deployment if post-verification fails."""
    state = read_state()
    state["current_stage"] = "CANDIDATE"
    state["approved_by"] = None
    state["evidence"] = None
    state["demotion_reason"] = reason
    write_state(state)
    return {"status": "DEMOTED", "reason": reason}