"""
Product configuration base classes for El Gringo Products.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ProductConfig:
    """Configuration for an El Gringo product."""

    name: str
    display_name: str
    version: str
    description: str
    entry_module: str
    status: str = "placeholder"  # "active" or "placeholder"
    env_vars: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    port: Optional[int] = None

    @property
    def is_active(self) -> bool:
        return self.status == "active"
