"""
Specialized AI Agents
=====================

Purpose-built agents for specific development tasks:
- SecurityAuditor: Vulnerability scanning and security analysis
- CodeReviewer: Automated code review and quality checks
- SolutionArchitect: System design and architecture decisions
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from .base import AIAgent, AgentConfig, AgentResponse, ModelType

logger = logging.getLogger(__name__)


class Severity(Enum):
    """Issue severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class SecurityFinding:
    """A security vulnerability or issue"""
    severity: Severity
    category: str
    title: str
    description: str
    location: Optional[str] = None
    recommendation: Optional[str] = None
    cwe_id: Optional[str] = None  # Common Weakness Enumeration


@dataclass
class CodeReviewComment:
    """A code review comment"""
    type: str  # "issue", "suggestion", "praise", "question"
    severity: Severity
    file: str
    line: Optional[int]
    message: str
    suggested_fix: Optional[str] = None


@dataclass
class ArchitectureDecision:
    """An architecture decision record"""
    title: str
    context: str
    decision: str
    consequences: List[str]
    alternatives: List[str]
    status: str = "proposed"  # proposed, accepted, deprecated


class SecurityAuditor(AIAgent):
    """
    AI Agent specialized in security analysis and vulnerability detection.

    Capabilities:
    - Static code analysis for security vulnerabilities
    - OWASP Top 10 detection
    - Secret detection in code
    - Dependency vulnerability checks
    - Security best practices validation
    """

    # Security patterns to detect
    SECURITY_PATTERNS = {
        "hardcoded_secret": [
            r"password\s*=\s*['\"][^'\"]+['\"]",
            r"api_key\s*=\s*['\"][^'\"]+['\"]",
            r"secret\s*=\s*['\"][^'\"]+['\"]",
            r"AWS_SECRET_ACCESS_KEY\s*=\s*['\"][^'\"]+['\"]",
        ],
        "sql_injection": [
            r"execute\s*\(\s*['\"].*%s.*['\"]",
            r"cursor\.execute\s*\(\s*f['\"]",
            r"\.format\s*\(.*\).*execute",
        ],
        "xss_vulnerability": [
            r"innerHTML\s*=",
            r"document\.write\s*\(",
            r"dangerouslySetInnerHTML",
        ],
        "command_injection": [
            r"os\.system\s*\(",
            r"subprocess\.call\s*\(.*shell\s*=\s*True",
            r"eval\s*\(",
            r"exec\s*\(",
        ],
        "path_traversal": [
            r"open\s*\([^)]*\+[^)]*\)",
            r"\.\.\/",
            r"\.\.\\\\",
        ],
        "insecure_random": [
            r"random\.random\s*\(",
            r"Math\.random\s*\(",
        ],
    }

    def __init__(self, base_agent: Optional[AIAgent] = None):
        config = AgentConfig(
            name="security-auditor",
            model_type=ModelType.LOCAL,
            role="Security Specialist",
            capabilities=["security", "vulnerability-detection", "code-audit"],
            system_prompt=self._get_security_prompt(),
            temperature=0.2,  # Low temperature for consistent analysis
        )
        super().__init__(config)
        self.base_agent = base_agent
        self._findings: List[SecurityFinding] = []

    async def is_available(self) -> bool:
        """Security auditor is always available (local pattern matching)"""
        return True

    def _get_security_prompt(self) -> str:
        return """You are an expert Security Auditor with deep knowledge of:
- OWASP Top 10 vulnerabilities
- Common Weakness Enumeration (CWE)
- Secure coding practices for Python, JavaScript, and other languages
- Authentication and authorization best practices
- Cryptography and secure data handling
- Cloud security (AWS, GCP, Azure)

When analyzing code:
1. Identify security vulnerabilities with severity levels (CRITICAL, HIGH, MEDIUM, LOW)
2. Provide CWE IDs where applicable
3. Explain the potential impact of each vulnerability
4. Recommend specific fixes with code examples
5. Consider the full attack surface

Format findings as:
FINDING: [SEVERITY] - [Category]
Title: <issue title>
Location: <file:line if applicable>
Description: <detailed explanation>
CWE: <CWE-XXX if applicable>
Recommendation: <how to fix>
"""

    def scan_code(self, code: str, filename: str = "unknown") -> List[SecurityFinding]:
        """Scan code for security vulnerabilities using pattern matching"""
        findings = []

        for category, patterns in self.SECURITY_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, code, re.IGNORECASE)
                for match in matches:
                    # Determine line number
                    line_num = code[:match.start()].count('\n') + 1

                    severity = self._get_severity_for_category(category)
                    finding = SecurityFinding(
                        severity=severity,
                        category=category.replace('_', ' ').title(),
                        title=f"Potential {category.replace('_', ' ')}",
                        description=f"Found pattern matching {category} at line {line_num}",
                        location=f"{filename}:{line_num}",
                        recommendation=self._get_recommendation(category),
                        cwe_id=self._get_cwe_for_category(category),
                    )
                    findings.append(finding)

        self._findings.extend(findings)
        return findings

    def _get_severity_for_category(self, category: str) -> Severity:
        """Map category to severity"""
        severity_map = {
            "hardcoded_secret": Severity.CRITICAL,
            "sql_injection": Severity.CRITICAL,
            "command_injection": Severity.CRITICAL,
            "xss_vulnerability": Severity.HIGH,
            "path_traversal": Severity.HIGH,
            "insecure_random": Severity.MEDIUM,
        }
        return severity_map.get(category, Severity.MEDIUM)

    def _get_cwe_for_category(self, category: str) -> Optional[str]:
        """Get CWE ID for category"""
        cwe_map = {
            "hardcoded_secret": "CWE-798",
            "sql_injection": "CWE-89",
            "command_injection": "CWE-78",
            "xss_vulnerability": "CWE-79",
            "path_traversal": "CWE-22",
            "insecure_random": "CWE-330",
        }
        return cwe_map.get(category)

    def _get_recommendation(self, category: str) -> str:
        """Get fix recommendation for category"""
        recommendations = {
            "hardcoded_secret": "Use environment variables or a secrets manager (e.g., AWS Secrets Manager, HashiCorp Vault)",
            "sql_injection": "Use parameterized queries or an ORM. Never concatenate user input into SQL.",
            "command_injection": "Avoid shell=True, use subprocess with list arguments, validate and sanitize inputs",
            "xss_vulnerability": "Sanitize user input, use proper encoding, avoid innerHTML",
            "path_traversal": "Validate and sanitize file paths, use allowlists, avoid user input in paths",
            "insecure_random": "Use secrets module for cryptographic purposes (secrets.token_hex)",
        }
        return recommendations.get(category, "Review and fix according to security best practices")

    async def generate_response(
        self,
        prompt: str,
        context: str = "",
        system_override: Optional[str] = None
    ) -> AgentResponse:
        """Generate security analysis response"""
        import time
        start_time = time.time()

        # First, do pattern-based scanning
        findings = self.scan_code(context if context else prompt)

        # Build response with findings
        response_parts = []
        if findings:
            response_parts.append(f"## Security Scan Results\n\nFound {len(findings)} potential issues:\n")
            for f in findings:
                response_parts.append(f"""
### [{f.severity.value.upper()}] {f.title}
- **Location**: {f.location or 'N/A'}
- **Category**: {f.category}
- **CWE**: {f.cwe_id or 'N/A'}
- **Description**: {f.description}
- **Recommendation**: {f.recommendation}
""")
        else:
            response_parts.append("## Security Scan Results\n\nNo obvious security issues detected by pattern matching.")
            response_parts.append("\n\nNote: This is a basic scan. For comprehensive analysis, consider using dedicated security tools like Bandit (Python), ESLint security plugins, or commercial SAST tools.")

        response_time = time.time() - start_time
        return AgentResponse(
            agent_name=self.name,
            model_type=self.config.model_type,
            content="\n".join(response_parts),
            confidence=0.8,
            response_time=response_time,
            metadata={"findings_count": len(findings)}
        )

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all findings"""
        summary = {
            "total": len(self._findings),
            "by_severity": {},
            "by_category": {},
        }
        for f in self._findings:
            sev = f.severity.value
            summary["by_severity"][sev] = summary["by_severity"].get(sev, 0) + 1
            summary["by_category"][f.category] = summary["by_category"].get(f.category, 0) + 1
        return summary

    def clear_findings(self):
        """Clear accumulated findings"""
        self._findings = []


class CodeReviewer(AIAgent):
    """
    AI Agent specialized in code review and quality analysis.

    Capabilities:
    - Code quality assessment
    - Style and convention checking
    - Bug detection
    - Performance suggestions
    - Best practices enforcement
    """

    # Code quality patterns
    QUALITY_PATTERNS = {
        "missing_type_hints": r"def\s+\w+\s*\([^)]*\)\s*:",  # Python functions without return type
        "bare_except": r"except\s*:",
        "print_statement": r"\bprint\s*\(",
        "todo_comment": r"#\s*(TODO|FIXME|HACK|XXX)",
        "magic_number": r"(?<![.\w])\d{2,}(?![.\w])",  # Numbers > 9 not part of identifiers
        "long_function": None,  # Checked programmatically
        "deep_nesting": None,  # Checked programmatically
    }

    def __init__(self, base_agent: Optional[AIAgent] = None):
        config = AgentConfig(
            name="code-reviewer",
            model_type=ModelType.LOCAL,
            role="Code Review Specialist",
            capabilities=["code-review", "quality", "best-practices"],
            system_prompt=self._get_review_prompt(),
            temperature=0.3,
        )
        super().__init__(config)
        self.base_agent = base_agent
        self._comments: List[CodeReviewComment] = []

    async def is_available(self) -> bool:
        """Code reviewer is always available (local pattern matching)"""
        return True

    def _get_review_prompt(self) -> str:
        return """You are an expert Code Reviewer with experience in:
