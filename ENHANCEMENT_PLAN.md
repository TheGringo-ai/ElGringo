# AITeamPlatform Enhancement Plan
## Commander: Claude (Lead Analyst) | Date: January 28, 2026

---

## PHASE 1: Llama Cloud API Integration (Priority: HIGH)

### 1.1 Create Llama Cloud Agent (`ai_dev_team/agents/llama_cloud.py`)

```python
"""
Llama Cloud Agent - API-based Llama Models
==========================================

Integrates Llama models via cloud APIs for:
- Higher capacity than local Ollama
- Function calling support
- No local GPU requirements
"""

import os
import logging
import time
from typing import Optional, List

from .base import AIAgent, AgentConfig, AgentResponse, ModelType

logger = logging.getLogger(__name__)


class LlamaCloudAgent(AIAgent):
    """
    Llama via Together AI, Fireworks, or Groq APIs.

    Benefits over Ollama:
    - Llama 3.3 70B (too large for most local machines)
    - Function calling support
    - No local resource usage
    - Faster for large models
    """

    PROVIDERS = {
        "together": {
            "url": "https://api.together.xyz/v1/chat/completions",
            "key_env": "TOGETHER_API_KEY",
            "models": {
                "llama-3.3-70b": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
                "llama-3.2-3b": "meta-llama/Llama-3.2-3B-Instruct-Turbo",
                "llama-3.1-8b": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
            }
        },
        "fireworks": {
            "url": "https://api.fireworks.ai/inference/v1/chat/completions",
            "key_env": "FIREWORKS_API_KEY",
            "models": {
                "llama-3.3-70b": "accounts/fireworks/models/llama-v3p3-70b-instruct",
                "llama-3.1-405b": "accounts/fireworks/models/llama-v3p1-405b-instruct",
            }
        },
        "groq": {
            "url": "https://api.groq.com/openai/v1/chat/completions",
            "key_env": "GROQ_API_KEY",
            "models": {
                "llama-3.3-70b": "llama-3.3-70b-versatile",
                "llama-3.1-8b": "llama-3.1-8b-instant",
                "mixtral": "mixtral-8x7b-32768",
            }
        },
    }

    def __init__(
        self,
        provider: str = "groq",  # Groq is fastest
        model: str = "llama-3.3-70b",
        config: Optional[AgentConfig] = None,
    ):
        self.provider = provider
        self.model_key = model

        provider_config = self.PROVIDERS.get(provider, self.PROVIDERS["groq"])
        self.api_url = provider_config["url"]
        self.api_key = os.getenv(provider_config["key_env"])
        self.model_name = provider_config["models"].get(model, model)

        if config is None:
            config = AgentConfig(
                name=f"llama-{model}-{provider}",
                model_type=ModelType.LOCAL,  # Categorize with local for now
                role=f"Llama Expert ({model} via {provider})",
                capabilities=["coding", "analysis", "reasoning", "fast-response"],
                model_name=self.model_name,
                temperature=0.7,
                cost_tier="budget",  # Llama is cost-effective
            )
        super().__init__(config)

    async def is_available(self) -> bool:
        """Check if API key is configured"""
        return bool(self.api_key)

    async def generate_response(
        self,
        prompt: str,
        context: str = "",
        system_override: Optional[str] = None,
        **kwargs
    ) -> AgentResponse:
        import aiohttp

        start_time = time.time()

        if not self.api_key:
            return AgentResponse(
                agent_name=self.name,
                model_type=self.config.model_type,
                content="",
                confidence=0.0,
                response_time=0.0,
                error=f"Missing API key: {self.PROVIDERS[self.provider]['key_env']}"
            )

        try:
            system_prompt = system_override or self.config.system_prompt or (
                f"You are {self.name}, a powerful Llama AI assistant. "
                "Provide helpful, accurate, and well-reasoned responses."
            )

            messages = [{"role": "system", "content": system_prompt}]

            if context:
                messages.append({"role": "user", "content": f"Context:\n{context}"})

            messages.append({"role": "user", "content": prompt})

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            data = {
                "model": self.model_name,
                "messages": messages,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    headers=headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result["choices"][0]["message"]["content"]
                        response_time = time.time() - start_time

                        self.update_stats(response_time, True)
                        self.add_to_history("user", prompt)
                        self.add_to_history("assistant", content)

                        return AgentResponse(
                            agent_name=self.name,
                            model_type=self.config.model_type,
                            content=content,
                            confidence=0.85,  # Llama 70B is very capable
                            response_time=response_time,
                            metadata={
                                "model": self.model_name,
                                "provider": self.provider,
                                "tokens": result.get("usage", {}),
                            }
                        )
                    else:
                        error_text = await response.text()
                        raise Exception(f"API Error {response.status}: {error_text}")

        except Exception as e:
            response_time = time.time() - start_time
            self.update_stats(response_time, False)
            logger.error(f"Llama Cloud error: {e}")

            return AgentResponse(
                agent_name=self.name,
                model_type=self.config.model_type,
                content="",
                confidence=0.0,
                response_time=response_time,
                error=str(e)
            )


# Factory functions
def create_llama_70b(provider: str = "groq") -> LlamaCloudAgent:
    """Create Llama 3.3 70B agent (most capable)"""
    return LlamaCloudAgent(provider=provider, model="llama-3.3-70b")

def create_llama_fast(provider: str = "groq") -> LlamaCloudAgent:
    """Create fast Llama 3.1 8B agent"""
    return LlamaCloudAgent(provider=provider, model="llama-3.1-8b")
```

