"""Documentation Generator Service configuration."""

from products.base import ProductConfig

PRODUCT_CONFIG = ProductConfig(
    name="doc-generator",
    display_name="Documentation Generator Service",
    version="0.1.0",
    description="AI-powered documentation generation for codebases, APIs, and architectures",
    entry_module="products.doc_generator.server",
    status="active",
    port=8083,
    env_vars=["DOC_GEN_API_KEYS", "DOC_GEN_CORS_ORIGINS", "DOC_GEN_PORT"],
)
