import os
import sys
# DEFECT 5 FIX: Faculty assignment had an import bug in eval directory. 
# Fixed by inserting root into sys.path before importing server components.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from server.security import mint_approval_token