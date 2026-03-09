"""
Domain Knowledge - Specialized expertise for the AI team
"""

DOMAIN_EXPERTISE = {
    "frontend": {
        "technologies": ["React", "Vue", "Angular", "Svelte", "Next.js", "TypeScript", "Tailwind CSS"],
        "best_practices": [
            "Component-based architecture with single responsibility",
            "State management: Use React Context for simple, Redux/Zustand for complex",
            "Performance: Lazy loading, code splitting, memoization",
            "Accessibility: ARIA labels, semantic HTML, keyboard navigation",
            "Testing: Jest + React Testing Library for unit, Cypress for E2E",
            "CSS: Mobile-first responsive design, CSS-in-JS or Tailwind",
        ],
        "patterns": [
            "Container/Presentational components",
            "Custom hooks for reusable logic",
            "Error boundaries for graceful failures",
            "Optimistic UI updates",
            "Infinite scroll with virtualization",
        ],
        "common_mistakes": [
            "Prop drilling instead of context/state management",
            "Not memoizing expensive computations",
            "Blocking renders with synchronous operations",
            "Missing loading and error states",
            "Not handling race conditions in async operations",
        ],
    },

    "backend": {
        "technologies": ["Python/FastAPI", "Node.js/Express", "Go", "Rust", "GraphQL", "REST"],
        "best_practices": [
            "RESTful design: proper HTTP methods and status codes",
            "Input validation at API boundaries",
            "Rate limiting and throttling",
            "Structured logging with correlation IDs",
            "Health checks and graceful shutdown",
            "API versioning (/v1/, /v2/)",
        ],
        "patterns": [
            "Repository pattern for data access",
            "Service layer for business logic",
            "Middleware for cross-cutting concerns",
            "Circuit breaker for external services",
            "CQRS for read/write separation at scale",
        ],
        "common_mistakes": [
            "N+1 queries in ORM usage",
            "Not handling timeouts for external calls",
            "Exposing internal errors to clients",
            "Missing authentication on endpoints",
            "Synchronous operations that should be async",
        ],
    },

    "database": {
        "technologies": ["PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "DynamoDB"],
        "best_practices": [
            "Index columns used in WHERE, JOIN, ORDER BY",
            "Use connection pooling",
            "Normalize for writes, denormalize for reads",
            "Use transactions for data integrity",
            "Regular backups with tested restore procedures",
            "Query analysis with EXPLAIN",
        ],
        "patterns": [
            "Read replicas for scaling reads",
            "Sharding for horizontal scaling",
            "Event sourcing for audit trails",
            "Soft deletes with deleted_at timestamp",
            "Optimistic locking with version columns",
        ],
        "common_mistakes": [
            "Missing indexes on foreign keys",
            "SELECT * instead of specific columns",
            "Not using prepared statements (SQL injection)",
            "Storing passwords in plain text",
            "Not setting query timeouts",
        ],
    },

    "devops": {
        "technologies": ["Docker", "Kubernetes", "Terraform", "GitHub Actions", "AWS/GCP/Azure"],
        "best_practices": [
            "Infrastructure as Code (IaC)",
            "CI/CD pipelines for all deployments",
            "Blue-green or canary deployments",
            "Secrets management (never in code)",
            "Monitoring, alerting, and dashboards",
            "Disaster recovery plans tested regularly",
        ],
        "patterns": [
            "GitOps for declarative deployments",
            "Sidecar pattern for observability",
            "Service mesh for microservices",
            "Feature flags for safe rollouts",
            "Immutable infrastructure",
        ],
        "common_mistakes": [
            "Hardcoded secrets in Docker images",
            "No resource limits on containers",
            "Missing health checks in orchestration",
            "Not testing rollback procedures",
            "Ignoring security scanning in CI/CD",
        ],
    },

    "security": {
        "technologies": ["OAuth2", "JWT", "HTTPS/TLS", "OWASP", "Vault", "WAF"],
        "best_practices": [
            "HTTPS everywhere, HSTS headers",
            "Input validation and output encoding",
            "Least privilege access control",
            "Regular dependency security scans",
            "Security headers (CSP, X-Frame-Options)",
            "Audit logging for sensitive operations",
        ],
        "patterns": [
            "Defense in depth (multiple layers)",
            "Zero trust architecture",
            "JWT with short expiry + refresh tokens",
            "Role-based access control (RBAC)",
            "API gateway for centralized auth",
        ],
        "common_mistakes": [
            "SQL injection from unsanitized input",
            "XSS from unescaped user content",
            "CORS misconfiguration (allow *)",
            "Sensitive data in URLs or logs",
            "Using outdated dependencies with CVEs",
        ],
    },

    "architecture": {
        "technologies": ["Microservices", "Event-Driven", "Serverless", "Monolith", "CQRS"],
        "best_practices": [
            "Start monolith, extract services when needed",
            "Define clear service boundaries",
            "Async communication for loose coupling",
            "API contracts with versioning",
            "Document architecture decisions (ADRs)",
            "Design for failure and resilience",
        ],
        "patterns": [
            "Strangler fig for migrations",
            "Saga pattern for distributed transactions",
            "Event sourcing for audit and replay",
            "BFF (Backend for Frontend)",
            "Domain-Driven Design (DDD)",
        ],
        "common_mistakes": [
            "Distributed monolith (tight coupling)",
            "Premature microservices",
            "Shared databases between services",
            "Synchronous chains of service calls",
            "No circuit breakers for cascading failures",
        ],
    },

    "testing": {
        "technologies": ["Jest", "Pytest", "Cypress", "Playwright", "k6", "Postman"],
        "best_practices": [
            "Test pyramid: many unit, fewer integration, few E2E",
            "TDD for complex logic",
            "Mock external dependencies",
            "Test edge cases and error paths",
            "Performance testing before production",
            "Snapshot testing for UI regression",
        ],
        "patterns": [
            "Arrange-Act-Assert structure",
            "Factory pattern for test data",
            "Page Object Model for E2E",
            "Contract testing for APIs",
            "Chaos engineering for resilience",
        ],
        "common_mistakes": [
            "Testing implementation instead of behavior",
            "Flaky tests from timing issues",
            "Not testing error handling",
            "Missing integration tests",
            "No test data cleanup",
        ],
    },
}


def get_domain_context(domains: list) -> str:
    """Generate context string for specified domains"""
    context_parts = []

    for domain in domains:
        if domain in DOMAIN_EXPERTISE:
            expertise = DOMAIN_EXPERTISE[domain]
            context_parts.append(f"\n## {domain.upper()} EXPERTISE\n")
            context_parts.append(f"**Technologies**: {', '.join(expertise['technologies'])}\n")
            context_parts.append("**Best Practices**:\n" + "\n".join(f"- {bp}" for bp in expertise['best_practices']))
            context_parts.append("**Patterns**:\n" + "\n".join(f"- {p}" for p in expertise['patterns']))
            context_parts.append("**Avoid These Mistakes**:\n" + "\n".join(f"- {m}" for m in expertise['common_mistakes']))

    return "\n".join(context_parts)


def get_all_domains() -> list:
    """Get list of all available domains"""
    return list(DOMAIN_EXPERTISE.keys())
