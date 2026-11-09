from typing import Optional
from pydantic import BaseModel

class User(BaseModel):
    user_id: str
    role: str

# In a real app, this would query a secure identity provider.
# For this prototype, we use a synthetic hardcoded store.
SYNTHETIC_USERS = {
    "agent_service": User(user_id="agent_service", role="agent"),
    "alice_mgr": User(user_id="alice_mgr", role="manager"),
    "bob_mgr": User(user_id="bob_mgr", role="manager"),
    "charlie_exec": User(user_id="charlie_exec", role="executive"),
    "unauthorized_user": User(user_id="unauthorized_user", role="customer_support")
}

def authenticate_user(user_id: str) -> Optional[User]:
    return SYNTHETIC_USERS.get(user_id)

def is_authorized(user: User, required_role: list[str]) -> bool:
    return user.role in required_role