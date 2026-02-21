"""Test Generator Service configuration."""

from products.base import ProductConfig

PRODUCT_CONFIG = ProductConfig(
    name="test-generator",
    display_name="Test Generator Service",
    version="0.1.0",
    description="AI-powered unit test generation, coverage analysis, and test improvement",
    entry_module="products.test_generator.server",
    status="active",
    port=8082,
)
