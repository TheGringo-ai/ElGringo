"""
Firebase-Specific Code Validator
================================

Validates Firebase/Firestore code for:
- Security issues
- Performance anti-patterns
- Best practice violations
"""

import re

from .code_validator import ValidationResult, ValidationWarning


class FirebaseValidator:
    """Validator for Firebase/Firestore specific code patterns."""

    # Security rule patterns to flag
    SECURITY_PATTERNS = [
        # Overly permissive rules
        (r'allow\s+(read|write):\s*if\s+true\s*;?',
         "Overly permissive security rule - allows all {0}",
         "Add proper authentication checks (request.auth != null)"),

        # Missing authentication
        (r'allow\s+(read|write).*;\s*$(?!.*request\.auth)',
         "Security rule may be missing authentication check",
         "Consider adding 'request.auth != null' to your rules"),
    ]

    # Code anti-patterns
    CODE_PATTERNS = [
        # Missing await on Firestore operations
        (r'(?<!await\s)(?:db\.|collection\().*\.(add|set|update|delete)\(',
         "Firestore write operation may be missing 'await'",
         "Add 'await' before the operation to ensure it completes before continuing"),

        # Missing await on get
        (r'(?<!await\s)(?:db\.|doc\().*\.get\(\)',
         "Firestore get operation may be missing 'await'",
         "Add 'await' to ensure the data is retrieved before using it"),

        # Using forEach with async (doesn't wait)
        (r'\.forEach\s*\(\s*async',
         "Using forEach with async - operations won't be awaited",
         "Use 'for...of' loop or Promise.all() with map() instead"),

        # Not using batch for bulk operations
        (r'for\s*\([^)]+\)\s*\{[^}]*\.(set|update|delete)\(',
         "Loop with individual Firestore writes - consider using batch",
         "Use batch writes for better performance with multiple operations"),

        # Missing error handling on Firestore operations
        (r'await\s+(?:db\.|collection\().*\.(add|set|update|delete|get)\([^)]*\)(?!\s*\.catch|\s*\)\s*\.catch)',
         "Firestore operation without error handling",
         "Wrap in try/catch or add .catch() to handle potential errors"),

        # Using collection() without proper reference
        (r"collection\(['\"][^'\"]+['\"]\)\.doc\(['\"][^'\"]+['\"]\)\.collection\(['\"][^'\"]+['\"]\)\.doc\(['\"][^'\"]+['\"]\)\.collection",
         "Deeply nested collection references",
         "Consider restructuring data or using collection group queries"),
    ]

    # Performance patterns
    PERFORMANCE_PATTERNS = [
        # Not limiting queries
        (r'\.where\([^)]+\)(?!.*\.limit\()',
         "Query without limit() - may return excessive data",
         "Add .limit() to queries to prevent retrieving too many documents"),

        # Using get() in a loop without batching
        (r'for\s*\([^)]+\)\s*\{[^}]*\.get\(',
         "Multiple get() calls in a loop",
         "Use getAll() or batch get for better performance"),

        # Storing large arrays that get updated frequently
        (r'arrayUnion|arrayRemove',
         "Array operations detected - ensure arrays don't grow unbounded",
         "Consider using subcollections for large or frequently updated arrays"),

        # No index hint in composite query
        (r'\.where\([^)]+\)\.where\([^)]+\)(?!.*\.orderBy)',
         "Composite query may need an index",
         "Ensure composite indexes are created for multi-field queries"),
    ]

    # Security rules specific patterns
    RULES_PATTERNS = [
        # Allow all authenticated
        (r'allow\s+write:\s*if\s+request\.auth\s*!=\s*null\s*;?\s*$',
         "Rule allows any authenticated user to write",
         "Consider adding ownership checks (request.auth.uid == userId)"),

        # No data validation
        (r'allow\s+(create|update):[^}]+(?!request\.resource\.data)',
         "Write rule without data validation",
         "Validate incoming data with request.resource.data checks"),

        # Using == true in rules (unnecessary)
        (r'==\s*true',
         "Unnecessary '== true' comparison in security rule",
         "Just use the boolean expression directly"),
    ]

    def __init__(self):
        self._all_patterns = (
            [('security', p, m, s) for p, m, s in self.SECURITY_PATTERNS] +
            [('code', p, m, s) for p, m, s in self.CODE_PATTERNS] +
            [('performance', p, m, s) for p, m, s in self.PERFORMANCE_PATTERNS]
        )

    def validate(self, code: str, context: str = None) -> ValidationResult:
        """
        Validate Firebase/Firestore code.

        Args:
            code: Code to validate
            context: Optional context about the code's purpose

        Returns:
            ValidationResult with warnings and suggestions
        """
        result = ValidationResult(valid=True, language="firebase")

        # Detect if this is security rules
        is_security_rules = 'rules_version' in code or 'service cloud.firestore' in code

        if is_security_rules:
            self._validate_security_rules(code, result)
        else:
            self._validate_code(code, result)

        result.validators_run.append("firebase")
        return result

    def _validate_security_rules(self, code: str, result: ValidationResult):
        """Validate Firestore security rules."""
        # Check for overly permissive rules
        for pattern, message, suggestion in self.SECURITY_PATTERNS:
            matches = re.finditer(pattern, code, re.MULTILINE)
            for match in matches:
                # Get line number
                line_num = code[:match.start()].count('\n') + 1

                # Format message if needed
                msg = message.format(match.group(1)) if '{0}' in message else message

                result.warnings.append(ValidationWarning(
                    warning_type="security",
                    message=msg,
                    line=line_num,
                    suggestion=suggestion,
                ))

        # Check rules-specific patterns
        for pattern, message, suggestion in self.RULES_PATTERNS:
            matches = re.finditer(pattern, code, re.MULTILINE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1

                result.warnings.append(ValidationWarning(
                    warning_type="security",
                    message=message,
                    line=line_num,
                    suggestion=suggestion,
                ))

        # Check for missing rules
        if 'match /databases/{database}/documents' in code:
            if 'match /' not in code.split('match /databases/{database}/documents')[1]:
                result.warnings.append(ValidationWarning(
                    warning_type="security",
                    message="Security rules appear to have no collection matches defined",
                    suggestion="Add match rules for your collections",
                ))

    def _validate_code(self, code: str, result: ValidationResult):
        """Validate Firebase application code."""
        # Check code patterns
        for category, pattern, message, suggestion in self._all_patterns:
            if category == 'security':
                continue  # Skip security rule patterns for regular code

            matches = re.finditer(pattern, code, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                # Get line number
                line_num = code[:match.start()].count('\n') + 1

                result.warnings.append(ValidationWarning(
                    warning_type=category,
                    message=message,
                    line=line_num,
                    suggestion=suggestion,
                ))

        # Check for performance patterns
        for pattern, message, suggestion in self.PERFORMANCE_PATTERNS:
            matches = re.finditer(pattern, code, re.MULTILINE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1

                result.warnings.append(ValidationWarning(
                    warning_type="performance",
                    message=message,
                    line=line_num,
                    suggestion=suggestion,
                ))

        # Additional context-aware checks
        self._check_initialization(code, result)
        self._check_transaction_usage(code, result)

    def _check_initialization(self, code: str, result: ValidationResult):
        """Check Firebase initialization patterns."""
        # Check for missing initialization
        if ('db.collection' in code or 'firestore()' in code) and 'initializeApp' not in code:
            if 'import' in code:  # Only warn if this looks like a complete file
                result.suggestions.append(
                    "Ensure Firebase is initialized before using Firestore"
                )

        # Check for multiple initializations
        init_count = len(re.findall(r'initializeApp\(', code))
        if init_count > 1:
            result.warnings.append(ValidationWarning(
                warning_type="code",
                message="Multiple initializeApp() calls detected",
                suggestion="Initialize Firebase only once, typically at app startup",
            ))

    def _check_transaction_usage(self, code: str, result: ValidationResult):
        """Check transaction usage patterns."""
        # Check for transactions without proper error handling
        if 'runTransaction' in code or '@firestore.transactional' in code:
            if 'catch' not in code and 'except' not in code:
                result.warnings.append(ValidationWarning(
                    warning_type="code",
                    message="Transaction without error handling",
                    suggestion="Transactions can fail and should be wrapped in try/catch",
                ))

        # Check for reads outside transaction in transaction function
        if 'runTransaction' in code:
            # Look for .get() calls that might be outside the transaction context
            trans_match = re.search(r'runTransaction\s*\([^)]*,\s*async\s*\([^)]*\)\s*=>\s*\{', code)
            if trans_match:
                trans_body = code[trans_match.end():]
                # Check if there are .get() calls without transaction parameter
                if '.get()' in trans_body and 'transaction.get' not in trans_body:
                    result.warnings.append(ValidationWarning(
                        warning_type="code",
                        message="Possible read outside transaction context",
                        suggestion="Use transaction.get() for reads inside transactions",
                    ))

    def validate_security_rules(self, rules: str) -> ValidationResult:
        """Convenience method to validate security rules specifically."""
        result = ValidationResult(valid=True, language="firestore-rules")
        self._validate_security_rules(rules, result)
        result.validators_run.append("firebase-rules")
        return result