### 1.2 Update `.env.template`

Add to environment variables:
```bash
# Llama Cloud Providers
TOGETHER_API_KEY=your_together_api_key
FIREWORKS_API_KEY=your_fireworks_api_key
GROQ_API_KEY=your_groq_api_key
```

### 1.3 Update Router Agent Strengths

Add to `ai_dev_team/routing/router.py`:
```python
# In _build_agent_strengths():
"llama-cloud": {
    "model_type": ModelType.LOCAL,
    "strengths": [TaskType.CODING, TaskType.ANALYSIS, TaskType.REASONING],
    "capabilities": ["fast-coding", "reasoning", "analysis", "multilingual"],
    "performance_weight": 1.2,
},
"ollama-local": {
    "model_type": ModelType.LOCAL,
    "strengths": [TaskType.CODING, TaskType.DEBUGGING],
    "capabilities": ["offline", "privacy", "fast-simple"],
    "performance_weight": 0.9,
},
```

---

## PHASE 2: Enhanced Apple Intelligence Integration (Priority: HIGH)

### 2.1 Core ML Integration (`ai_dev_team/monitor/apple_coreml.py`)

```python
"""
Apple Core ML Integration
=========================

Leverage Apple Silicon Neural Engine for:
- On-device inference (privacy)
- Hardware acceleration
- Zero API costs
"""

import logging
import os
import platform
import subprocess
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class AppleCoreMLIntegration:
    """
    Apple Silicon Neural Engine integration for on-device AI.

    Provides:
    - On-device LLM inference (via MLX or llama.cpp)
    - Image analysis via Vision framework
    - Speech recognition via Speech framework
    - Text analysis via NaturalLanguage framework
    """

    def __init__(self):
        self.is_apple_silicon = self._check_apple_silicon()
        self.mlx_available = self._check_mlx()

    def _check_apple_silicon(self) -> bool:
        """Check if running on Apple Silicon"""
        if platform.system() != "Darwin":
            return False
        try:
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True, text=True
            )
            return "Apple" in result.stdout
        except Exception:
            return False

    def _check_mlx(self) -> bool:
        """Check if MLX is available"""
        try:
            import mlx
            return True
        except ImportError:
            return False

    async def run_local_llm(
        self,
        prompt: str,
        model: str = "mlx-community/Llama-3.2-3B-Instruct-4bit",
        max_tokens: int = 512,
    ) -> Dict[str, Any]:
        """
        Run LLM inference on Apple Silicon Neural Engine via MLX.

        Benefits:
        - Completely private (on-device)
        - No API costs
        - Fast on Apple Silicon
        - Works offline
        """
        if not self.is_apple_silicon:
            return {"success": False, "error": "Requires Apple Silicon Mac"}

        if not self.mlx_available:
            return {"success": False, "error": "MLX not installed. Run: pip install mlx mlx-lm"}

        try:
            from mlx_lm import load, generate

            # Load model (cached after first load)
            model_obj, tokenizer = load(model)

            # Generate response
            response = generate(
                model_obj,
                tokenizer,
                prompt=prompt,
                max_tokens=max_tokens,
                verbose=False,
            )

            return {
                "success": True,
                "content": response,
                "model": model,
                "device": "Apple Neural Engine",
            }

        except Exception as e:
            logger.error(f"MLX inference error: {e}")
            return {"success": False, "error": str(e)}

    async def analyze_image(self, image_path: str) -> Dict[str, Any]:
        """
        Analyze image using Apple Vision framework.

        Uses on-device ML for:
        - Object detection
        - Text recognition (OCR)
        - Face detection
        - Scene classification
        """
        if platform.system() != "Darwin":
            return {"success": False, "error": "Requires macOS"}

        try:
            # Use PyObjC to access Vision framework
            script = f'''
            import Vision
            import Quartz
            from Foundation import NSURL

            url = NSURL.fileURLWithPath_("{image_path}")
            request = Vision.VNRecognizeTextRequest.alloc().init()
            handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(url, None)
            handler.performRequests_error_([request], None)

            results = []
            for observation in request.results():
                text = observation.topCandidates_(1)[0].string()
                confidence = observation.confidence()
                results.append({{"text": text, "confidence": confidence}})

            print(results)
            '''

            result = subprocess.run(
                ["python3", "-c", script],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                import ast
                return {
                    "success": True,
                    "results": ast.literal_eval(result.stdout.strip()),
                    "framework": "Apple Vision",
                }
            else:
                return {"success": False, "error": result.stderr}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def speech_to_text(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribe audio using Apple Speech framework.
        On-device, private, no API costs.
        """
        if platform.system() != "Darwin":
            return {"success": False, "error": "Requires macOS"}

        try:
            # Use Apple's speech recognition
            script = f'''
            import Speech

            recognizer = Speech.SFSpeechRecognizer.alloc().init()
            url = Foundation.NSURL.fileURLWithPath_("{audio_path}")
            request = Speech.SFSpeechURLRecognitionRequest.alloc().initWithURL_(url)

            # This is simplified - full implementation needs async handling
            print("Transcription would happen here")
            '''

            # For now, fall back to whisper.cpp for Apple Silicon
            result = subprocess.run(
                ["whisper", audio_path, "--model", "base", "--output_format", "txt"],
                capture_output=True,
                text=True,
                timeout=60
            )

            return {
                "success": result.returncode == 0,
                "transcription": result.stdout,
                "error": result.stderr if result.returncode != 0 else None,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_system_info(self) -> Dict[str, Any]:
        """Get Apple Silicon system capabilities"""
        info = {
            "is_apple_silicon": self.is_apple_silicon,
            "mlx_available": self.mlx_available,
            "platform": platform.platform(),
            "processor": platform.processor(),
        }

        if self.is_apple_silicon:
            try:
                # Get Neural Engine info
                result = subprocess.run(
                    ["system_profiler", "SPHardwareDataType"],
                    capture_output=True,
                    text=True
                )
                if "Apple M" in result.stdout:
                    for line in result.stdout.split("\n"):
                        if "Chip:" in line or "Memory:" in line:
                            key, value = line.split(":", 1)
                            info[key.strip().lower()] = value.strip()
            except Exception:
                pass

        return info


# Singleton instance
_apple_coreml = None

def get_apple_coreml() -> AppleCoreMLIntegration:
    """Get Apple Core ML integration instance"""
    global _apple_coreml
    if _apple_coreml is None:
        _apple_coreml = AppleCoreMLIntegration()
    return _apple_coreml
```

