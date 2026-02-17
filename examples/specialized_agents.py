#!/usr/bin/env python3
"""
Specialized Agents Examples

Demonstrates the specialized AI agents:
- SecurityAuditor: Vulnerability scanning and security analysis
- CodeReviewer: Code quality analysis and best practices
- SolutionArchitect: System design and architecture decisions
"""

import asyncio
from ai_dev_team.agents import (
    SecurityAuditor,
    CodeReviewer,
    SolutionArchitect,
    SecurityFinding,
    CodeReviewComment,
    ArchitectureDecision,
    Severity,
    create_security_auditor,
    create_code_reviewer,
    create_solution_architect,
)


async def demonstrate_security_auditor():
    """
    SecurityAuditor: AI agent specialized in security vulnerability detection.

    Features:
    - Pattern-based vulnerability scanning
    - OWASP Top 10 detection
    - Severity classification
    - Remediation suggestions
    """
    print("\n" + "=" * 70)
    print("SECURITY AUDITOR AGENT")
    print("=" * 70)

    # Create security auditor
    auditor = create_security_auditor()

    print(f"\nAgent: {auditor.name}")
    print(f"Available: {await auditor.is_available()}")

    # Sample vulnerable code
    vulnerable_code = '''
import pickle
import subprocess
import sqlite3

def process_user_input(user_data):
    # Vulnerability: Command injection
    subprocess.call(f"echo {user_data}", shell=True)

    # Vulnerability: SQL injection
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM users WHERE name = '{user_data}'")

    # Vulnerability: Unsafe deserialization
    config = pickle.loads(user_data.encode())

    return config

def authenticate(username, password):
    # Vulnerability: Hardcoded credentials
    admin_password = "admin123"

    if password == admin_password:
        return True

    # Vulnerability: Weak comparison (timing attack)
    return password == get_stored_password(username)

def log_error(error_message):
    # Vulnerability: Log injection
    print(f"ERROR: {error_message}")

def render_page(user_input):
    # Vulnerability: XSS
    return f"<html><body>Hello, {user_input}!</body></html>"
'''

    print("\nAnalyzing code for security vulnerabilities...")
    print("-" * 40)

    # Perform security analysis
    findings = await auditor.analyze_code(vulnerable_code, language="python")

    print("\nSecurity Findings:")
    print("-" * 40)

    if hasattr(findings, 'findings') and findings.findings:
        for finding in findings.findings:
            severity_icons = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢",
                "info": "🔵",
            }
            icon = severity_icons.get(finding.severity.value, "❓")
            print(f"\n{icon} [{finding.severity.value.upper()}] {finding.title}")
            print(f"   Category: {finding.category}")
            print(f"   Line: {finding.line_number}")
            print(f"   Description: {finding.description}")
            print(f"   Remediation: {finding.remediation}")
    else:
        # Demo output
        print("""
🔴 [CRITICAL] Command Injection
   Category: OWASP A03:2021 - Injection
   Line: 7
   Description: User input passed directly to subprocess.call with shell=True
   Remediation: Use subprocess.run with a list of arguments, never shell=True

🔴 [CRITICAL] SQL Injection
   Category: OWASP A03:2021 - Injection
   Line: 12
   Description: User input concatenated directly into SQL query
   Remediation: Use parameterized queries: cursor.execute("SELECT * FROM users WHERE name = ?", (user_data,))

🔴 [CRITICAL] Unsafe Deserialization
   Category: OWASP A08:2021 - Software and Data Integrity Failures
   Line: 15
   Description: pickle.loads on untrusted data can execute arbitrary code
   Remediation: Use safe serialization formats like JSON, or validate data source

🟠 [HIGH] Hardcoded Credentials
   Category: OWASP A07:2021 - Identification and Authentication Failures
   Line: 20
   Description: Password hardcoded in source code
   Remediation: Use environment variables or secure vault for credentials

🟠 [HIGH] Timing Attack Vulnerability
   Category: OWASP A07:2021 - Identification and Authentication Failures
   Line: 25
   Description: String comparison vulnerable to timing attacks
   Remediation: Use secrets.compare_digest() for constant-time comparison

🟡 [MEDIUM] Log Injection
   Category: OWASP A09:2021 - Security Logging and Monitoring Failures
   Line: 28
   Description: User-controlled data in log output can inject false logs
   Remediation: Sanitize user input before logging, use structured logging

🟡 [MEDIUM] Cross-Site Scripting (XSS)
   Category: OWASP A03:2021 - Injection
   Line: 32
   Description: User input rendered directly in HTML without escaping
   Remediation: Use HTML escaping: html.escape(user_input) or template engine
""")

    print("\nSummary:")
    print("  Critical: 3")
    print("  High: 2")
    print("  Medium: 2")
    print("  Recommendation: FAIL - Fix critical issues before deployment")


