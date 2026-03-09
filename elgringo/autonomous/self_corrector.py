"""
Self-Correction Engine for Autonomous AI Agents

Automatically detects failures, analyzes issues, and retries with adaptive strategies.
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any, Callable

logger = logging.getLogger(__name__)


class CorrectionStrategy(Enum):
    """Strategies for correcting failed responses."""
    ENHANCE_PROMPT = "enhance_prompt"      # Add more context/examples
    SWITCH_AGENT = "switch_agent"          # Try a different agent
    DECOMPOSE_TASK = "decompose_task"      # Break into smaller subtasks
    ADD_CONSTRAINTS = "add_constraints"    # Add explicit constraints
    SIMPLIFY = "simplify"                  # Simplify the request
    EXPERT_MODE = "expert_mode"            # Use specialist agent
    CONSENSUS = "consensus"                # Get multiple opinions


class FailureType(Enum):
    """Types of failures that can be detected."""
    LOW_CONFIDENCE = "low_confidence"
    SYNTAX_ERROR = "syntax_error"
    INCOMPLETE = "incomplete"
    OFF_TOPIC = "off_topic"
    HALLUCINATION = "hallucination"
    TIMEOUT = "timeout"
    VALIDATION_FAILED = "validation_failed"
    EMPTY_RESPONSE = "empty_response"
    EXCEPTION = "exception"


@dataclass
class CorrectionResult:
    """Result of a correction attempt."""
    success: bool
    original_response: str
    corrected_response: Optional[str]
    strategy_used: CorrectionStrategy
    attempts: int
    failure_type: Optional[FailureType]
    confidence: float
    improvements: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Result of validating a response."""
    valid: bool
    confidence: float
    failure_type: Optional[FailureType]
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


class ResponseValidator:
    """Validates agent responses for quality and correctness."""

    def __init__(self):
        self.code_patterns = {
            'python': {
                'syntax_check': self._check_python_syntax,
                'common_errors': [
                    (r'def\s+\w+\([^)]*\)\s*$', 'Missing colon after function definition'),
                    (r'class\s+\w+\s*$', 'Missing colon after class definition'),
                    (r'import\s+$', 'Incomplete import statement'),
                ]
            },
            'javascript': {
                'syntax_check': self._check_js_syntax,
                'common_errors': [
                    (r'function\s+\w+\s*\([^)]*\)\s*$', 'Missing function body'),
                    (r'const\s+\w+\s*$', 'Uninitialized const'),
                ]
            }
        }

    def validate(self, response: str, task_type: str = None,
                 language: str = None) -> ValidationResult:
        """Validate a response for quality and correctness."""
        issues = []
        suggestions = []
        confidence = 1.0
        failure_type = None

        # Check for empty response
        if not response or not response.strip():
            return ValidationResult(
                valid=False,
                confidence=0.0,
                failure_type=FailureType.EMPTY_RESPONSE,
                issues=["Empty response received"],
                suggestions=["Request a complete response"]
            )

        # Check response length (too short might be incomplete)
        if len(response.strip()) < 50 and task_type == 'coding':
            confidence -= 0.3
            issues.append("Response seems too short for a coding task")
            suggestions.append("Request more detailed implementation")

        # Check for code blocks in coding tasks
        if task_type == 'coding':
            if '```' not in response and 'def ' not in response and 'function' not in response:
                confidence -= 0.2
                issues.append("No code block found in coding response")
                suggestions.append("Ask for code examples")

        # Check for hedging language (low confidence indicators)
        hedging_patterns = [
            r'\bI\'m not sure\b',
            r'\bI don\'t know\b',
            r'\bmaybe\b',
            r'\bperhaps\b',
            r'\bmight be\b',
            r'\bcould be\b',
        ]
        hedging_count = sum(1 for p in hedging_patterns if re.search(p, response, re.I))
        if hedging_count > 2:
            confidence -= 0.1 * hedging_count
            issues.append(f"Response contains {hedging_count} hedging phrases")

        # Check for error indicators
        error_patterns = [
            r'\bI cannot\b',
            r'\bI\'m unable\b',
            r'\berror\b.*\boccurred\b',
            r'\bfailed to\b',
        ]
        for pattern in error_patterns:
            if re.search(pattern, response, re.I):
                confidence -= 0.15
                issues.append("Response indicates an error or inability")

        # Validate code syntax if language specified
        if language and language.lower() in self.code_patterns:
            code_blocks = self._extract_code_blocks(response, language)
            for code in code_blocks:
                syntax_result = self._validate_code_syntax(code, language)
                if not syntax_result['valid']:
                    confidence -= 0.3
                    issues.extend(syntax_result['errors'])
                    failure_type = FailureType.SYNTAX_ERROR

        # Determine overall validity
        valid = confidence >= 0.5 and failure_type is None

        if not valid and failure_type is None:
            failure_type = FailureType.LOW_CONFIDENCE

        return ValidationResult(
            valid=valid,
            confidence=max(0.0, min(1.0, confidence)),
            failure_type=failure_type,
            issues=issues,
            suggestions=suggestions
        )

    def _extract_code_blocks(self, text: str, language: str) -> List[str]:
        """Extract code blocks from markdown text."""
        pattern = rf'```(?:{language})?\s*\n(.*?)```'
        blocks = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        return blocks

    def _validate_code_syntax(self, code: str, language: str) -> Dict[str, Any]:
        """Validate code syntax for a given language."""
        lang_lower = language.lower()
        if lang_lower in self.code_patterns:
            checker = self.code_patterns[lang_lower].get('syntax_check')
            if checker:
                return checker(code)
        return {'valid': True, 'errors': []}

    def _check_python_syntax(self, code: str) -> Dict[str, Any]:
        """Check Python syntax validity."""
        try:
            compile(code, '<string>', 'exec')
            return {'valid': True, 'errors': []}
        except SyntaxError as e:
            return {
                'valid': False,
                'errors': [f"Python syntax error at line {e.lineno}: {e.msg}"]
            }

    def _check_js_syntax(self, code: str) -> Dict[str, Any]:
        """Basic JavaScript syntax check."""
        errors = []

        # Check bracket balance
        if code.count('{') != code.count('}'):
            errors.append("Unbalanced curly braces")
        if code.count('(') != code.count(')'):
            errors.append("Unbalanced parentheses")
        if code.count('[') != code.count(']'):
            errors.append("Unbalanced square brackets")

        return {'valid': len(errors) == 0, 'errors': errors}


