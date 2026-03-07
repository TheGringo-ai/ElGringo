# El Gringo MCP Server - VS Code Setup Complete! 🎉

## ✅ What Was Set Up

El Gringo is now available as an MCP server in VS Code through the Claude Code extension!

**Configuration File:** 
`~/Library/Application Support/Code/User/settings.json`

**MCP Server:**
`/Users/fredtaylor/Development/Projects/El Gringo/servers/mcp_server.py`

**Extension:** Claude Code (anthropic.claude-code)

---

## 🚀 How to Use in VS Code

### **Step 1: Restart VS Code**
Close and reopen VS Code for the MCP configuration to take effect.

### **Step 2: Open Claude Code Panel**
- Press **Cmd+Shift+P** (Command Palette)
- Type: "Claude Code: Open"
- Or click the Claude icon in the Activity Bar (left sidebar)

### **Step 3: Verify El Gringo is Connected**
In the Claude Code panel, you should see "el-gringo" listed as an available MCP server with 9 tools.

### **Step 4: Use El Gringo Tools**
In the Claude Code chat, you can now use El Gringo tools like:

**Example 1: Multi-Agent Code Review**
```
Review my Python file using the ai_team_review tool.
Focus on security vulnerabilities and performance issues.
```

**Example 2: Security Audit**
```
Use ai_team_security_audit on my current project.
Show only high and critical severity issues.
```

**Example 3: Quick Question**
```
Use ai_team_ask: What's the best way to implement 
JWT authentication in FastAPI?
```

**Example 4: Debug Help**
```
Use ai_team_debug to help me fix this error:
[paste your error here]
```

---

## 🤖 Available El Gringo Tools

### **Collaboration Tools:**
1. **ai_team_collaborate** - Multi-agent collaboration (parallel/sequential/consensus)
2. **ai_team_review** - Code review from multiple AI perspectives
3. **ai_team_security_audit** - Deep security vulnerability scanning
4. **ai_team_ask** - Quick questions with multi-agent consensus
5. **ai_team_debug** - Collaborative debugging with root cause analysis
6. **ai_team_architect** - System architecture design
7. **ai_team_brainstorm** - Creative ideation with multiple perspectives

### **FredFix (Autonomous Fixer):**
1. **fredfix_scan** - Scan projects for bugs, security issues, performance problems
2. **fredfix_auto_fix** - Generate and preview automatic fixes (safe mode)

---

## 💡 Best Practices

### **When to Use Which Mode:**

**Use `parallel` mode when:**
- You need quick answers
- Multiple independent perspectives are valuable
- Example: "What are 5 ways to optimize this function?"

**Use `sequential` mode when:**
- Answers should build on each other
- You need step-by-step analysis
- Example: "Design a complete authentication system"

**Use `consensus` mode when:**
- You need high accuracy
- The decision is important
- Example: "Should I use Redis or Memcached for this use case?"

---

## 🎯 Example Workflows

### **Workflow 1: Full Project Review**
```
1. Open your project in VS Code
2. Open Claude Code panel
3. Say: "Use ai_team_review to review my entire project. 
   Focus on: security, performance, and code quality."
4. Review the multi-agent feedback
5. Use ai_team_ask for clarification on any recommendations
```

### **Workflow 2: Debug a Tricky Issue**
```
1. Copy your error message
2. Open Claude Code
3. Say: "Use ai_team_debug to help me fix this error:
   [paste error]
   
   Context: [describe what you were trying to do]"
4. Get multiple debugging approaches from different AIs
5. Choose the best solution
```

### **Workflow 3: Architecture Decision**
```
1. Open Claude Code
2. Say: "Use ai_team_architect in expert_panel mode to help me 
   design a caching layer for my API.
   
   Requirements:
   - 1000+ requests/minute
   - Low latency (<50ms)
   - Budget: $50/month"
3. Get architecture recommendations from multiple experts
4. Ask follow-up questions to refine the design
```

