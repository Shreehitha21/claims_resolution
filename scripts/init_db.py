import os
import sys

# Ensure the root project directory is in the Python path (fixes Defect 4: Import bug)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ledger.database import init_db

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")