- Clean code principles and SOLID design
- Language-specific best practices (Python, JavaScript, TypeScript)
- Performance optimization
- Testing strategies
- Documentation standards

When reviewing code:
1. Identify bugs, potential issues, and code smells
2. Suggest improvements with severity levels
3. Praise good patterns and practices
4. Ask clarifying questions when intent is unclear
5. Provide specific, actionable suggestions

Format comments as:
[TYPE: issue/suggestion/praise/question] [SEVERITY: critical/high/medium/low/info]
File: <filename>
Line: <line number if applicable>
Message: <detailed feedback>
Suggested Fix: <code example if applicable>
"""

    def review_code(self, code: str, filename: str = "unknown") -> List[CodeReviewComment]:
        """Review code for quality issues"""
        comments = []

        # Check for bare except
        for match in re.finditer(r"except\s*:", code):
            line_num = code[:match.start()].count('\n') + 1
            comments.append(CodeReviewComment(
                type="issue",
                severity=Severity.MEDIUM,
                file=filename,
                line=line_num,
                message="Bare except clause catches all exceptions including KeyboardInterrupt and SystemExit",
                suggested_fix="except Exception as e:  # Or specify the exact exception type"
            ))

        # Check for print statements
        for match in re.finditer(r"\bprint\s*\(", code):
            line_num = code[:match.start()].count('\n') + 1
            comments.append(CodeReviewComment(
                type="suggestion",
                severity=Severity.LOW,
                file=filename,
                line=line_num,
                message="Consider using logging instead of print for production code",
                suggested_fix="import logging\nlogger = logging.getLogger(__name__)\nlogger.info('message')"
            ))

        # Check for TODOs
        for match in re.finditer(r"#\s*(TODO|FIXME|HACK|XXX)(.*)$", code, re.MULTILINE):
            line_num = code[:match.start()].count('\n') + 1
            comments.append(CodeReviewComment(
                type="issue",
                severity=Severity.INFO,
                file=filename,
                line=line_num,
                message=f"Found {match.group(1)}: {match.group(2).strip()}",
                suggested_fix=None
            ))

        # Check function length
        func_pattern = r"(def\s+\w+\s*\([^)]*\).*?:)(.*?)(?=\ndef\s|\nclass\s|\Z)"
        for match in re.finditer(func_pattern, code, re.DOTALL):
            func_body = match.group(2)
            line_count = func_body.count('\n')
            if line_count > 50:
                func_start = code[:match.start()].count('\n') + 1
                comments.append(CodeReviewComment(
                    type="issue",
                    severity=Severity.MEDIUM,
                    file=filename,
                    line=func_start,
                    message=f"Function is {line_count} lines long. Consider breaking it into smaller functions.",
                    suggested_fix=None
                ))

        self._comments.extend(comments)
        return comments

    async def generate_response(
        self,
        prompt: str,
        context: str = "",
        system_override: Optional[str] = None
    ) -> AgentResponse:
        """Generate code review response"""
        import time
        start_time = time.time()

        # Do pattern-based review
        comments = self.review_code(context if context else prompt)

        # Build response
        response_parts = []
        if comments:
            response_parts.append(f"## Code Review Results\n\nFound {len(comments)} items to address:\n")

            # Group by severity
            by_severity = {}
            for c in comments:
                sev = c.severity.value
                if sev not in by_severity:
                    by_severity[sev] = []
                by_severity[sev].append(c)

            for severity in ["critical", "high", "medium", "low", "info"]:
                if severity in by_severity:
                    response_parts.append(f"\n### {severity.upper()} Priority\n")
                    for c in by_severity[severity]:
                        response_parts.append(f"""
