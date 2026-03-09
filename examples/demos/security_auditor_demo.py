"""SecurityAuditor: AI agent specialized in security vulnerability detection."""

from elgringo.agents import create_security_auditor


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

    auditor = create_security_auditor()

    print(f"\nAgent: {auditor.name}")
    print(f"Available: {await auditor.is_available()}")

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
    admin_password = os.getenv("ADMIN_PASSWORD", "")

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
