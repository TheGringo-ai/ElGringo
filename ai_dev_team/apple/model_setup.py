"""
Model Setup Helper
==================

Checks and pulls optimal local models for Apple Silicon Macs.
Designed for M3 Pro 18GB: picks models that fit comfortably in unified memory.

Usage:
    from ai_dev_team.apple.model_setup import ensure_models
    await ensure_models()  # Pull any missing recommended models
"""

import asyncio
import logging
import subprocess
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Recommended models for M3 Pro 18GB unified memory
# Total footprint: ~6GB loaded, leaving 12GB for system + MLX
RECOMMENDED_MODELS: Dict[str, Dict] = {
    "llama3.2:3b": {
        "size_gb": 1.8,
        "purpose": "General chat, fast responses",
        "priority": 1,  # Pull first
    },
    "qwen2.5-coder:7b": {
        "size_gb": 4.2,
        "purpose": "Coding tasks, best code quality at this size",
        "priority": 2,
    },
    "deepseek-coder-v2:16b": {
        "size_gb": 9.1,
        "purpose": "Complex coding, large context window",
        "priority": 3,  # Pull last, largest model
    },
}


def get_installed_models() -> List[str]:
    """Get list of currently installed Ollama models."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            models = []
            for line in result.stdout.strip().split('\n')[1:]:
                parts = line.split()
                if parts:
                    models.append(parts[0])
            return models
    except Exception as e:
        logger.debug(f"Could not list Ollama models: {e}")
    return []


def get_missing_models() -> List[str]:
    """Return recommended models that aren't installed yet."""
    installed = get_installed_models()
    missing = []
    for model_name in sorted(RECOMMENDED_MODELS, key=lambda m: RECOMMENDED_MODELS[m]["priority"]):
        # Check if model is installed (handle tag variations)
        base_name = model_name.split(":")[0]
        if not any(base_name in m for m in installed):
            missing.append(model_name)
    return missing


async def pull_model(model_name: str) -> bool:
    """Pull a single Ollama model. Returns True on success."""
    logger.info(f"Pulling model: {model_name} ({RECOMMENDED_MODELS.get(model_name, {}).get('purpose', '')})")
    try:
        proc = await asyncio.create_subprocess_exec(
            "ollama", "pull", model_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0:
            logger.info(f"Successfully pulled {model_name}")
            return True
        else:
            logger.warning(f"Failed to pull {model_name}: {stderr.decode().strip()}")
            return False
    except Exception as e:
        logger.error(f"Error pulling {model_name}: {e}")
        return False


async def ensure_models(skip_large: bool = False) -> Dict[str, bool]:
    """
    Ensure recommended models are available. Pulls any that are missing.

    Args:
        skip_large: If True, skip models over 5GB (e.g. deepseek-coder-v2:16b)

    Returns:
        Dict mapping model name to success status
    """
    missing = get_missing_models()
    if not missing:
        logger.info("All recommended models are already installed")
        return {}

    results = {}
    for model_name in missing:
        info = RECOMMENDED_MODELS.get(model_name, {})
        if skip_large and info.get("size_gb", 0) > 5:
            logger.info(f"Skipping large model {model_name} ({info.get('size_gb')}GB)")
            results[model_name] = False
            continue

        results[model_name] = await pull_model(model_name)

    return results


def print_model_status():
    """Print current model status to console."""
    installed = get_installed_models()
    missing = get_missing_models()

    print("\n=== El Gringo Local Model Status ===\n")

    for name, info in sorted(RECOMMENDED_MODELS.items(), key=lambda x: x[1]["priority"]):
        base = name.split(":")[0]
        is_installed = any(base in m for m in installed)
        status = "INSTALLED" if is_installed else "MISSING"
        icon = "+" if is_installed else "-"
        print(f"  [{icon}] {name:<30} {info['size_gb']}GB  {info['purpose']}")
        print(f"       Status: {status}")

    if missing:
        print(f"\n  {len(missing)} model(s) missing. Run: fred setup-models")
    else:
        print("\n  All recommended models installed!")
    print()