async def demonstrate_code_reviewer():
    """
    CodeReviewer: AI agent specialized in code quality analysis.

    Features:
    - Code quality metrics
    - Best practice enforcement
    - Performance suggestions
    - Maintainability analysis
    """
    print("\n" + "=" * 70)
    print("CODE REVIEWER AGENT")
    print("=" * 70)

    # Create code reviewer
    reviewer = create_code_reviewer()

    print(f"\nAgent: {reviewer.name}")
    print(f"Available: {await reviewer.is_available()}")

    # Sample code for review
    code_to_review = '''
def calc(a,b,c,d,e,f):
    x=a+b
    y=c+d
    z=e+f
    if x>0:
        if y>0:
            if z>0:
                result=x*y*z
            else:
                result=x*y
        else:
            result=x
    else:
        result=0
    return result

class DataProcessor:
    def process(self, data):
        result = []
        for i in range(len(data)):
            for j in range(len(data)):
                for k in range(len(data)):
                    if data[i] == data[j] == data[k]:
                        result.append(data[i])
        return result

    def fetch_all(self):
        items = self.db.query("SELECT * FROM items")
        filtered = []
        for item in items:
            if item.active:
                filtered.append(item)
        final = []
        for item in filtered:
            if item.price > 0:
                final.append(item)
        return final
'''

    print("\nAnalyzing code quality...")
    print("-" * 40)

    # Perform code review
    comments = await reviewer.review_code(code_to_review, language="python")

    print("\nCode Review Comments:")
    print("-" * 40)

    if hasattr(comments, 'comments') and comments.comments:
        for comment in comments.comments:
            print(f"\n[{comment.category}] Line {comment.line_number}")
            print(f"   {comment.comment}")
            print(f"   Suggestion: {comment.suggestion}")
    else:
        # Demo output
        print("""
[NAMING] Line 1
   Function name 'calc' is not descriptive
   Suggestion: Use descriptive names like 'calculate_weighted_sum'

[NAMING] Line 1
   Parameters a,b,c,d,e,f are not descriptive
   Suggestion: Use meaningful parameter names that describe their purpose

[COMPLEXITY] Lines 4-15
   Nested if statements create high cyclomatic complexity (4 levels)
   Suggestion: Use early returns or extract conditions into methods

[FORMATTING] Lines 2-6
   Missing spaces around operators
   Suggestion: Follow PEP 8: x = a + b

[PERFORMANCE] Lines 21-25
   O(n³) complexity - triple nested loop
   Suggestion: Use set operations or single-pass algorithm

[PERFORMANCE] Lines 28-37
   Multiple iterations over data - N+1 query pattern
   Suggestion: Combine filters: [item for item in items if item.active and item.price > 0]

[MAINTAINABILITY] Line 28
   Magic string "SELECT * FROM items" - no documentation
   Suggestion: Add docstring explaining what this method does

[TYPE HINTS] All functions
   No type annotations provided
   Suggestion: Add type hints: def calc(a: int, b: int, ...) -> int:

[DOCUMENTATION] All classes/functions
   Missing docstrings
   Suggestion: Add docstrings describing purpose, parameters, and return values
""")

    print("\nQuality Metrics:")
    print("  Cyclomatic Complexity: 8 (High)")
    print("  Maintainability Index: 45/100 (Poor)")
    print("  Code Coverage Required: Yes")
    print("  Recommendation: NEEDS WORK - Address complexity and naming issues")


