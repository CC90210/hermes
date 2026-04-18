"""Shim — re-exports PlaywrightA2000Client under the name the orchestrator imports."""
from adapters.a2000_client import PlaywrightA2000Client as A2000PlaywrightClient

__all__ = ["A2000PlaywrightClient"]
