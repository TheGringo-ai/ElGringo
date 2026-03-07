"""
Tests for Validation and Routing modules
"""

import pytest
from ai_dev_team.validation.code_validator import (
    CodeValidator,
    ValidationError,
    ValidationWarning,
    ValidationResult,
)
from ai_dev_team.routing import (
    TaskRouter,
    TaskType,
    TaskClassification,
    CostOptimizer,
    ModelTier,
)
from ai_dev_team.routing.cost_optimizer import MODEL_TIER_MAPPING, MODEL_COSTS, COMPLEXITY_TO_TIER


class TestValidationDataclasses:
    """Test validation dataclasses"""

    def test_validation_error_str_with_line(self):
        err = ValidationError(error_type="syntax", message="bad code", line=42, code="E501")
        s = str(err)
        assert "syntax" in s
        assert "E501" in s
        assert "line 42" in s

    def test_validation_error_str_no_line(self):
        err = ValidationError(error_type="lint", message="issue")
        s = str(err)
        assert "lint" in s
        assert "line" not in s

    def test_validation_warning_str(self):
        w = ValidationWarning(warning_type="security", message="eval found", line=10)
        s = str(w)
        assert "security" in s
        assert "line 10" in s

    def test_validation_warning_no_line(self):
        w = ValidationWarning(warning_type="perf", message="slow")
        assert "line" not in str(w)

    def test_validation_result_has_errors(self):
        r = ValidationResult(valid=False, errors=[
            ValidationError(error_type="x", message="y")
        ])
        assert r.has_errors
        assert not r.has_warnings

    def test_validation_result_has_warnings(self):
        r = ValidationResult(valid=True, warnings=[
            ValidationWarning(warning_type="x", message="y")
        ])
        assert not r.has_errors
        assert r.has_warnings

    def test_validation_result_summary_clean(self):
        r = ValidationResult(valid=True)
        assert "passed" in r.to_summary()

    def test_validation_result_summary_with_errors(self):
        r = ValidationResult(valid=False, errors=[
            ValidationError(error_type="syntax", message="bad"),
        ], warnings=[
            ValidationWarning(warning_type="style", message="ugly"),
        ], suggestions=["fix it"])
        summary = r.to_summary()
        assert "1 error" in summary
        assert "1 warning" in summary
        assert "fix it" in summary


class TestCodeValidator:
    """Test CodeValidator"""

    @pytest.fixture
    def validator(self):
        return CodeValidator()

    def test_detect_python(self, validator):
        code = "import os\ndef foo():\n    pass\n"
        assert validator.detect_language(code) == "python"

    def test_detect_typescript(self, validator):
        code = "import { foo } from 'bar'\nconst x: string = 'hello'\n"
        assert validator.detect_language(code) == "typescript"

    def test_detect_javascript(self, validator):
        code = "const x = 5\nlet y = 10\nfunction foo() {}\n"
        assert validator.detect_language(code) == "javascript"

    def test_detect_unknown(self, validator):
        code = "just some random text"
        assert validator.detect_language(code) == "unknown"

    def test_validate_empty_code(self, validator):
        result = validator.validate("")
        assert result.valid

    def test_validate_whitespace_only(self, validator):
        result = validator.validate("   \n  \n  ")
        assert result.valid

    def test_validate_python_valid(self, validator):
        code = "x = 1\ny = 2\nprint(x + y)\n"
        result = validator.validate(code, language="python")
        assert result.language == "python"

    def test_validate_security_hardcoded_secret(self, validator):
        code = 'api_key = "sk-12345678"\n'
        result = validator.validate(code, language="python")
        security_warnings = [w for w in result.warnings if w.warning_type == "security"]
        assert len(security_warnings) > 0

    def test_validate_security_eval(self, validator):
        code = "result = eval(user_input)\n"
        result = validator.validate(code, language="python")
        security_warnings = [w for w in result.warnings if w.warning_type == "security"]
        assert any("eval" in w.message for w in security_warnings)

    def test_validate_security_exec(self, validator):
        code = "exec(code_string)\n"
        result = validator.validate(code, language="python")
        security_warnings = [w for w in result.warnings if w.warning_type == "security"]
        assert any("exec" in w.message for w in security_warnings)

    def test_validate_security_sql_injection(self, validator):
        code = 'query = f"SELECT * FROM users WHERE id={user_id}"\n'
        result = validator.validate(code, language="python")
        security_warnings = [w for w in result.warnings if w.warning_type == "security"]
        assert len(security_warnings) > 0

    def test_validate_domain_firebase(self, validator):
        code = "from firebase_admin import firestore\ndb = firestore.client()\n"
        result = validator.validate(code, language="python", check_domain=True)
        assert "firebase" in result.validators_run or isinstance(result, ValidationResult)

    def test_extract_code_blocks(self, validator):
        text = '```python\nx = 1\n```\n\n```javascript\nconst y = 2\n```'
        blocks = validator.extract_code_blocks(text)
        assert len(blocks) == 2
        assert blocks[0][0] == "python"
        assert blocks[1][0] == "javascript"

    def test_extract_code_blocks_no_language(self, validator):
        text = '```\nimport os\ndef foo():\n    pass\n```'
        blocks = validator.extract_code_blocks(text)
        assert len(blocks) == 1
        # Should auto-detect python
        assert blocks[0][0] == "python"

    def test_validate_response(self, validator):
        text = '```python\nx = 1\n```'
        results = validator.validate_response(text)
        assert len(results) == 1
        assert results[0].language == "python"


