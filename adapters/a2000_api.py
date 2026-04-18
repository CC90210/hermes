"""Shim — re-exports APIA2000Client under the name the orchestrator imports."""
from adapters.a2000_client import APIA2000Client as A2000ApiClient

__all__ = ["A2000ApiClient"]