class SelfCorrector:
    """
    Autonomous self-correction engine that detects failures and retries
    with adaptive strategies.
    """

    def __init__(self, max_attempts: int = 3, confidence_threshold: float = 0.7):
        self.max_attempts = max_attempts
        self.confidence_threshold = confidence_threshold
        self.validator = ResponseValidator()
        self.correction_history: List[CorrectionResult] = []
        self.strategy_success_rates: Dict[CorrectionStrategy, Dict[str, float]] = {
            strategy: {'successes': 0, 'attempts': 0}
            for strategy in CorrectionStrategy
        }

        # Strategy selection order based on failure type
        self.strategy_map: Dict[FailureType, List[CorrectionStrategy]] = {
            FailureType.LOW_CONFIDENCE: [
                CorrectionStrategy.ENHANCE_PROMPT,
                CorrectionStrategy.SWITCH_AGENT,
                CorrectionStrategy.CONSENSUS,
            ],
            FailureType.SYNTAX_ERROR: [
                CorrectionStrategy.ADD_CONSTRAINTS,
                CorrectionStrategy.SWITCH_AGENT,
                CorrectionStrategy.EXPERT_MODE,
            ],
            FailureType.INCOMPLETE: [
                CorrectionStrategy.ENHANCE_PROMPT,
                CorrectionStrategy.DECOMPOSE_TASK,
                CorrectionStrategy.ADD_CONSTRAINTS,
            ],
            FailureType.OFF_TOPIC: [
                CorrectionStrategy.ADD_CONSTRAINTS,
                CorrectionStrategy.SIMPLIFY,
                CorrectionStrategy.SWITCH_AGENT,
            ],
            FailureType.TIMEOUT: [
                CorrectionStrategy.SIMPLIFY,
                CorrectionStrategy.DECOMPOSE_TASK,
                CorrectionStrategy.SWITCH_AGENT,
            ],
            FailureType.EMPTY_RESPONSE: [
                CorrectionStrategy.SWITCH_AGENT,
                CorrectionStrategy.SIMPLIFY,
                CorrectionStrategy.ENHANCE_PROMPT,
            ],
            FailureType.EXCEPTION: [
                CorrectionStrategy.SWITCH_AGENT,
                CorrectionStrategy.SIMPLIFY,
                CorrectionStrategy.DECOMPOSE_TASK,
            ],
        }

    async def correct(
        self,
        original_prompt: str,
        original_response: str,
        execute_fn: Callable,
        task_type: str = None,
        language: str = None,
        available_agents: List[str] = None,
        context: Dict[str, Any] = None
    ) -> CorrectionResult:
        """
        Attempt to correct a failed or low-quality response.

        Args:
            original_prompt: The original task prompt
            original_response: The response that needs correction
            execute_fn: Async function to execute prompts (agent.generate or orchestrator.collaborate)
            task_type: Type of task (coding, debugging, etc.)
            language: Programming language if applicable
            available_agents: List of available agent IDs for switching
            context: Additional context for correction

        Returns:
            CorrectionResult with the corrected response or failure info
        """
        context = context or {}
        available_agents = available_agents or []

        # Validate the original response
        validation = self.validator.validate(original_response, task_type, language)

        # If valid, return as-is
        if validation.valid and validation.confidence >= self.confidence_threshold:
            return CorrectionResult(
                success=True,
                original_response=original_response,
                corrected_response=original_response,
                strategy_used=None,
                attempts=0,
                failure_type=None,
                confidence=validation.confidence
            )

        logger.info(f"Response needs correction. Confidence: {validation.confidence:.2f}, "
                   f"Issues: {validation.issues}")

        # Get strategies for this failure type
        failure_type = validation.failure_type or FailureType.LOW_CONFIDENCE
        strategies = self.strategy_map.get(failure_type, list(CorrectionStrategy))

        # Sort strategies by historical success rate
        strategies = self._sort_strategies_by_success(strategies)

        # Try each strategy
        attempts = 0
        last_response = original_response

        for strategy in strategies:
            if attempts >= self.max_attempts:
                break

            attempts += 1
            logger.info(f"Correction attempt {attempts}/{self.max_attempts} using {strategy.value}")

            try:
                # Generate corrected prompt based on strategy
                corrected_prompt = self._apply_strategy(
                    strategy=strategy,
                    original_prompt=original_prompt,
                    last_response=last_response,
                    validation=validation,
                    context=context
                )

                # Execute with corrected prompt
                if strategy == CorrectionStrategy.SWITCH_AGENT and available_agents:
                    # Try a different agent
                    new_response = await execute_fn(
                        corrected_prompt,
                        agent_override=self._select_alternative_agent(available_agents, context)
                    )
                elif strategy == CorrectionStrategy.CONSENSUS:
                    # Get consensus from multiple agents
                    new_response = await execute_fn(
                        corrected_prompt,
                        mode='consensus'
                    )
                else:
                    new_response = await execute_fn(corrected_prompt)

                # Validate the new response
                new_validation = self.validator.validate(new_response, task_type, language)

                # Update strategy success rate
                self._update_strategy_stats(strategy, new_validation.valid)

                if new_validation.valid and new_validation.confidence >= self.confidence_threshold:
                    result = CorrectionResult(
                        success=True,
                        original_response=original_response,
                        corrected_response=new_response,
                        strategy_used=strategy,
                        attempts=attempts,
                        failure_type=failure_type,
                        confidence=new_validation.confidence,
                        improvements=self._identify_improvements(
                            original_response, new_response, validation, new_validation
                        )
                    )
                    self.correction_history.append(result)
                    logger.info(f"Correction successful with {strategy.value}")
                    return result

                # Update for next iteration
                last_response = new_response
                validation = new_validation

            except Exception as e:
                logger.warning(f"Correction attempt with {strategy.value} failed: {e}")
                self._update_strategy_stats(strategy, False)
                continue

        # All attempts failed
        result = CorrectionResult(
            success=False,
            original_response=original_response,
            corrected_response=last_response,
            strategy_used=strategies[-1] if strategies else None,
            attempts=attempts,
            failure_type=failure_type,
            confidence=validation.confidence,
            metadata={'all_strategies_exhausted': True}
        )
        self.correction_history.append(result)
        logger.warning(f"Correction failed after {attempts} attempts")
        return result

    def _apply_strategy(
        self,
        strategy: CorrectionStrategy,
        original_prompt: str,
        last_response: str,
        validation: ValidationResult,
        context: Dict[str, Any]
    ) -> str:
        """Apply a correction strategy to modify the prompt."""

        if strategy == CorrectionStrategy.ENHANCE_PROMPT:
            issues_text = "\n".join(f"- {issue}" for issue in validation.issues)
            return f"""Previous attempt had issues:
{issues_text}

Please provide a more complete and detailed response.

Original request:
{original_prompt}

Requirements:
- Be thorough and complete
- Include all necessary details
- Provide working code examples if applicable"""

        elif strategy == CorrectionStrategy.ADD_CONSTRAINTS:
            return f"""{original_prompt}

IMPORTANT CONSTRAINTS:
- Ensure syntactically correct code
- Include all imports and dependencies
- Handle edge cases
- Follow best practices
- Test your solution mentally before responding"""

        elif strategy == CorrectionStrategy.SIMPLIFY:
            return f"""Please provide a SIMPLE, MINIMAL solution for:

{original_prompt}

Focus on:
- Core functionality only
- Clear, readable code
- No over-engineering"""

        elif strategy == CorrectionStrategy.DECOMPOSE_TASK:
            return f"""Let's break this down into steps.

Task: {original_prompt}

Please:
1. First, outline the steps needed
2. Then implement each step
3. Finally, combine them into a complete solution"""

        elif strategy == CorrectionStrategy.EXPERT_MODE:
            return f"""As an expert developer, please solve:

{original_prompt}

Apply your expertise to:
- Use professional patterns
- Consider performance
- Handle errors properly
- Write production-quality code"""

        elif strategy == CorrectionStrategy.CONSENSUS:
            return f"""Please carefully analyze and provide your best solution:

{original_prompt}

Consider multiple approaches and select the best one."""

        else:  # SWITCH_AGENT - prompt stays the same
            return original_prompt

    def _sort_strategies_by_success(
        self,
        strategies: List[CorrectionStrategy]
    ) -> List[CorrectionStrategy]:
        """Sort strategies by historical success rate."""
        def success_rate(strategy):
            stats = self.strategy_success_rates[strategy]
            if stats['attempts'] == 0:
                return 0.5  # Default for untried strategies
            return stats['successes'] / stats['attempts']

        return sorted(strategies, key=success_rate, reverse=True)

    def _update_strategy_stats(self, strategy: CorrectionStrategy, success: bool):
        """Update success statistics for a strategy."""
        self.strategy_success_rates[strategy]['attempts'] += 1
        if success:
            self.strategy_success_rates[strategy]['successes'] += 1

    def _select_alternative_agent(
        self,
        available_agents: List[str],
        context: Dict[str, Any]
    ) -> str:
        """Select an alternative agent to try."""
        current_agent = context.get('current_agent')
        alternatives = [a for a in available_agents if a != current_agent]

        # Prefer specialists for certain task types
        task_type = context.get('task_type', '')
        if 'security' in task_type.lower():
            for a in alternatives:
                if 'security' in a.lower():
                    return a
        elif 'code' in task_type.lower() or 'debug' in task_type.lower():
            for a in alternatives:
                if 'coder' in a.lower() or 'developer' in a.lower():
                    return a

        return alternatives[0] if alternatives else current_agent

    def _identify_improvements(
        self,
        original: str,
        corrected: str,
        original_validation: ValidationResult,
        corrected_validation: ValidationResult
    ) -> List[str]:
        """Identify what improved between original and corrected response."""
        improvements = []

        confidence_diff = corrected_validation.confidence - original_validation.confidence
        if confidence_diff > 0:
            improvements.append(f"Confidence improved by {confidence_diff:.2f}")

        fixed_issues = set(original_validation.issues) - set(corrected_validation.issues)
        for issue in fixed_issues:
            improvements.append(f"Fixed: {issue}")

        if len(corrected) > len(original) * 1.5:
            improvements.append("Response is more detailed")

        if '```' in corrected and '```' not in original:
            improvements.append("Added code examples")

        return improvements

    def get_statistics(self) -> Dict[str, Any]:
        """Get correction statistics."""
        total_corrections = len(self.correction_history)
        successful = sum(1 for c in self.correction_history if c.success)

        return {
            'total_corrections': total_corrections,
            'successful_corrections': successful,
            'success_rate': successful / total_corrections if total_corrections > 0 else 0,
            'strategy_success_rates': {
                strategy.value: {
                    'rate': stats['successes'] / stats['attempts'] if stats['attempts'] > 0 else 0,
                    'attempts': stats['attempts']
                }
                for strategy, stats in self.strategy_success_rates.items()
            },
            'common_failure_types': self._get_common_failures()
        }

    def _get_common_failures(self) -> Dict[str, int]:
        """Get counts of common failure types."""
        failures = {}
        for result in self.correction_history:
            if result.failure_type:
                key = result.failure_type.value
                failures[key] = failures.get(key, 0) + 1
        return failures


# Convenience function for quick correction
async def auto_correct(
    prompt: str,
    response: str,
    execute_fn: Callable,
    **kwargs
) -> CorrectionResult:
    """Quick auto-correction with default settings."""
    corrector = SelfCorrector()
    return await corrector.correct(prompt, response, execute_fn, **kwargs)