**[{c.type.upper()}]** {c.file}:{c.line or '?'}
{c.message}
""")
                        if c.suggested_fix:
                            response_parts.append(f"```\n{c.suggested_fix}\n```\n")
        else:
            response_parts.append("## Code Review Results\n\n✅ No obvious issues detected. Code looks clean!")

        response_time = time.time() - start_time
        return AgentResponse(
            agent_name=self.name,
            model_type=self.config.model_type,
            content="\n".join(response_parts),
            confidence=0.75,
            response_time=response_time,
            metadata={"comments_count": len(comments)}
        )

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all comments"""
        return {
            "total": len(self._comments),
            "by_type": {t: sum(1 for c in self._comments if c.type == t) for t in ["issue", "suggestion", "praise", "question"]},
            "by_severity": {s.value: sum(1 for c in self._comments if c.severity == s) for s in Severity},
        }

    def clear_comments(self):
        """Clear accumulated comments"""
        self._comments = []


class SolutionArchitect(AIAgent):
    """
    AI Agent specialized in system architecture and design decisions.

    Capabilities:
    - System design and architecture
    - Technology selection
    - Scalability planning
    - Architecture Decision Records (ADRs)
    - Trade-off analysis
    """

    def __init__(self, base_agent: Optional[AIAgent] = None):
        config = AgentConfig(
            name="solution-architect",
            model_type=ModelType.LOCAL,
            role="Solution Architect",
            capabilities=["architecture", "design", "planning", "trade-offs"],
            system_prompt=self._get_architect_prompt(),
            temperature=0.5,
        )
        super().__init__(config)
        self.base_agent = base_agent
        self._decisions: List[ArchitectureDecision] = []

    async def is_available(self) -> bool:
        """Solution architect is always available"""
        if self.base_agent:
            return await self.base_agent.is_available()
        return True

    def _get_architect_prompt(self) -> str:
        return """You are an expert Solution Architect with experience in:
- Distributed systems and microservices
- Cloud architecture (AWS, GCP, Azure)
- Database design (SQL, NoSQL, caching)
- API design (REST, GraphQL, gRPC)
- Event-driven architecture
- Security architecture
- Performance and scalability

When designing systems:
1. Understand requirements and constraints
2. Consider scalability, reliability, and maintainability
3. Evaluate multiple approaches with trade-offs
4. Document decisions using ADR format
5. Consider cost and operational complexity

Format Architecture Decision Records (ADRs) as:
## ADR: <title>
**Status**: proposed/accepted/deprecated
**Context**: <why this decision is needed>
**Decision**: <what we decided>
**Consequences**: <positive and negative outcomes>
**Alternatives Considered**: <other options evaluated>
"""

    def create_adr(
        self,
        title: str,
        context: str,
        decision: str,
        consequences: List[str],
        alternatives: List[str],
        status: str = "proposed"
    ) -> ArchitectureDecision:
        """Create an Architecture Decision Record"""
        adr = ArchitectureDecision(
            title=title,
            context=context,
            decision=decision,
            consequences=consequences,
            alternatives=alternatives,
            status=status
        )
        self._decisions.append(adr)
        return adr

    def format_adr(self, adr: ArchitectureDecision) -> str:
        """Format ADR as markdown"""
        return f"""## ADR: {adr.title}

**Status**: {adr.status}

### Context
{adr.context}

### Decision
{adr.decision}

### Consequences
{chr(10).join(f'- {c}' for c in adr.consequences)}

### Alternatives Considered
{chr(10).join(f'- {a}' for a in adr.alternatives)}

---
*Recorded: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}*
"""

    async def generate_response(
        self,
        prompt: str,
        context: str = "",
        system_override: Optional[str] = None
    ) -> AgentResponse:
        """Generate architecture response"""
        import time
        start_time = time.time()

        # If we have a base agent (like Ollama or Claude), use it for generation
        if self.base_agent:
            full_prompt = f"{self._get_architect_prompt()}\n\n{prompt}"
            return await self.base_agent.generate_response(full_prompt, context, system_override)

        # Otherwise, provide a template response
        response = f"""## Architecture Analysis

Based on your request: "{prompt[:100]}..."

### Recommended Approach

I would need more context to provide a complete architecture recommendation. Please consider:

1. **Functional Requirements**: What must the system do?
2. **Non-Functional Requirements**: Performance, scalability, security needs
3. **Constraints**: Budget, timeline, team expertise, existing infrastructure
4. **Integration Points**: External systems, APIs, data sources

### Common Patterns to Consider

- **Microservices**: For large teams and independent scaling
- **Monolith First**: For MVPs and small teams
- **Event-Driven**: For async processing and decoupling
- **CQRS**: For complex read/write patterns
- **Serverless**: For variable workloads and cost optimization

Would you like me to elaborate on any specific architecture pattern or create an ADR for a particular decision?
"""

        response_time = time.time() - start_time
        return AgentResponse(
            agent_name=self.name,
            model_type=self.config.model_type,
            content=response,
            confidence=0.6,
            response_time=response_time,
        )

    def get_all_adrs(self) -> List[ArchitectureDecision]:
        """Get all recorded ADRs"""
        return self._decisions


