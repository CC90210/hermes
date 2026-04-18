"""Shim — re-exports MockA2000Client under the name the orchestrator imports."""
from adapters.a2000_client import MockA2000Client as A2000MockClient

__all__ = ["A2000MockClient"]