### 2.2 Siri Voice Commands (`ai_dev_team/monitor/siri_integration.py`)

```python
"""
Siri Integration for AI Team
============================

Enable voice-activated AI team commands:
- "Hey Siri, ask AI team to review my code"
- "Hey Siri, debug this error"
- "Hey Siri, what did AI team learn today?"
"""

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SiriIntegration:
    """
    Siri Shortcuts integration for voice-activated AI team.

    Creates Shortcuts that can:
    - Trigger AI team collaboration
    - Query learned knowledge
    - Execute common commands
    """

    SHORTCUTS_DIR = Path.home() / "Library" / "Shortcuts"

    def __init__(self, api_url: str = "http://localhost:8080"):
        self.api_url = api_url

    def create_ai_team_shortcut(self) -> bool:
        """
        Create Siri Shortcut for "Ask AI Team".

        Usage: "Hey Siri, Ask AI Team <your question>"
        """
        shortcut_script = f'''
        tell application "Shortcuts Events"
            run shortcut "Ask AI Team" with input "{{input}}"
        end tell
        '''

        # Create a shell script that Shortcuts can call
        script_path = Path.home() / ".ai-dev-team" / "siri-bridge.sh"
        script_path.parent.mkdir(parents=True, exist_ok=True)

        script_content = f'''#!/bin/bash
# AI Team Siri Bridge
# Called by Siri Shortcuts to interact with AI Team

QUESTION="$1"
API_URL="{self.api_url}"

# Send to AI team API
RESPONSE=$(curl -s -X POST "$API_URL/api/ai/collaborate" \\
    -H "Content-Type: application/json" \\
    -d '{{"prompt": "'$QUESTION'", "mode": "parallel"}}')

# Extract answer
ANSWER=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('final_answer', 'No response'))")

# Speak the response
say "$ANSWER"

# Also copy to clipboard
echo "$ANSWER" | pbcopy

echo "$ANSWER"
'''

        script_path.write_text(script_content)
        os.chmod(script_path, 0o755)

        logger.info(f"Created Siri bridge script at {script_path}")

        # Instructions for manual Shortcut creation
        instructions = f"""
To complete Siri integration:

1. Open Shortcuts app on your Mac
2. Create new Shortcut named "Ask AI Team"
3. Add action: "Run Shell Script"
4. Set script to: {script_path} "Shortcut Input"
5. Add action: "Speak Text" with the script output
6. Enable "Show in Share Sheet"
7. Set Siri phrase: "Ask AI Team"

Now you can say: "Hey Siri, Ask AI Team how do I fix this bug?"
"""
        print(instructions)
        return True

    def create_code_review_shortcut(self) -> bool:
        """Create Shortcut for quick code review from clipboard"""
        script_path = Path.home() / ".ai-dev-team" / "code-review.sh"
        script_path.parent.mkdir(parents=True, exist_ok=True)

        script_content = f'''#!/bin/bash
# Get code from clipboard
CODE=$(pbpaste)

# Send to AI team for review
RESPONSE=$(curl -s -X POST "{self.api_url}/api/ai/review" \\
    -H "Content-Type: application/json" \\
    -d '{{"code": "'$CODE'", "language": "auto"}}')

# Extract review
REVIEW=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('final_answer', 'No review available'))")

# Show notification
osascript -e "display notification \\"$REVIEW\\" with title \\"AI Code Review\\""

# Speak summary
say "Code review complete. Check the notification for details."
'''

        script_path.write_text(script_content)
        os.chmod(script_path, 0o755)

        logger.info(f"Created code review script at {script_path}")
        return True

    def list_available_commands(self) -> List[Dict[str, str]]:
        """List available Siri commands"""
        return [
            {
                "phrase": "Ask AI Team <question>",
                "description": "Ask the AI team any development question",
                "example": "Hey Siri, Ask AI Team how to implement authentication",
            },
            {
                "phrase": "Review my code",
                "description": "Review code currently in clipboard",
                "example": "Hey Siri, Review my code",
            },
            {
                "phrase": "Debug this error",
                "description": "Debug error message in clipboard",
                "example": "Hey Siri, Debug this error",
            },
            {
                "phrase": "What did AI Team learn today",
                "description": "Get summary of today's learnings",
                "example": "Hey Siri, What did AI Team learn today",
            },
        ]


# Singleton
_siri_integration = None

def get_siri_integration(api_url: str = "http://localhost:8080") -> SiriIntegration:
    global _siri_integration
    if _siri_integration is None:
        _siri_integration = SiriIntegration(api_url)
    return _siri_integration
```

