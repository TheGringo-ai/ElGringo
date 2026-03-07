# Security

## What El Gringo Can Access

El Gringo agents can execute tools that interact with your system. Understanding the permission surface is important.

### MCP Server Tools
When running as an MCP server, tools are invoked by the connected client (e.g., Claude Code, Cursor). The client controls which tool calls to approve. El Gringo does not execute tools autonomously unless explicitly triggered.

### Tool Execution Scope
- **File tools**: Read/write within the working directory
- **Shell tools**: Execute commands in a subprocess
- **Git tools**: Standard git operations
- **Docker tools**: Container management (requires Docker installed)
- **Deploy tools**: Deployment scripts (requires explicit configuration)

### What El Gringo Does NOT Do
- Does not send your code to any service unless you configure an API key for that provider
- Does not persist data outside `~/.ai-dev-team/` (local) or your Firestore project (if enabled)
- Does not auto-execute agent suggestions — tool calls require client approval via MCP protocol
- Does not have network access beyond the AI provider APIs you configure

## API Keys & Secrets

- **Never commit `.env` files** — `.gitignore` excludes them by default
- Store API keys in environment variables or `~/.ai_secrets` (sourced at runtime)
- Firestore credentials: set `GOOGLE_APPLICATION_CREDENTIALS` to your service account JSON path
- The platform checks for API keys at startup and only registers agents whose keys are present

## Reporting Vulnerabilities

If you discover a security vulnerability, please report it privately:

1. **Do not** open a public GitHub issue
2. Email the maintainer or use GitHub's private vulnerability reporting
3. Include steps to reproduce and potential impact

We will respond within 48 hours and work with you on a fix before any public disclosure.
