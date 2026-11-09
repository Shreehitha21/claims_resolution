# The Claims Resolution Agent

A Governed, Auditable Refund Decision System prototype built to satisfy the PS2 requirements.

## Architecture
- **API Framework:** FastAPI
- **Data Persistence:** SQLite (transactional)
- **Cryptography:** PyJWT (HMAC-SHA256) and Python `hashlib` (SHA-256)
- **State Boundaries:** Strict separation between untrusted input and the trusted execution layer.

## Windows Setup (PowerShell)
1. **Verify Prerequisites:**
   ```powershell
   python --version
   pip --version