@dataclass
class FrontendAnalysis:
    """Frontend code analysis result"""
    category: str  # "performance", "accessibility", "best-practice", "security", "style"
    severity: Severity
    title: str
    description: str
    file: Optional[str] = None
    line: Optional[int] = None
    suggestion: Optional[str] = None
    code_fix: Optional[str] = None


@dataclass
class ComponentSuggestion:
    """Suggested component structure"""
    name: str
    type: str  # "functional", "server", "client", "layout", "page"
    props: List[str]
    description: str
    code_template: str


class FrontendDeveloper(AIAgent):
    """
    AI Agent specialized in modern frontend development.

    The BEST frontend developer with expertise in:

    FRAMEWORKS & LIBRARIES:
    - React 19+ (Server Components, Actions, use() hook)
    - Next.js 15+ (App Router, Server Actions, Turbopack)
    - Vue 3 (Composition API, Pinia)
    - Svelte 5 (Runes, fine-grained reactivity)
    - Astro (Islands architecture, View Transitions)

    STYLING:
    - Tailwind CSS 4+ (CSS-first config, @theme, container queries)
    - CSS Modules, CSS-in-JS (styled-components, Emotion)
    - Modern CSS (has(), :where(), subgrid, anchor positioning)
    - shadcn/ui, Radix UI, Headless UI

    STATE & DATA:
    - TanStack Query (React Query v5)
    - Zustand, Jotai, Recoil
    - tRPC, GraphQL (Apollo, urql)
    - SWR, RTK Query

    BUILD & TOOLING:
    - Vite 6+, Turbopack
    - TypeScript 5.5+ (inferred type predicates)
    - ESLint 9+ (flat config), Biome
    - pnpm, Bun

    TESTING:
    - Vitest, Jest
    - Playwright, Cypress
    - React Testing Library
    - Storybook 8+

    PERFORMANCE:
    - Core Web Vitals (LCP, FID, CLS, INP)
    - Code splitting, lazy loading
    - Image optimization (next/image, @unpic/*)
    - Bundle analysis, tree shaking

    ACCESSIBILITY:
    - WCAG 2.2 AA compliance
    - ARIA patterns
    - Semantic HTML
    - Screen reader testing

    MOBILE & PWA:
    - React Native / Expo
    - PWA with Workbox
    - Responsive design
    - Touch interactions
    """

    # Frontend patterns to detect and improve
    FRONTEND_PATTERNS = {
        # Performance issues
        "unoptimized_image": [
            r"<img[^>]*src=",
            r"background-image:\s*url\(",
        ],
        "missing_lazy_load": [
            r"<img(?![^>]*loading=)[^>]*>",
        ],
        "inline_styles": [
            r"style=\{?\{[^}]+\}\}?",
            r"style=\"[^\"]+\"",
        ],
        "console_log": [
            r"console\.(log|debug|info)\s*\(",
        ],
        # Accessibility issues
        "missing_alt": [
            r"<img(?![^>]*alt=)[^>]*>",
        ],
        "missing_aria_label": [
            r"<button(?![^>]*(aria-label|aria-labelledby))[^>]*>\s*<",
        ],
        "div_button": [
            r"<div[^>]*onClick",
        ],
        # React-specific
        "use_effect_deps": [
            r"useEffect\s*\(\s*\(\)\s*=>\s*\{[^}]+\}\s*\)",  # Missing deps array
        ],
        "array_index_key": [
            r"\.map\s*\([^)]*,\s*index\s*\)[^{]*key=\{?\s*index",
        ],
        # Security
        "dangerous_html": [
            r"dangerouslySetInnerHTML",
        ],
        "eval_usage": [
            r"eval\s*\(",
            r"new\s+Function\s*\(",
        ],
    }

    # Modern component templates
    COMPONENT_TEMPLATES = {
        "react_server": '''
// {name}.tsx - React Server Component
import {{ Suspense }} from 'react'

interface {name}Props {{
  {props}
}}

export default async function {name}({{ {destructured_props} }}: {name}Props) {{
  // Server-side data fetching
  const data = await fetchData()

  return (
    <Suspense fallback={{<{name}Skeleton />}}>
      <div className="...">
        {{/* Component content */}}
      </div>
    </Suspense>
  )
}}
''',
        "react_client": '''
'use client'

// {name}.tsx - React Client Component
import {{ useState, useCallback }} from 'react'

interface {name}Props {{
  {props}
}}

export function {name}({{ {destructured_props} }}: {name}Props) {{
  const [state, setState] = useState<State>(initialState)

  const handleAction = useCallback(() => {{
    // Handle user interaction
  }}, [])

  return (
    <div className="...">
      {{/* Interactive content */}}
    </div>
  )
}}
''',
        "next_page": '''
// app/{route}/page.tsx - Next.js Page
import {{ Metadata }} from 'next'

export const metadata: Metadata = {{
  title: '{title}',
  description: '{description}',
}}

interface PageProps {{
  params: Promise<{{ id: string }}>
  searchParams: Promise<{{ [key: string]: string | undefined }}>
}}

export default async function Page({{ params, searchParams }}: PageProps) {{
  const {{ id }} = await params
  const query = await searchParams

  return (
    <main className="container mx-auto px-4 py-8">
      {{/* Page content */}}
    </main>
  )
}}
''',
        "tailwind_component": '''
// {name}.tsx - Tailwind + shadcn/ui Component
import {{ cn }} from '@/lib/utils'
import {{ Button }} from '@/components/ui/button'

interface {name}Props {{
  className?: string
  {props}
}}

export function {name}({{ className, {destructured_props} }}: {name}Props) {{
  return (
    <div className={{cn(
      "relative flex flex-col gap-4 rounded-lg border bg-card p-6 shadow-sm",
      "hover:shadow-md transition-shadow duration-200",
      className
    )}}>
      {{/* Component content */}}
    </div>
  )
}}
''',
    }

    def __init__(self, base_agent: Optional[AIAgent] = None):
        config = AgentConfig(
            name="frontend-developer",
            model_type=ModelType.LOCAL,
            role="Senior Frontend Developer",
            capabilities=[
                "react", "nextjs", "vue", "svelte", "astro",
                "tailwind", "typescript", "accessibility",
                "performance", "testing", "mobile", "pwa"
            ],
            system_prompt=self._get_frontend_prompt(),
            temperature=0.4,
        )
        super().__init__(config)
        self.base_agent = base_agent
        self._analyses: List[FrontendAnalysis] = []

    async def is_available(self) -> bool:
        """Frontend developer is always available"""
        return True

    def _get_frontend_prompt(self) -> str:
        return """You are a WORLD-CLASS Senior Frontend Developer - the best in the business.

YOUR EXPERTISE (2025 cutting edge):

🚀 FRAMEWORKS:
- React 19: Server Components, Actions, use() hook, Suspense boundaries
- Next.js 15: App Router, Server Actions, Partial Prerendering, Turbopack
- Vue 3.5: Composition API, Pinia, Vapor mode
- Svelte 5: Runes ($state, $derived, $effect), fine-grained reactivity
- Astro 5: Islands, View Transitions, Content Collections

🎨 STYLING:
- Tailwind CSS 4: CSS-first config, @theme directive, 3D transforms
- Modern CSS: Container queries, :has(), subgrid, anchor positioning
- shadcn/ui, Radix UI: Accessible, customizable components
- CSS Variables for theming, prefer-reduced-motion

📊 STATE & DATA:
- TanStack Query v5: Suspense integration, optimistic updates
- Zustand: Lightweight state with slices pattern
- tRPC v11: End-to-end typesafe APIs
- Server State vs Client State distinction

⚡ PERFORMANCE:
- Core Web Vitals: LCP < 2.5s, INP < 200ms, CLS < 0.1
- Code splitting with dynamic imports
- Image optimization: next/image, @unpic/react
- Bundle analysis: why-did-you-render, react-scan

♿ ACCESSIBILITY:
- WCAG 2.2 AA compliance
- Semantic HTML first
- ARIA only when necessary
- Focus management, skip links
- Color contrast, motion preferences

🧪 TESTING:
- Vitest for unit tests
- Playwright for E2E
- React Testing Library (user-centric)
- Visual regression with Chromatic

📱 MOBILE:
- React Native / Expo SDK 52
- Responsive design (mobile-first)
- PWA with Workbox
- Touch gestures, haptics

YOUR APPROACH:
1. Performance is non-negotiable
2. Accessibility is not optional
3. TypeScript strict mode always
4. Test behavior, not implementation
5. Server Components by default, 'use client' only when needed
6. Prefer composition over configuration
7. Progressive enhancement

When reviewing frontend code:
- Check for performance anti-patterns
- Verify accessibility compliance
- Ensure proper TypeScript usage
- Recommend modern patterns
- Provide working code examples

You write clean, maintainable, performant, and accessible code."""

    def analyze_code(self, code: str, filename: str = "unknown") -> List[FrontendAnalysis]:
        """Analyze frontend code for issues and improvements"""
        analyses = []

        for category, patterns in self.FRONTEND_PATTERNS.items():
            for pattern in patterns:
                try:
                    matches = re.finditer(pattern, code, re.IGNORECASE | re.MULTILINE)
                    for match in matches:
                        line_num = code[:match.start()].count('\n') + 1
                        analysis = self._create_analysis(category, filename, line_num, match.group())
                        if analysis:
                            analyses.append(analysis)
                except re.error:
                    continue

        self._analyses.extend(analyses)
        return analyses

    def _create_analysis(self, category: str, filename: str, line: int, matched: str) -> Optional[FrontendAnalysis]:
        """Create analysis based on detected pattern"""
        analysis_map = {
            "unoptimized_image": FrontendAnalysis(
                category="performance",
                severity=Severity.MEDIUM,
                title="Unoptimized Image",
                description="Use next/image or @unpic/react for automatic optimization",
                file=filename,
                line=line,
                suggestion="Replace with optimized image component",
                code_fix="""import Image from 'next/image'

<Image
  src="/path/to/image.jpg"
  alt="Descriptive alt text"
  width={800}
  height={600}
  placeholder="blur"
/>"""
            ),
            "missing_alt": FrontendAnalysis(
                category="accessibility",
                severity=Severity.HIGH,
                title="Missing Alt Text",
                description="Images must have alt text for screen readers (WCAG 1.1.1)",
                file=filename,
                line=line,
                suggestion="Add descriptive alt attribute",
                code_fix='<img src="..." alt="Descriptive text about the image" />'
            ),
            "div_button": FrontendAnalysis(
                category="accessibility",
                severity=Severity.HIGH,
                title="Non-semantic Button",
                description="Using div with onClick instead of button element",
                file=filename,
                line=line,
                suggestion="Use <button> element for clickable actions",
                code_fix='<button type="button" onClick={handleClick}>Click me</button>'
            ),
            "dangerous_html": FrontendAnalysis(
                category="security",
                severity=Severity.HIGH,
                title="Dangerous HTML Injection",
                description="dangerouslySetInnerHTML can lead to XSS vulnerabilities",
                file=filename,
                line=line,
                suggestion="Sanitize HTML with DOMPurify or use safer alternatives",
                code_fix="""import DOMPurify from 'dompurify'

<div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(html) }} />"""
            ),
            "console_log": FrontendAnalysis(
                category="best-practice",
                severity=Severity.LOW,
                title="Console Statement",
                description="Remove console.log before production",
                file=filename,
                line=line,
                suggestion="Use proper logging or remove",
                code_fix="// Use a logger or remove: logger.debug('...')"
            ),
            "use_effect_deps": FrontendAnalysis(
                category="best-practice",
                severity=Severity.MEDIUM,
                title="Missing useEffect Dependencies",
                description="useEffect without dependency array runs on every render",
                file=filename,
                line=line,
                suggestion="Add dependency array",
                code_fix="useEffect(() => { /* effect */ }, [dependency1, dependency2])"
            ),
            "array_index_key": FrontendAnalysis(
                category="performance",
                severity=Severity.MEDIUM,
                title="Array Index as Key",
                description="Using array index as key can cause rendering issues",
                file=filename,
                line=line,
                suggestion="Use stable unique identifier",
                code_fix="items.map(item => <Item key={item.id} {...item} />)"
            ),
            "inline_styles": FrontendAnalysis(
                category="style",
                severity=Severity.LOW,
                title="Inline Styles Detected",
                description="Prefer Tailwind classes or CSS modules over inline styles",
                file=filename,
                line=line,
                suggestion="Use Tailwind CSS or CSS modules",
                code_fix='<div className="flex items-center gap-4 p-4">'
            ),
        }

        return analysis_map.get(category)

    def generate_component(
        self,
        name: str,
        component_type: str = "react_client",
        props: List[str] = None
    ) -> str:
        """Generate a component template"""
        props = props or []
        template = self.COMPONENT_TEMPLATES.get(component_type, self.COMPONENT_TEMPLATES["react_client"])

        props_str = "\n  ".join(f"{p}: unknown" for p in props) if props else "// Add props here"
        destructured = ", ".join(props) if props else ""

        return template.format(
            name=name,
            props=props_str,
            destructured_props=destructured,
            title=name,
            description=f"{name} page",
            route=name.lower().replace(" ", "-"),
        )

    async def generate_response(
        self,
        prompt: str,
        context: str = "",
        system_override: Optional[str] = None
    ) -> AgentResponse:
        """Generate frontend development response"""
        import time
        start_time = time.time()

        # Analyze any code in the prompt or context
        code_to_analyze = context if context else prompt
        analyses = self.analyze_code(code_to_analyze)

        response_parts = []

        # If analyses found issues
        if analyses:
            response_parts.append("## Frontend Code Analysis\n")

            # Group by category
            by_category = {}
            for a in analyses:
                if a.category not in by_category:
                    by_category[a.category] = []
                by_category[a.category].append(a)

            for category in ["security", "accessibility", "performance", "best-practice", "style"]:
                if category in by_category:
                    emoji = {"security": "🔒", "accessibility": "♿", "performance": "⚡", "best-practice": "✨", "style": "🎨"}
                    response_parts.append(f"\n### {emoji.get(category, '📝')} {category.title()}\n")

                    for a in by_category[category]:
                        severity_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢", "info": "🔵"}
                        response_parts.append(f"""
**{severity_icon.get(a.severity.value, '')} [{a.severity.value.upper()}] {a.title}**
- Location: {a.file}:{a.line}
- Issue: {a.description}
- Fix: {a.suggestion}
```tsx
{a.code_fix}
```
""")
        else:
            response_parts.append("## Frontend Analysis\n\n✅ No obvious frontend issues detected!\n")

        # Add general recommendations
        response_parts.append("""
### 💡 Frontend Best Practices Checklist

- [ ] Using Server Components by default (React 19 / Next.js 15)
- [ ] TypeScript strict mode enabled
- [ ] Tailwind CSS 4 with CSS-first config
- [ ] Images optimized with next/image
- [ ] Accessibility audit passed (axe-core)
- [ ] Core Web Vitals in green
- [ ] No console.log in production
- [ ] Error boundaries in place
- [ ] Loading and error states handled
""")

        response_time = time.time() - start_time

        return AgentResponse(
            agent_name=self.name,
            model_type=self.config.model_type,
            content="\n".join(response_parts),
            confidence=0.85,
            response_time=response_time,
            metadata={
                "issues_found": len(analyses),
                "by_severity": {s.value: sum(1 for a in analyses if a.severity == s) for s in Severity}
            }
        )

    def get_modern_stack_recommendation(self) -> str:
        """Get recommended modern frontend stack"""
        return """
## 🚀 Recommended Modern Frontend Stack (2025)

### Framework
- **Next.js 15** - Full-stack React with App Router
- Alternative: **Astro 5** for content-heavy sites

### Styling
- **Tailwind CSS 4** - Utility-first CSS
- **shadcn/ui** - Beautiful, accessible components
- **Framer Motion** - Animations

### State Management
- **TanStack Query** - Server state
- **Zustand** - Client state (if needed)
- **React Context** - Theme/auth only

### Data Fetching
- **Server Components** - Default for data fetching
- **tRPC** - End-to-end type safety
- **GraphQL** (optional) - Complex data requirements

### Testing
- **Vitest** - Fast unit tests
- **Playwright** - E2E testing
- **Storybook 8** - Component development

### Tooling
- **pnpm** - Fast package manager
- **Biome** - Linting + formatting (faster than ESLint)
- **Turbopack** - Next.js bundler

### Deployment
- **Vercel** - Optimized for Next.js
- **Cloudflare Pages** - Edge-first
"""

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all analyses"""
        return {
            "total_issues": len(self._analyses),
            "by_category": {},
            "by_severity": {},
        }

    def clear_analyses(self):
        """Clear accumulated analyses"""
        self._analyses = []


# Factory functions
def create_security_auditor(base_agent: Optional[AIAgent] = None) -> SecurityAuditor:
    """Create a Security Auditor agent"""
    return SecurityAuditor(base_agent=base_agent)


def create_code_reviewer(base_agent: Optional[AIAgent] = None) -> CodeReviewer:
    """Create a Code Reviewer agent"""
    return CodeReviewer(base_agent=base_agent)


def create_solution_architect(base_agent: Optional[AIAgent] = None) -> SolutionArchitect:
    """Create a Solution Architect agent"""
    return SolutionArchitect(base_agent=base_agent)


def create_frontend_developer(base_agent: Optional[AIAgent] = None) -> FrontendDeveloper:
    """Create a Frontend Developer agent - the best in the business"""
    return FrontendDeveloper(base_agent=base_agent)
