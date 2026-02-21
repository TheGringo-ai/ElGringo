"""Fred API configuration."""

from products.base import ProductConfig

PRODUCT_CONFIG = ProductConfig(
    name="fred-api",
    display_name="Fred API",
    version="0.1.0",
    description="Public REST API for FredAI orchestration as a service",
    entry_module="products.fred_api.server",
    status="active",
    port=8080,
)
