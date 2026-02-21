"""Code Audit Service configuration."""

from products.base import ProductConfig

PRODUCT_CONFIG = ProductConfig(
    name="code-audit",
    display_name="Code Audit Service",
    version="0.1.0",
    description="Automated codebase security and quality audits",
    entry_module="products.code_audit.server",
    status="active",
    port=8081,
)
