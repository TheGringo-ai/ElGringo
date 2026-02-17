# MLX Fine-tuning for AI Team Platform

Fine-tune local LLMs on Apple Silicon using MLX with LoRA (Low-Rank Adaptation).

## System Requirements

- Apple Silicon Mac (M1/M2/M3)
- 18GB+ RAM recommended for 7B models
- Python 3.10+
- MLX and MLX-LM installed

## Quick Start

### 1. Prepare Training Data

Add your training examples to `data/train.jsonl` in this format:

```json
{"text": "<|im_start|>system\nYou are an expert coder.<|im_end|>\n<|im_start|>user\nYour question here<|im_end|>\n<|im_start|>assistant\nYour answer here<|im_end|>"}
```

**Recommended:** 100-1000 high-quality examples for good results.

### 2. Run Training

```bash
cd mlx-training
python scripts/train_qwen_coder.py
```

Training will:
- Download Qwen 2.5 Coder 7B (first run only)
- Fine-tune using LoRA (memory efficient)
- Save adapter to `models/qwen-coder-lora/`

### 3. Test Fine-tuned Model

```bash
python -m mlx_lm.generate \
  --model Qwen/Qwen2.5-Coder-7B-Instruct \
  --adapter-path models/qwen-coder-lora \
  --prompt "Write a Python function to sort a list"
```

### 4. Convert to Ollama (Optional)

```bash
python scripts/convert_to_ollama.py
```

## Memory Usage (M3 Pro 18GB)

| Model | LoRA Training | Full Fine-tune |
|-------|---------------|----------------|
| 3B    | ~6 GB         | ~12 GB         |
| 7B    | ~10 GB        | Too large      |
| 14B+  | Not recommended | Not possible |

## Training Tips

1. **Start small**: Begin with 100 iterations, increase if loss decreases
2. **Quality > Quantity**: 100 good examples beat 1000 bad ones
3. **Monitor memory**: Close other apps during training
4. **Check loss**: If loss stops decreasing, stop training

## Files

```
mlx-training/
├── configs/
│   └── lora_config.yaml    # Training configuration
├── data/
│   ├── train.jsonl         # Training data (add your examples)
│   └── valid.jsonl         # Validation data (optional)
├── models/
│   └── qwen-coder-lora/    # Fine-tuned adapter output
└── scripts/
    ├── train_qwen_coder.py # Main training script
    └── convert_to_ollama.py # Convert to Ollama format
```

## Troubleshooting

**Out of Memory:**
- Reduce `--lora-layers` to 8
- Reduce `--lora-rank` to 4
- Close all other applications

**Poor Results:**
- Add more training data (aim for 500+ examples)
- Increase iterations
- Check data quality

**Slow Training:**
- This is normal for 7B models
- Expect ~1-2 iterations per second on M3 Pro
