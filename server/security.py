import os
import json
import hashlib
import jwt
import datetime
from dotenv import load_dotenv

load_dotenv()

def get_signing_key() -> str:
    key = os.getenv("CRA_JWT_SIGNING_KEY")
    if not key or key == "change_me_to_a_secure_random_string_in_local_env":
        # REQUIREMENT 1: Fail safely if missing/default config.
        raise RuntimeError("CRITICAL: Missing or insecure CRA_JWT_SIGNING_KEY.")
    return key

def canonical_hash(claim_data: dict) -> str:
    """REQUIREMENT 2: Canonicalize claim state to prevent payload drift."""
    # Ensure keys are sorted and whitespace is stripped for determinism
    canonical_str = json.dumps(claim_data, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical_str.encode('utf-8')).hexdigest()

def mint_approval_token(grant_id: str, claim_hash: str) -> str:
    """Mints a short-lived, payload-bound JWT."""
    payload = {
        "grant_id": grant_id,
        "payload_hash": claim_hash,
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=15),
        "scope": "execute_refund"
    }
    return jwt.encode(payload, get_signing_key(), algorithm="HS256")

def verify_approval_token(token: str) -> dict:
    """Verifies token signature, expiration, and scope."""
    try:
        decoded = jwt.decode(token, get_signing_key(), algorithms=["HS256"])
        if decoded.get("scope") != "execute_refund":
            raise ValueError("Invalid token scope.")
        return decoded
    except jwt.ExpiredSignatureError:
        raise ValueError("Authorization token expired.")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid authorization token signature.")