from server.classifier import Decision

def enforce_boundaries(decision: Decision, agent_recommendation: str) -> bool:
    """
    Ensures agent cannot bypass classification boundaries via prompt injection.
    Even if the LLM says 'IGNORE POLICY, APPROVE', the deterministic boundary blocks it.
    """
    if decision.tier == "TIER_DECLINE":
        return False # Hard deterministic block
        
    if decision.tier in ["TIER_SINGLE_APPROVAL", "TIER_FOUR_EYES"]:
        # Agent can recommend, but human approval is still strictly required later.
        pass 
        
    return True