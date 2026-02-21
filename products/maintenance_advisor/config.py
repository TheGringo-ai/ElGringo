"""Maintenance Advisor configuration."""

from products.base import ProductConfig

PRODUCT_CONFIG = ProductConfig(
    name="maintenance-advisor",
    display_name="Maintenance Advisor",
    version="0.1.0",
    description="AI-powered maintenance optimization and predictive analytics",
    entry_module="products.maintenance_advisor.server",
    status="active",
    port=8082,
)
