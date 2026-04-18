"""Shim — re-exports EDIA2000Client under the name the orchestrator imports."""
from adapters.a2000_client import EDIA2000Client as A2000EdiClient

__all__ = ["A2000EdiClient"]
