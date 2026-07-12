"""Analysis modes: macro (broad conservation) and strict (orthology by cohesion)."""
from __future__ import annotations

from .macro import MacroMode
from .strict import StrictMode

__all__ = ["MacroMode", "StrictMode"]
