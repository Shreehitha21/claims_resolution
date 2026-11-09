from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class ClaimRequest(BaseModel):
    claim_id: str
    customer_id: str
    amount: float = Field(..., gt=0)
    currency: str = "USD"
    description: str
    # Untrusted data: agent might try to inject instructions here.

class CustomerContext(BaseModel):
    refund_count: int
    account_age_days: int
    fraud_flag: bool = False

class ApprovalRequest(BaseModel):
    claim_id: str
    approver_id: str

class ExecuteRequest(BaseModel):
    claim_id: str
    authorization_token: str
    idempotency_key: str