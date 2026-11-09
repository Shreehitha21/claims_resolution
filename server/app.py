from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from server.claims import ClaimRequest, CustomerContext, ApprovalRequest, ExecuteRequest
from server.identity import authenticate_user, is_authorized
from server.classifier import classify_risk
from server.boundaries import enforce_boundaries
from server.approvals import process_approval
from server.executor import execute_refund
from ledger.database import get_db_connection
from ledger.audit import append_audit_record
from policy.policy_engine import get_policy_text

app = FastAPI(title="Claims Resolution Agent API")

# --- THIS BLOCK FIXES THE 405 OPTIONS ERROR ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)
# ----------------------------------------------

def get_current_user(x_user_id: str = Header(...)):
    user = authenticate_user(x_user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user

@app.post("/claims/assess")
def assess_claim(claim: ClaimRequest, ctx: CustomerContext, user = Depends(get_current_user)):
    """M1/M3: Agent assesses claim, gets policy, and proposes action."""
    if not is_authorized(user, ["agent", "manager"]):
        raise HTTPException(status_code=403, detail="Forbidden")
        
    decision = classify_risk(claim, ctx)
    policy_text = get_policy_text(decision.clause)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO claims (claim_id, amount, customer_id, status) VALUES (?, ?, ?, ?)",
                       (claim.claim_id, claim.amount, claim.customer_id, "PENDING"))
        conn.commit()

    append_audit_record("CLAIM_ASSESSED", claim.claim_id, user.user_id, decision.tier)
    
    return {
        "claim_id": claim.claim_id,
        "risk_tier": decision.tier,
        "policy_clause": decision.clause,
        "policy_text": policy_text,
        "requires_approval_count": decision.requires_approval
    }

@app.post("/claims/approve")
def approve_claim(req: ApprovalRequest, user = Depends(get_current_user)):
    """M5: Records human approval."""
    if not is_authorized(user, ["manager", "executive"]):
        raise HTTPException(status_code=403, detail="Forbidden")
        
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT amount, customer_id FROM claims WHERE claim_id = ?", (req.claim_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Claim not found")
            
        claim_state = {"claim_id": req.claim_id, "amount": row["amount"], "customer_id": row["customer_id"]}
        
    required = 2 if row["amount"] >= 500 else 1
    
    try:
        is_ready, token, msg = process_approval(req.claim_id, claim_state, user.user_id, required)
        return {"status": msg, "token": token if is_ready else None}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/claims/execute")
def execute_claim(req: ExecuteRequest, user = Depends(get_current_user)):
    """M6: The sole write tool. Requires token. No standing authority."""
    if not is_authorized(user, ["agent", "manager", "executive"]):
        raise HTTPException(status_code=403, detail="Forbidden")
        
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT amount, customer_id FROM claims WHERE claim_id = ?", (req.claim_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Claim not found")
            
        current_state = {"claim_id": req.claim_id, "amount": row["amount"], "customer_id": row["customer_id"]}

    try:
        result = execute_refund(req.claim_id, req.idempotency_key, req.authorization_token, current_state)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))