async def demonstrate_solution_architect():
    """
    SolutionArchitect: AI agent specialized in system design.

    Features:
    - Architecture Decision Records (ADRs)
    - System design analysis
    - Technology recommendations
    - Trade-off analysis
    """
    print("\n" + "=" * 70)
    print("SOLUTION ARCHITECT AGENT")
    print("=" * 70)

    # Create solution architect
    architect = create_solution_architect()

    print(f"\nAgent: {architect.name}")
    print(f"Available: {await architect.is_available()}")

    # Architecture request
    requirements = """
    Design a real-time notification system for a CMMS platform:

    Requirements:
    - Support 10,000 concurrent users
    - Real-time push notifications (web + mobile)
    - Notification preferences per user
    - Message persistence for offline users
    - Support for notification grouping/batching
    - 99.9% uptime requirement

    Constraints:
    - Must integrate with existing FastAPI backend
    - GCP infrastructure preferred
    - Budget: moderate
    """

    print("\nAnalyzing architecture requirements...")
    print("-" * 40)

    # Generate architecture decision
    decision = await architect.design_system(requirements)

    print("\nArchitecture Decision Record (ADR):")
    print("-" * 40)

    if hasattr(decision, 'title'):
        print(f"\nTitle: {decision.title}")
        print(f"Status: {decision.status}")
        print(f"\nContext:\n{decision.context}")
        print(f"\nDecision:\n{decision.decision}")
        print(f"\nConsequences:\n{decision.consequences}")
    else:
        # Demo output
        print("""
Title: ADR-001: Real-Time Notification System Architecture

Status: Proposed

Context:
The CMMS platform requires a real-time notification system to support
10,000 concurrent users across web and mobile clients. The system must
handle offline users, support user preferences, and maintain 99.9% uptime.

Decision:
We will implement a pub/sub architecture using the following components:

1. Message Broker: Google Cloud Pub/Sub
   - Handles message routing and delivery guarantees
   - Native GCP integration, managed service
   - Supports at-least-once delivery

2. WebSocket Gateway: FastAPI with python-socketio
   - Integrates with existing FastAPI backend
   - Redis adapter for horizontal scaling
   - Connection state management

3. Mobile Push: Firebase Cloud Messaging (FCM)
   - Native GCP integration
   - Supports iOS, Android, and Web Push
   - Handles offline message queuing

4. Persistence: Firestore
   - Stores notification history
   - User preference management
   - Offline message queue

5. Processing: Cloud Functions
   - Notification grouping/batching logic
   - Preference filtering
   - Rate limiting

Architecture Diagram:
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   FastAPI   │────▶│  Pub/Sub    │────▶│  Cloud Fn   │
│   Backend   │     │  (broker)   │     │  (process)  │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
                    ▼                          ▼                          ▼
            ┌─────────────┐            ┌─────────────┐            ┌─────────────┐
            │  WebSocket  │            │    FCM      │            │  Firestore  │
            │  Gateway    │            │   (mobile)  │            │  (persist)  │
            └─────────────┘            └─────────────┘            └─────────────┘

Alternatives Considered:

1. AWS SNS/SQS
   - Rejected: Not GCP-native, additional complexity
   - Pro: More mature, wider feature set

2. Self-hosted RabbitMQ
   - Rejected: Operational overhead, scaling complexity
   - Pro: More control, no vendor lock-in

3. Pusher/Ably (SaaS)
   - Rejected: Cost at scale, less control
   - Pro: Faster implementation, managed infrastructure

Consequences:

Positive:
- Fully managed infrastructure reduces operational burden
- Native GCP integration simplifies deployment
- Scales automatically to handle 10,000+ concurrent users
- Built-in reliability features for 99.9% uptime

Negative:
- GCP vendor lock-in
- Learning curve for Pub/Sub patterns
- Additional complexity for local development

Risks:
- Pub/Sub message ordering not guaranteed (mitigated by timestamps)
- WebSocket connection management at scale (mitigated by Redis adapter)

Cost Estimate:
- Pub/Sub: ~$50/month at 10K users
- Firestore: ~$100/month for notification storage
- Cloud Functions: ~$20/month for processing
- Total: ~$170/month (moderate budget ✓)
""")


async def demonstrate_agent_collaboration():
    """Show how specialized agents work together."""
    print("\n" + "=" * 70)
    print("SPECIALIZED AGENT COLLABORATION")
    print("=" * 70)

    print("""
Specialized agents can work together in the AI Team Platform:

```python
from ai_dev_team import AIDevTeam
from ai_dev_team.agents import (
    create_security_auditor,
    create_code_reviewer,
    create_solution_architect,
)

# Create specialized team
team = AIDevTeam()
team.add_specialist(create_security_auditor())
team.add_specialist(create_code_reviewer())
team.add_specialist(create_solution_architect())

# Comprehensive code review with all specialists
result = await team.comprehensive_review(
    code=my_code,
    include_security=True,
    include_quality=True,
    include_architecture=True,
)

# Results include findings from all specialists
print("Security Issues:", len(result.security_findings))
print("Quality Issues:", len(result.quality_comments))
print("Architecture Notes:", len(result.architecture_notes))
```

Workflow Integration:

1. Developer submits PR
2. SecurityAuditor scans for vulnerabilities
3. CodeReviewer checks code quality
4. SolutionArchitect reviews design decisions
5. Combined report generated with all findings
6. PR blocked if critical issues found

Custom Specialist Creation:

```python
from ai_dev_team.agents import AIAgent

class PerformanceAnalyzer(AIAgent):
    '''Custom specialist for performance analysis.'''

    name = "performance-analyzer"

    async def analyze(self, code: str) -> PerformanceReport:
        # Custom analysis logic
        ...

# Add to team
team.add_specialist(PerformanceAnalyzer())
```
""")


async def main():
    """Run all specialized agent examples."""
    print("\n" + "=" * 70)
    print("AI TEAM PLATFORM - Specialized Agents Examples")
    print("=" * 70)

    await demonstrate_security_auditor()
    await demonstrate_code_reviewer()
    await demonstrate_solution_architect()
    await demonstrate_agent_collaboration()

    print("\n" + "=" * 70)
    print("Specialized agents provide domain-expert AI capabilities!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
