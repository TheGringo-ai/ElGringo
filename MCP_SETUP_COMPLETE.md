# El Gringo MCP Server - Setup Complete! 🎉

## ✅ What Was Set Up

El Gringo is now available as an MCP (Model Context Protocol) server in Claude Desktop!

**Configuration File:** 
`~/Library/Application Support/Claude/claude_desktop_config.json`

**MCP Server:**
`/Users/fredtaylor/Development/Projects/El Gringo/servers/mcp_server.py`

---

## 🤖 Available Tools in Claude Desktop

Once you restart Claude Desktop, you'll have access to these El Gringo tools:

### **Collaboration Tools:**
1. **ai_team_collaborate** - Have multiple AI agents (ChatGPT, Gemini, Grok) work together
2. **ai_team_review** - Get code review from multiple AI perspectives
3. **ai_team_security_audit** - Deep security vulnerability scanning
4. **ai_team_ask** - Quick questions with multi-agent consensus
5. **ai_team_debug** - Collaborative debugging with root cause analysis
6. **ai_team_architect** - System architecture design with expert panel
7. **ai_team_brainstorm** - Creative ideation with multiple perspectives

### **FredFix (Autonomous Fixer):**
1. **fredfix_scan** - Scan projects for bugs, security issues, performance problems
2. **fredfix_auto_fix** - Generate and preview automatic fixes (safe mode)

### **Memory & Learning:**
- Cross-session memory (learns from past conversations)
- Mistake prevention (won't repeat past errors)
- Adaptive routing (learns which agents are best for which tasks)

---

## 🚀 How to Use

### **Step 1: Restart Claude Desktop**
```bash
# Close Claude Desktop completely, then reopen it
killall Claude 2>/dev/null; open -a Claude
```

### **Step 2: Verify Connection**
In Claude Desktop, look for the **MCP icon** (🔌) in the toolbar. You should see "el-gringo" listed.

### **Step 3: Use El Gringo Tools**
In Claude Desktop, you can now say things like:

**Example 1: Code Review**
```
Review my Python project at /Users/fredtaylor/Development/Projects/work/managers-dashboard
using the ai_team_review tool. Focus on security and performance.
```

**Example 2: Security Audit**
```
Run a security audit on /Users/fredtaylor/Development/Projects/ChatterFix
using ai_team_security_audit. Show only high and critical severity issues.
```

**Example 3: Multi-Agent Collaboration**
```
Use ai_team_collaborate to design a caching strategy for my API.
Mode: consensus. Context: FastAPI backend with 1000+ req/min.
```

**Example 4: Debug Help**
```
Use ai_team_debug to help fix this error: [paste error]
Project: /path/to/project
```

---

## 🔧 Troubleshooting

### **MCP Server Not Showing Up?**
1. Make sure Claude Desktop is completely closed (check Activity Monitor)
2. Restart Claude Desktop
3. Check the logs: `tail -f /tmp/ai_team_mcp.log`

### **Permission Errors?**
The MCP server needs access to:
- Your API keys (set in `~/.ai_secrets` or environment)
- Project directories you want to analyze

### **API Keys Not Found?**
Make sure you have API keys set:
```bash
# Check if secrets file exists
cat ~/.ai_secrets

# Or set environment variables:
export OPENAI_API_KEY="sk-..."
export GEMINI_API_KEY="..."
export ANTHROPIC_API_KEY="..."
```

---

## 📊 What Makes El Gringo Unique

1. **Multi-Agent Consensus** - Gets perspectives from multiple AIs, not just one
2. **Weighted Voting** - Different agents have different expertise (e.g., Grok is better at code, Gemini at docs)
3. **Memory System** - Remembers past conversations and learns from mistakes
4. **Mistake Prevention** - Won't repeat errors it made before
5. **Autonomous Fixing** - FredFix can scan and suggest fixes automatically
6. **Collaboration Modes**:
   - **Parallel** - All agents work at once (fast)
   - **Sequential** - Build on each other's answers (thorough)
   - **Consensus** - Multiple rounds until agreement (accurate)
   - **Debate** - Agents challenge each other (creative)
   - **Peer Review** - Code review mode
   - **Expert Panel** - Domain experts collaborate

---

## 🎯 Best Use Cases

**Use El Gringo when:**
- ✅ You need multiple perspectives on a complex problem
- ✅ You want security auditing with multiple scanners
- ✅ You're making architectural decisions (expert panel mode)
- ✅ You need to debug something tricky (multiple approaches)
- ✅ You want code review from different viewpoints

**Don't use El Gringo when:**
- ❌ Simple questions (use regular Claude, it's faster)
- ❌ You need very fast responses (multi-agent takes 20-60s)
- ❌ The task doesn't benefit from multiple perspectives

---

## 📝 Next Steps

1. **Restart Claude Desktop** to activate El Gringo
2. **Try a simple task** first (ai_team_ask with a question)
3. **Test on a real project** (ai_team_review on managers-dashboard)
4. **Explore collaboration modes** to see which fits your workflow

---

## 🔗 Resources

- **El Gringo GitHub:** (add your repo URL)
- **MCP Protocol:** https://modelcontextprotocol.io
- **Logs:** `/tmp/ai_team_mcp.log`
- **Config:** `~/Library/Application Support/Claude/claude_desktop_config.json`

---

**You now have a multi-agent AI team at your fingertips! 🚀**

Questions? Issues? The MCP server logs everything to `/tmp/ai_team_mcp.log`.
