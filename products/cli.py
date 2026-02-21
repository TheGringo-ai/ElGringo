"""
FredAI Products CLI handler.

Supports: fred products list|run|info <name>
"""

import importlib
import sys

from . import list_products, get_product


def handle_products_command(args):
    """Handle 'fred products' subcommand."""
    action = getattr(args, "products_action", "list")

    if action == "list":
        _list_products()
    elif action == "info":
        _show_info(args.product_name)
    elif action == "run":
        _run_product(args.product_name)
    else:
        print(f"Unknown products action: {action}")
        sys.exit(1)


def _list_products():
    """List all discovered products."""
    products = list_products()
    if not products:
        print("No products found.")
        return

    print(f"\nFredAI Products ({len(products)} found)\n")
    print(f"{'Name':<25} {'Version':<10} {'Status':<12} {'Description'}")
    print("-" * 80)
    for p in products:
        status_icon = "[active]" if p.is_active else "[placeholder]"
        print(f"{p.display_name:<25} {p.version:<10} {status_icon:<12} {p.description}")
    print()


def _show_info(name: str):
    """Show detailed info about a product."""
    product = get_product(name)
    if not product:
        print(f"Product '{name}' not found. Run 'fred products list' to see available products.")
        sys.exit(1)

    print(f"\n{product.display_name} v{product.version}")
    print(f"  Status:      {product.status}")
    print(f"  Description: {product.description}")
    print(f"  Module:      {product.entry_module}")
    if product.port:
        print(f"  Port:        {product.port}")
    if product.env_vars:
        print(f"  Env vars:    {', '.join(product.env_vars)}")
    if product.dependencies:
        print(f"  Deps:        {', '.join(product.dependencies)}")
    print()


def _run_product(name: str):
    """Launch a product."""
    product = get_product(name)
    if not product:
        print(f"Product '{name}' not found.")
        sys.exit(1)

    if not product.is_active:
        print(f"Product '{product.display_name}' is a placeholder and cannot be run yet.")
        sys.exit(1)

    try:
        module = importlib.import_module(product.entry_module)
        main_fn = getattr(module, "main", None)
        if main_fn is None:
            print(f"No main() function found in {product.entry_module}")
            sys.exit(1)
        main_fn()
    except ImportError as e:
        print(f"Failed to import {product.entry_module}: {e}")
        print(f"Install dependencies: pip install {' '.join(product.dependencies)}")
        sys.exit(1)
