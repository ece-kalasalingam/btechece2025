"""
ARTICULATION POLICY CONTRACT (KARE R2025)

- This file defines authoritative accreditation limits
- Values here MUST NOT be overridden at runtime
- Any change requires:
  - Git commit
  - Re-validation of all syllabi
"""

MAX_PO  = 11
MAX_PSO = 3
MAX_SO  = 7
ALLOWED_LEVELS = {1, 2, 3}