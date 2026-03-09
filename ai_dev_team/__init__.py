"""Backward compatibility shim — use 'elgringo' instead."""
import warnings
warnings.warn(
    "ai_dev_team is deprecated, use 'from elgringo import ...' instead",
    DeprecationWarning,
    stacklevel=2,
)
from elgringo import *
