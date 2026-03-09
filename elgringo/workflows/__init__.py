"""Workflows subpackage — re-exports for backward compatibility."""

from .workflows import (
    PreCommitWorkflow,
    CICDWorkflow,
    CodeReviewPipeline,
    WorkflowResult,
    GateResult,
    WorkflowStatus,
    GateType,
    create_pre_commit_workflow,
    create_cicd_workflow,
    create_code_review_pipeline,
    run_pre_commit,
)
from .fredfix import FredFix, FixResult, create_fredfix
from .parallel_coding import ParallelCodingEngine, CodeTask, CodeFix, ParallelCodingResult
from .app_generator import AppGenerator, create_app_generator, generate_app
from .project_context import ProjectContextManager
