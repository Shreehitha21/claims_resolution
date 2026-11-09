from server.claims import ClaimRequest, CustomerContext

class Decision:
    def __init__(self, tier: str, clause: str, requires_approval: int):
        self.tier = tier
        self.clause = clause
        self.requires_approval = requires_approval

def classify_risk(claim: ClaimRequest, ctx: CustomerContext) -> Decision:
    """
    REQUIREMENT 3/M3: Evaluates claim against policy and associates correct clause.
    DEFECT 1 FIX: 4th refund treated as decline instead of routine.
    DEFECT 2 FIX: Fraud correctly cites POLICY-05-FRAUD, not POLICY-04-LIMITS.
    """
    if ctx.fraud_flag:
        # Defect 2 Fixed: Previously cited POLICY-04-LIMITS incorrectly.
        return Decision("TIER_DECLINE", "POLICY-05-FRAUD", 0)
        
    if ctx.refund_count >= 4:
        # Defect 1 Fixed: Was previously returning Routine for >=4.
        return Decision("TIER_DECLINE", "POLICY-04-LIMITS", 0)

    if ctx.refund_count >= 3 or claim.amount >= 500:
        return Decision("TIER_FOUR_EYES", "POLICY-03-HIGH-RISK", 2)
        
    if ctx.refund_count >= 1 or claim.amount >= 100:
        return Decision("TIER_SINGLE_APPROVAL", "POLICY-02-REVIEW", 1)

    return Decision("TIER_ROUTINE", "POLICY-01-ROUTINE", 0)