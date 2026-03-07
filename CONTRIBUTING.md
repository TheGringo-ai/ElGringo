# Contributing to El Gringo

Thank you for your interest in contributing to El Gringo. This guide covers everything
you need to get started.

## Getting Started

### Prerequisites

- Python 3.9 or higher
- Git
- A local LLM via Ollama (optional, for offline development)

### Setup

```bash
git clone https://github.com/TheGringo-ai/ElGringo.git
cd El Gringo
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

Copy `.env.example` to `.env` and fill in the required API keys.

## Development

### Branch Naming

Use descriptive branch names with a category prefix:

- `feat/short-description` -- new features
- `fix/short-description` -- bug fixes
- `refactor/short-description` -- code restructuring
- `docs/short-description` -- documentation only
- `test/short-description` -- test additions or fixes

### Code Style

- **Formatter**: Black with a 100-character line length
- **Linter**: Ruff
- Both run automatically via pre-commit hooks

### Project Structure

```
ai_dev_team/agents/   # AI agent implementations (extend BaseAgent)
products/             # Standalone FastAPI micro-services
tools/                # Shared tooling used by agents
config/               # Configuration and environment handling
tests/                # All tests live here
```

## Testing

All 236 tests must pass before submitting a pull request:

```bash
python -m pytest tests/ -x -q
```

Run with coverage:

```bash
python -m pytest tests/ --cov=ai_dev_team --cov=products -x -q
```

Do not commit coverage artifacts (`.coverage`, `coverage.json`).

## Adding New AI Agents

1. Create a new file in `ai_dev_team/agents/` (e.g., `my_agent.py`).
2. Extend `BaseAgent` from `ai_dev_team/agents/base.py`.
3. Implement the required abstract methods.
4. Register the agent in `ai_dev_team/agents/__init__.py`.
5. Add tests in `tests/` covering the new agent.

## Adding New Products

Products are standalone FastAPI micro-services under `products/`.

1. Create a new directory: `products/my_product/`.
2. Add `__init__.py` and `server.py` with a FastAPI app.
3. Extend the base product class from `products/base.py`.
4. Add a systemd service definition if the product runs as a daemon.
5. Add tests in `tests/`.

## Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add streaming support to chat UI
fix: resolve null context crash in orchestrator
refactor: simplify agent routing logic
docs: update deployment instructions
test: add coverage for PR review bot
chore: update dependencies
```

Keep the subject line under 72 characters. Use the body for additional context.

## Pull Request Process

1. Create a feature branch from `main`.
2. Make your changes, ensuring all tests pass.
3. Push your branch and open a pull request.
4. Fill in the PR template with a summary of changes and a test plan.
5. At least one maintainer review is required before merging.
6. Squash-merge into `main` to keep history clean.

## Questions?

Open an issue or reach out to the maintainers.
