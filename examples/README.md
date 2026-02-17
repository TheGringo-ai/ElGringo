# AI Team Platform - Examples

This directory contains comprehensive examples demonstrating the capabilities of the AI Team Platform.

## Quick Start

```bash
# Install the package
pip install ai-team-platform[all]

# Set your API keys
export ANTHROPIC_API_KEY=your_claude_key
export OPENAI_API_KEY=your_openai_key
export GOOGLE_API_KEY=your_gemini_key

# Run an example
python examples/basic_usage.py
```

## Example Files

### 1. Basic Usage (`basic_usage.py`)
Introduction to the AI Team Platform with simple examples.

**Topics covered:**
- Creating an AIDevTeam instance
- Asking simple questions
- Collaborative tasks
- Code review
- Team status monitoring

```bash
python examples/basic_usage.py
```

---

### 2. Multi-Model Collaboration (`multi_model_collaboration.py`)
Demonstrates all collaboration modes available in the platform.

**Topics covered:**
- **Parallel Mode**: Execute across multiple models simultaneously
- **Sequential Mode**: Chain outputs for iterative refinement
- **Consensus Mode**: Multi-model voting for critical decisions
- **Devil's Advocate Mode**: Challenge proposed solutions
- **Peer Review Mode**: Cross-model code review
- **Brainstorming Mode**: Creative ideation
- **Debate Mode**: Structured argumentation
- **Expert Panel Mode**: Domain-specific consultation

```bash
python examples/multi_model_collaboration.py
```

---

### 3. Security Validation (`security_validation.py`)
Shows the security features for AI-generated tool calls.

**Topics covered:**
- Input validation for tool calls
- Threat level classification (SAFE → CRITICAL)
- Dangerous command detection and blocking
- Permission-based access control
- Audit logging
- Integration with the orchestrator

```bash
python examples/security_validation.py
```

---

### 4. Workflow Automation (`workflow_automation.py`)
Demonstrates automated CI/CD and code review workflows.

**Topics covered:**
- **PreCommitWorkflow**: Security and quality gates
- **CICDWorkflow**: Full CI/CD pipeline automation
- **CodeReviewPipeline**: Automated PR review
- Git hook integration
- Quality gate configuration

```bash
python examples/workflow_automation.py
```

---

### 5. Infrastructure Tools (`infrastructure_tools.py`)
Shows the infrastructure management capabilities.

**Topics covered:**
- **Kubernetes**: kubectl operations for cluster management
- **Terraform**: Infrastructure as Code operations
- **GCP**: Google Cloud Platform operations via gcloud
- Integrated tool usage with `create_all_tools()`
- AI orchestration with infrastructure commands

```bash
python examples/infrastructure_tools.py
```

---

### 6. Specialized Agents (`specialized_agents.py`)
Demonstrates the specialized AI agents for domain expertise.

**Topics covered:**
- **SecurityAuditor**: Vulnerability scanning and OWASP detection
- **CodeReviewer**: Code quality analysis and best practices
- **SolutionArchitect**: System design and Architecture Decision Records
- Agent collaboration patterns
- Custom specialist creation

```bash
python examples/specialized_agents.py
```

---

## Running All Examples

```bash
# Run each example sequentially
for example in basic_usage multi_model_collaboration security_validation workflow_automation infrastructure_tools specialized_agents; do
    echo "Running $example..."
    python examples/${example}.py
    echo ""
done
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | For Claude | Anthropic API key |
| `OPENAI_API_KEY` | For ChatGPT/Grok | OpenAI API key |
| `GOOGLE_API_KEY` | For Gemini | Google AI API key |
| `GOOGLE_CLOUD_PROJECT` | For GCP tools | GCP project ID |
| `KUBECONFIG` | For K8s tools | Kubernetes config path |

## Need Help?

- [Full Documentation](https://github.com/fredtaylor/ai-team-platform#readme)
- [API Reference](https://github.com/fredtaylor/ai-team-platform/docs)
- [Issue Tracker](https://github.com/fredtaylor/ai-team-platform/issues)
