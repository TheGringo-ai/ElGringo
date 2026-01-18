# AI Development Team

Multi-Model AI Orchestration Platform for Software Development.

Coordinates Claude, ChatGPT, Gemini, and Grok to collaborate on software development tasks with intelligent task routing, persistent memory, and continuous learning.

## Features

- **Multi-Model Orchestration**: Claude (Anthropic), ChatGPT (OpenAI), Gemini (Google), Grok (xAI)
- **Collaboration Modes**: Parallel, Sequential, Consensus, Devil's Advocate, Peer Review
- **Intelligent Task Routing**: Automatically selects best agents for each task type
- **Memory System**: Captures all interactions, mistakes, and solutions
- **Never-Repeat-Mistakes**: Learns from errors to prevent recurring issues
- **Cross-Project Learning**: Share knowledge across all your projects

## Installation

```bash
# Clone the repository
git clone https://github.com/fredtaylor/ai-dev-team.git
cd ai-dev-team

# Install with all AI model support
pip install -e ".[all]"

# Or install with specific models only
pip install -e ".[claude,openai]"
```

## Quick Start

### Set API Keys

```bash
export ANTHROPIC_API_KEY="your-claude-key"
export OPENAI_API_KEY="your-openai-key"
export GEMINI_API_KEY="your-gemini-key"
export XAI_API_KEY="your-grok-key"
```

### Python API

```python
from ai_dev_team import AIDevTeam
import asyncio

async def main():
    # Create AI team
    team = AIDevTeam(project_name="my-project")

    # Collaborate on a task
    result = await team.collaborate(
        "Build a REST API for user authentication with JWT tokens"
    )

    print(f"Success: {result.success}")
    print(f"Answer: {result.final_answer}")
    print(f"Confidence: {result.confidence_score:.0%}")

asyncio.run(main())
```

### Command Line Interface

```bash
# Interactive mode
ai-dev-team

# Single task
ai-dev-team "Build a REST API for user authentication"

# Consensus mode (multiple rounds)
ai-dev-team -m consensus "Design a database schema for e-commerce"

# Check API keys
ai-dev-team --check-keys

# Show team status
ai-dev-team --status
```

## Collaboration Modes

### Parallel (Default)
All agents work simultaneously on the task.

```python
result = await team.collaborate(prompt, mode="parallel")
```

### Sequential
Agents work in sequence, each building on previous responses.

```python
result = await team.collaborate(prompt, mode="sequential")
```

### Consensus
Multiple rounds to build agreement among agents.

```python
result = await team.collaborate(prompt, mode="consensus", max_iterations=3)
```

## Specialized Methods

### Code Review

```python
result = await team.code_review(
    code="def hello(): print('Hello')",
    language="python",
    focus=["security", "performance"]
)
```

### Debugging

```python
result = await team.debug(
    error="TypeError: cannot unpack non-iterable NoneType object",
    code="x, y = get_values()",
    context="get_values() sometimes returns None"
)
```

### Architecture Design

```python
result = await team.architect(
    requirements="Build a real-time chat application",
    constraints=["Use WebSockets", "Scale to 10k concurrent users"]
)
```

## Memory & Learning

The AI team learns from every interaction:

```python
from ai_dev_team.memory import MemorySystem, LearningEngine

# Create memory system
memory = MemorySystem(storage_dir="~/.ai-dev-team/memory")

# Create learning engine
learning = LearningEngine(memory)

# Analyze performance
analysis = await learning.analyze_performance(project="my-project")
print(analysis["success_rate"])
print(analysis["recommendations"])
```

## Task Routing

Automatically route tasks to the best agents:

```python
from ai_dev_team.routing import TaskRouter

router = TaskRouter()
classification = router.classify("Fix the authentication bug in login.py")

print(f"Task type: {classification.primary_type}")
print(f"Recommended agents: {classification.recommended_agents}")
print(f"Recommended mode: {classification.recommended_mode}")
```

## Configuration

Create `ai-dev-team.json` in your project:

```json
{
    "project_name": "my-app",
    "enable_memory": true,
    "enable_learning": true,
    "default_mode": "parallel",
    "max_consensus_rounds": 3,
    "consensus_threshold": 0.8
}
```

## Agent Roles

| Agent | Model | Role | Best For |
|-------|-------|------|----------|
| claude-analyst | Claude | Lead Analyst | Analysis, Architecture, Planning |
| chatgpt-coder | GPT-4 | Senior Developer | Coding, Debugging, Testing |
| gemini-creative | Gemini | Creative Director | Design, Innovation, UI/UX |
| grok-reasoner | Grok-3 | Strategic Thinker | Reasoning, Strategy |
| grok-coder | Grok-Fast | Speed Coder | Fast coding, Optimization |

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Claude API key |
| `OPENAI_API_KEY` | OpenAI/ChatGPT API key |
| `GEMINI_API_KEY` | Google Gemini API key |
| `XAI_API_KEY` | xAI Grok API key |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to Firebase credentials (for Firestore memory) |

## Project Structure

```
ai-dev-team/
├── ai_dev_team/
│   ├── __init__.py          # Package exports
│   ├── orchestrator.py      # Main AIDevTeam class
│   ├── cli.py               # Command line interface
│   ├── agents/              # AI model integrations
│   │   ├── base.py          # Abstract agent class
│   │   ├── claude.py        # Claude/Anthropic
│   │   ├── chatgpt.py       # OpenAI/GPT
│   │   ├── gemini.py        # Google Gemini
│   │   └── grok.py          # xAI Grok
│   ├── memory/              # Memory & learning system
│   │   ├── system.py        # Core memory storage
│   │   ├── prevention.py    # Mistake prevention
│   │   └── learning.py      # Learning engine
│   ├── collaboration/       # Collaboration patterns
│   │   └── engine.py        # Collaboration modes
│   ├── routing/             # Task routing
│   │   └── router.py        # Intelligent routing
│   └── utils/               # Utilities
│       └── config.py        # Configuration
├── examples/                # Usage examples
├── tests/                   # Test suite
├── pyproject.toml           # Package configuration
└── README.md
```

## License

MIT License - See LICENSE file for details.

## Contributing

Contributions welcome! Please read CONTRIBUTING.md for guidelines.
