"""AgentCore Platform v1.0"""

# Shared mock-mode resolution helper. Single source of truth so every service/
# node checks the same env vars — see implementation_rule.md §1.
#
# STG_MOCK_MODE is what the scaffold's deploy-stg CI job actually sets
# (CI-script-only var, never exported to uvicorn); USE_MOCK is the canonical
# name tests set. Both must be accepted here, and nowhere else.

from __future__ import annotations

import os

_TRUTHY = ("1", "true", "yes")


def mock_mode_enabled() -> bool:
    """True if mock mode is on via USE_MOCK or STG_MOCK_MODE (either alias)."""
    for key in ("USE_MOCK", "STG_MOCK_MODE"):
        if os.environ.get(key, "").strip().lower() in _TRUTHY:
            return True
    return False
