"""Demonstrates how specialized agents work together."""


async def demonstrate_agent_collaboration():
    """Show how specialized agents work together."""
    print("\n" + "=" * 70)
    print("SPECIALIZED AGENT COLLABORATION")
    print("=" * 70)

    print("""
Specialized agents can work together in the AI Team Platform:

```python
from elgringo import AIDevTeam
from elgringo.agents import (
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
from elgringo.agents import AIAgent

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
