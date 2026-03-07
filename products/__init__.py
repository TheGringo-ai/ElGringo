"""
El Gringo Products Registry
=========================

Auto-discovers products by scanning products/*/config.py for PRODUCT_CONFIG instances.
"""

import importlib
import pkgutil
from pathlib import Path
from typing import Dict, List, Optional

from .base import ProductConfig


_registry: Optional[Dict[str, ProductConfig]] = None


def _discover_products() -> Dict[str, ProductConfig]:
    """Scan product subdirectories for PRODUCT_CONFIG instances."""
    products = {}
    products_dir = Path(__file__).parent

    for item in sorted(products_dir.iterdir()):
        if not item.is_dir() or item.name.startswith("_"):
            continue

        config_path = item / "config.py"
        if not config_path.exists():
            continue

        try:
            module = importlib.import_module(f"products.{item.name}.config")
            config = getattr(module, "PRODUCT_CONFIG", None)
            if isinstance(config, ProductConfig):
                products[config.name] = config
        except Exception:
            pass

    return products


def _get_registry() -> Dict[str, ProductConfig]:
    global _registry
    if _registry is None:
        _registry = _discover_products()
    return _registry


def list_products() -> List[ProductConfig]:
    """Return all discovered products."""
    return list(_get_registry().values())


def get_product(name: str) -> Optional[ProductConfig]:
    """Get a product by name."""
    return _get_registry().get(name)


def reload_products() -> List[ProductConfig]:
    """Force re-discovery of products."""
    global _registry
    _registry = None
    return list_products()


def discover_products() -> List[ProductConfig]:
    """Public alias for list_products() -- discovers and returns all products."""
    return list_products()