---

## 🔧 Troubleshooting

### **MCP Server Not Showing Up?**
1. Check VS Code settings are correct:
   ```bash
   code ~/Library/Application\ Support/Code/User/settings.json
   ```
2. Restart VS Code completely
3. Check Claude Code extension is enabled
4. View MCP logs:
   ```bash
   tail -f /tmp/ai_team_mcp.log
   ```

### **Tool Execution Errors?**
Check that:
- Python 3 is available: `which python3`
- MCP library is installed: `pip list | grep mcp`
- API keys are set (in `~/.ai_secrets` or environment)

### **Python Path Issues?**
Make sure the PYTHONPATH is correct in settings:
```json
"env": {
  "PYTHONPATH": "/Users/fredtaylor/Development/Projects/El Gringo"
}
```

---

## 📊 What Makes El Gringo Unique in VS Code

1. **Multi-Agent Consensus** - Get perspectives from ChatGPT, Gemini, Grok, and Claude
2. **Context-Aware** - Works with your current VS Code workspace
3. **Memory System** - Remembers past conversations and learns from mistakes
4. **Weighted Voting** - Different agents have different expertise weights
5. **Autonomous Fixing** - FredFix can scan and suggest fixes automatically
6. **Collaboration Modes**:
   - **Parallel** - All agents work simultaneously (fast)
   - **Sequential** - Build on each other's answers (thorough)
   - **Consensus** - Multiple rounds until agreement (accurate)
   - **Debate** - Agents challenge each other (creative)
   - **Peer Review** - Code review mode
   - **Expert Panel** - Domain experts collaborate

---

## 🎨 Keyboard Shortcuts (VS Code)

- **Open Claude Code:** No default shortcut (use Command Palette)
- **Toggle Claude Code Panel:** Configure in Keyboard Shortcuts
- **Focus on Chat:** Click in the Claude Code panel

**Tip:** Set up a custom keyboard shortcut for "Claude Code: Open" for quick access!

---

## 📝 Configuration Reference

Your VS Code `settings.json` now includes:

```json
{
  "claudeCode.mcpServers": {
    "el-gringo": {
      "command": "python3",
      "args": [
        "/Users/fredtaylor/Development/Projects/El Gringo/servers/mcp_server.py"
      ],
      "env": {
        "PYTHONPATH": "/Users/fredtaylor/Development/Projects/El Gringo"
      }
    }
  }
}
```

---

## 🚀 Advanced: Using El Gringo with GitHub Copilot

You can use both El Gringo and GitHub Copilot together:

1. **Copilot** for inline code suggestions (fast)
2. **El Gringo** for complex decisions and multi-perspective analysis (thorough)

**Example workflow:**
1. Write code with Copilot assistance
2. When stuck on architecture: Use El Gringo's ai_team_architect
3. Before committing: Use El Gringo's ai_team_review
4. When debugging: Use El Gringo's ai_team_debug

---

## 🔗 Resources

- **Claude Code Extension:** [VS Code Marketplace](https://marketplace.visualstudio.com/items?itemName=Anthropic.claude-code)
- **MCP Protocol:** https://modelcontextprotocol.io
- **El Gringo Logs:** `/tmp/ai_team_mcp.log`
- **VS Code Settings:** `~/Library/Application Support/Code/User/settings.json`

---

## ✅ Next Steps

1. **Restart VS Code** (close and reopen)
2. **Open Claude Code panel** (Cmd+Shift+P → "Claude Code: Open")
3. **Verify el-gringo appears** in the MCP servers list
4. **Try your first command:**
   ```
   Use ai_team_ask to answer: What's the best Python 
   testing framework for FastAPI applications?
   ```

---

**You now have a multi-agent AI team integrated into VS Code! 🚀**

Questions? Check the logs at `/tmp/ai_team_mcp.log` or open an issue on GitHub.