---

## PHASE 3: Seamless Development Enhancements (Priority: MEDIUM)

### 3.1 Auto-Agent Selection Improvements

Update `orchestrator.py` to:
1. Include Ollama agents in routing decisions
2. Auto-detect best model for task complexity
3. Fallback chains: Cloud API -> Local Ollama -> Cached response

### 3.2 Developer Experience Features

1. **IDE Status Bar**: Show AI team status in VS Code/menu bar
2. **Hotkey Activation**: `Cmd+Shift+A` to ask AI team
3. **Context-Aware Suggestions**: Auto-suggest based on current file
4. **Git Hook Integration**: Pre-commit AI review

### 3.3 Real-Time Collaboration Dashboard

Create web dashboard showing:
- Active agents and their status
- Recent learnings and patterns
- Cost tracking and budget
- Performance metrics

---

## PHASE 4: Intelligence Amplification (Priority: MEDIUM)

### 4.1 Cross-Model Debate Mode

Implement structured debate between models:
- Claude proposes solution
- Llama challenges assumptions
- Gemini synthesizes creative alternatives
- Grok validates reasoning
- Final consensus from weighted voting

### 4.2 Continuous Learning Pipeline

```python
# Auto-learn from:
1. Every successful code review
2. Every bug that was fixed
3. Every architectural decision
4. User feedback and corrections
5. Production error patterns
```

