"""Dataset discovery and readiness reporting for the OPC pipeline."""

from .inventory import build_inventory, write_reports

__all__ = ["build_inventory", "write_reports"]
