#!/usr/bin/env python3
"""
Convert MLX fine-tuned LoRA adapter to Ollama-compatible format
"""

import os
import sys
import subprocess

def main():
    print("=" * 60)
    print("Convert MLX LoRA Adapter to Ollama Format")
    print("=" * 60)
    print()

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    adapter_path = os.path.join(base_dir, "models", "qwen-coder-lora")
    output_dir = os.path.join(base_dir, "models", "ollama-export")

    if not os.path.exists(adapter_path):
        print(f"ERROR: LoRA adapter not found at {adapter_path}")
        print("Run training first: python scripts/train_qwen_coder.py")
        sys.exit(1)

    print(f"Adapter path: {adapter_path}")
    print(f"Output dir: {output_dir}")
    print()

    # Step 1: Fuse LoRA weights with base model
    print("Step 1: Fusing LoRA weights with base model...")
    fused_path = os.path.join(base_dir, "models", "qwen-coder-fused")

    fuse_cmd = [
        sys.executable, "-m", "mlx_lm.fuse",
        "--model", "Qwen/Qwen2.5-Coder-7B-Instruct",
        "--adapter-path", adapter_path,
        "--save-path", fused_path,
    ]

    result = subprocess.run(fuse_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Fusing failed: {result.stderr}")
        sys.exit(1)
    print("  Done!")

    # Step 2: Convert to GGUF format for Ollama
    print()
    print("Step 2: Converting to GGUF format...")
    print("  This requires llama.cpp's convert script.")
    print()
    print("  Manual steps:")
    print("  1. Clone llama.cpp: git clone https://github.com/ggerganov/llama.cpp")
    print("  2. Run: python llama.cpp/convert_hf_to_gguf.py", fused_path)
    print("  3. Quantize: ./llama.cpp/llama-quantize model.gguf model-q4.gguf Q4_K_M")
    print()

    # Step 3: Create Ollama Modelfile
    print("Step 3: Creating Ollama Modelfile...")
    os.makedirs(output_dir, exist_ok=True)

    modelfile_content = """# Ollama Modelfile for Fine-tuned Qwen Coder
FROM ./qwen-coder-finetuned.gguf

TEMPLATE \"\"\"<|im_start|>system
{{ .System }}<|im_end|>
<|im_start|>user
{{ .Prompt }}<|im_end|>
<|im_start|>assistant
\"\"\"

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER stop "<|im_end|>"

SYSTEM \"\"\"You are an expert coding assistant fine-tuned for the AI Team Platform.
You write clean, efficient, well-documented code.\"\"\"
"""

    modelfile_path = os.path.join(output_dir, "Modelfile")
    with open(modelfile_path, "w") as f:
        f.write(modelfile_content)

    print(f"  Created: {modelfile_path}")
    print()
    print("=" * 60)
    print("Next steps:")
    print("  1. Convert fused model to GGUF (see instructions above)")
    print("  2. Move GGUF file to:", output_dir)
    print("  3. Run: cd", output_dir, "&& ollama create qwen-coder-custom -f Modelfile")
    print("  4. Test: ollama run qwen-coder-custom")
    print("=" * 60)

if __name__ == "__main__":
    main()
