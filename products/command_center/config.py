"""Command Center configuration."""

from products.base import ProductConfig

PRODUCT_CONFIG = ProductConfig(
    name="command-center",
    display_name="Command Center",
    version="0.1.0",
    description="Unified dashboard API for daily founder operations",
    entry_module="products.command_center.server",
    status="active",
    port=7862,
)