### 4.3 Predictive Assistance

- Predict what developer needs next based on patterns
- Pre-fetch relevant documentation
- Suggest optimizations before they're needed

---

## Implementation Priority Matrix

| Enhancement | Impact | Effort | Priority |
|-------------|--------|--------|----------|
| Llama Cloud API | HIGH | LOW | 1 |
| Apple Core ML | HIGH | MEDIUM | 2 |
| Router Updates | MEDIUM | LOW | 3 |
| Siri Integration | MEDIUM | LOW | 4 |
| Dashboard | MEDIUM | HIGH | 5 |

---

## Quick Start Commands

```bash
# Install required dependencies
pip install mlx mlx-lm aiohttp

# Set up API keys
export GROQ_API_KEY="your_groq_key"
export TOGETHER_API_KEY="your_together_key"

# Test Llama Cloud
python -c "from ai_dev_team.agents.llama_cloud import create_llama_70b; print('Llama ready!')"

# Test Apple Core ML
python -c "from ai_dev_team.monitor.apple_coreml import get_apple_coreml; print(get_apple_coreml().get_system_info())"
```

---

## AI Team Consensus

**Claude (Lead Analyst)**: "The architecture is solid. Priority should be cloud Llama integration for capability boost."

**Gemini (Creative)**: "Siri voice commands would make the developer experience magical - hands-free coding!"

**Grok (Reasoner)**: "Core ML integration leverages Apple Silicon's neural engine - significant performance gain for local inference."

**ChatGPT (Coder)**: "The router needs local agent strengths added - currently Ollama agents are invisible to task routing."

---

*Plan authored by Claude (AI Team Commander) | January 28, 2026*
