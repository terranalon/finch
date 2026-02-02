"""Meitav Dash broker integration.

Israeli broker that provides Excel exports of positions and transactions.
Uses the shared IsraeliSecuritiesImportService for import logic.
"""

from .parser import MeitavParser

__all__ = [
    "MeitavParser",
]