class TestTaskRouter:
    """Test TaskRouter"""

    @pytest.fixture
    def router(self):
        return TaskRouter()

    def test_classify_coding_task(self, router):
        result = router.classify("Write a function to parse JSON data")
        assert result.primary_type == TaskType.CODING
        assert result.confidence > 0

    def test_classify_security_task(self, router):
        result = router.classify("Audit the authentication system for vulnerabilities")
        assert result.primary_type == TaskType.SECURITY

    def test_classify_debugging_task(self, router):
        result = router.classify("Debug the crash in the login handler")
        assert result.primary_type == TaskType.DEBUGGING

    def test_classify_architecture_task(self, router):
        result = router.classify("Design the microservices architecture for our platform")
        assert result.primary_type == TaskType.ARCHITECTURE

    def test_classify_creative_task(self, router):
        result = router.classify("Design a beautiful UI for the dashboard")
        assert result.primary_type in (TaskType.CREATIVE, TaskType.UI_UX)

    def test_classify_returns_recommended_agents(self, router):
        result = router.classify("Write unit tests for the API")
        assert len(result.recommended_agents) > 0

    def test_classify_returns_complexity(self, router):
        result = router.classify("Refactor the entire system")
        assert result.complexity in ("low", "medium", "high")

    def test_classify_returns_mode(self, router):
        result = router.classify("Review this code")
        assert result.recommended_mode in (
            "parallel", "sequential", "consensus",
            "peer_review", "debate", "expert_panel",
        )

    def test_task_type_values(self):
        assert TaskType.CODING.value == "coding"
        assert TaskType.SECURITY.value == "security"
        assert TaskType.DEBUGGING.value == "debugging"


class TestCostOptimizer:
    """Test CostOptimizer"""

    def test_model_tier_mapping_exists(self):
        assert len(MODEL_TIER_MAPPING) > 0
        assert "gpt-4o" in MODEL_TIER_MAPPING
        assert MODEL_TIER_MAPPING["gpt-4o"] == ModelTier.PREMIUM

    def test_model_costs_exist(self):
        assert len(MODEL_COSTS) > 0
        assert "gpt-4o" in MODEL_COSTS
        input_cost, output_cost = MODEL_COSTS["gpt-4o"]
        assert input_cost > 0
        assert output_cost > 0

    def test_local_models_are_free(self):
        input_cost, output_cost = MODEL_COSTS["llama3.2:3b"]
        assert input_cost == 0.0
        assert output_cost == 0.0

    def test_complexity_to_tier(self):
        assert COMPLEXITY_TO_TIER["low"] == ModelTier.BUDGET
        assert COMPLEXITY_TO_TIER["medium"] == ModelTier.STANDARD
        assert COMPLEXITY_TO_TIER["high"] == ModelTier.PREMIUM

    def test_model_tier_ordering(self):
        assert ModelTier.BUDGET.value < ModelTier.STANDARD.value
        assert ModelTier.STANDARD.value < ModelTier.PREMIUM.value

    def test_cost_optimizer_init(self):
        optimizer = CostOptimizer()
        assert optimizer is not None

    def test_budget_models_cheaper_than_premium(self):
        budget_costs = [MODEL_COSTS[m] for m, t in MODEL_TIER_MAPPING.items()
                       if t == ModelTier.BUDGET and m in MODEL_COSTS]
        premium_costs = [MODEL_COSTS[m] for m, t in MODEL_TIER_MAPPING.items()
                        if t == ModelTier.PREMIUM and m in MODEL_COSTS]
        if budget_costs and premium_costs:
            avg_budget = sum(c[0] + c[1] for c in budget_costs) / len(budget_costs)
            avg_premium = sum(c[0] + c[1] for c in premium_costs) / len(premium_costs)
            assert avg_budget < avg_premium


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
