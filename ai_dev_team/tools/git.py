"""
Git Tools - Version control operations for AI agents
=====================================================

Capabilities:
- Repository management (init, clone, status)
- Branch operations (create, switch, merge, delete)
- Commit operations (add, commit, amend)
- Remote operations (push, pull, fetch)
- Advanced (stash, rebase, cherry-pick)
- Pull Request creation via GitHub CLI
- AI-powered commit message generation
- Smart auto-commit with change analysis
"""

import asyncio
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

from .base import Tool, ToolResult, PermissionManager

logger = logging.getLogger(__name__)


class GitTools(Tool):
    """
    Git version control tools for AI-powered development.

    Enables AI agents to manage code repositories, create branches,
    commit changes, and collaborate through pull requests.
    """

    def __init__(
        self,
        permission_manager: Optional[PermissionManager] = None,
        default_cwd: Optional[str] = None
    ):
        super().__init__(
            name="git",
            description="Git version control operations",
            permission_manager=permission_manager,
        )

        self.default_cwd = default_cwd or os.getcwd()

        # Register operations
        self.register_operation("status", self._status, "Get repository status", requires_permission=False)
        self.register_operation("log", self._log, "View commit history", requires_permission=False)
        self.register_operation("diff", self._diff, "Show changes", requires_permission=False)
        self.register_operation("branch", self._branch, "List or create branches", requires_permission=False)
        self.register_operation("checkout", self._checkout, "Switch branches or restore files")
        self.register_operation("add", self._add, "Stage files for commit")
        self.register_operation("commit", self._commit, "Commit staged changes")
        self.register_operation("push", self._push, "Push to remote")
        self.register_operation("pull", self._pull, "Pull from remote")
        self.register_operation("fetch", self._fetch, "Fetch from remote", requires_permission=False)
        self.register_operation("merge", self._merge, "Merge branches")
        self.register_operation("stash", self._stash, "Stash changes")
        self.register_operation("init", self._init, "Initialize repository")
        self.register_operation("clone", self._clone, "Clone repository")
        self.register_operation("create_pr", self._create_pr, "Create pull request via gh CLI")
        self.register_operation("rebase", self._rebase, "Rebase current branch")
        self.register_operation("reset", self._reset, "Reset to commit")
        self.register_operation("cherry_pick", self._cherry_pick, "Cherry-pick commits")
        self.register_operation("tag", self._tag, "Manage tags")

    async def _run_git(
        self,
        args: List[str],
        cwd: Optional[str] = None,
        timeout: int = 60
    ) -> ToolResult:
        """Execute a git command"""
        try:
            cmd = ["git"] + args
            work_dir = cwd or self.default_cwd

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=work_dir
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )

            stdout_str = stdout.decode().strip()
            stderr_str = stderr.decode().strip()

            if process.returncode == 0:
                return ToolResult(
                    success=True,
                    output=stdout_str or stderr_str,
                    metadata={"command": " ".join(cmd), "cwd": work_dir}
                )
            else:
                return ToolResult(
                    success=False,
                    output=stdout_str,
                    error=stderr_str or f"Git command failed with code {process.returncode}",
                    metadata={"command": " ".join(cmd)}
                )

        except asyncio.TimeoutError:
            return ToolResult(success=False, output=None, error=f"Git command timed out after {timeout}s")
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _status(self, cwd: Optional[str] = None) -> ToolResult:
        """Get repository status"""
        return asyncio.get_event_loop().run_until_complete(
            self._run_git(["status", "--short", "--branch"], cwd)
        )

    def _log(
        self,
        count: int = 10,
        oneline: bool = True,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """View commit history"""
        args = ["log", f"-{count}"]
        if oneline:
            args.append("--oneline")
        return asyncio.get_event_loop().run_until_complete(
            self._run_git(args, cwd)
        )

    def _diff(
        self,
        staged: bool = False,
        file_path: Optional[str] = None,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Show changes"""
        args = ["diff"]
        if staged:
            args.append("--staged")
        if file_path:
            args.append(file_path)
        return asyncio.get_event_loop().run_until_complete(
            self._run_git(args, cwd)
        )

    def _branch(
        self,
        name: Optional[str] = None,
        delete: bool = False,
        all_branches: bool = False,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """List or create branches"""
        args = ["branch"]
        if all_branches:
            args.append("-a")
        if delete and name:
            args.extend(["-d", name])
        elif name:
            args.append(name)
        return asyncio.get_event_loop().run_until_complete(
            self._run_git(args, cwd)
        )

    def _checkout(
        self,
        target: str,
        create: bool = False,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Switch branches or restore files"""
        args = ["checkout"]
        if create:
            args.append("-b")
        args.append(target)
        return asyncio.get_event_loop().run_until_complete(
            self._run_git(args, cwd)
        )

    def _add(
        self,
        files: Optional[List[str]] = None,
        all_files: bool = False,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Stage files for commit"""
        args = ["add"]
        if all_files:
            args.append("-A")
        elif files:
            args.extend(files)
        else:
            args.append(".")
        return asyncio.get_event_loop().run_until_complete(
            self._run_git(args, cwd)
        )

    def _commit(
        self,
        message: str,
        amend: bool = False,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Commit staged changes"""
        args = ["commit", "-m", message]
        if amend:
            args.append("--amend")
        return asyncio.get_event_loop().run_until_complete(
            self._run_git(args, cwd)
        )

    def _push(
        self,
        remote: str = "origin",
        branch: Optional[str] = None,
        force: bool = False,
        set_upstream: bool = False,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Push to remote"""
        args = ["push"]
        if force:
            args.append("--force-with-lease")
        if set_upstream:
            args.append("-u")
        args.append(remote)
        if branch:
            args.append(branch)
        return asyncio.get_event_loop().run_until_complete(
            self._run_git(args, cwd)
        )

    def _pull(
        self,
        remote: str = "origin",
        branch: Optional[str] = None,
        rebase: bool = False,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Pull from remote"""
        args = ["pull"]
        if rebase:
            args.append("--rebase")
        args.append(remote)
        if branch:
            args.append(branch)
        return asyncio.get_event_loop().run_until_complete(
            self._run_git(args, cwd)
        )

    def _fetch(
        self,
        remote: str = "origin",
        prune: bool = True,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Fetch from remote"""
        args = ["fetch", remote]
        if prune:
            args.append("--prune")
        return asyncio.get_event_loop().run_until_complete(
            self._run_git(args, cwd)
        )

    def _merge(
        self,
        branch: str,
        no_ff: bool = False,
        message: Optional[str] = None,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Merge branches"""
        args = ["merge", branch]
        if no_ff:
            args.append("--no-ff")
        if message:
            args.extend(["-m", message])
        return asyncio.get_event_loop().run_until_complete(
            self._run_git(args, cwd)
        )

    def _stash(
        self,
        action: str = "push",
        message: Optional[str] = None,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Stash changes (push, pop, list, apply, drop)"""
        args = ["stash", action]
        if action == "push" and message:
            args.extend(["-m", message])
        return asyncio.get_event_loop().run_until_complete(
            self._run_git(args, cwd)
        )

    def _init(
        self,
        path: Optional[str] = None,
        bare: bool = False,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Initialize repository"""
        args = ["init"]
        if bare:
            args.append("--bare")
        if path:
            args.append(path)
        return asyncio.get_event_loop().run_until_complete(
            self._run_git(args, cwd)
        )

    def _clone(
        self,
        url: str,
        path: Optional[str] = None,
        depth: Optional[int] = None,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Clone repository"""
        args = ["clone", url]
        if depth:
            args.extend(["--depth", str(depth)])
        if path:
            args.append(path)
        return asyncio.get_event_loop().run_until_complete(
            self._run_git(args, cwd, timeout=300)  # 5 min for large repos
        )

    def _create_pr(
        self,
        title: str,
        body: str,
        base: str = "main",
        draft: bool = False,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Create pull request using GitHub CLI"""
        try:
            args = ["gh", "pr", "create", "--title", title, "--body", body, "--base", base]
            if draft:
                args.append("--draft")

            work_dir = cwd or self.default_cwd

            result = asyncio.get_event_loop().run_until_complete(
                asyncio.create_subprocess_exec(
                    *args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=work_dir
                )
            )

            stdout, stderr = asyncio.get_event_loop().run_until_complete(
                result.communicate()
            )

            if result.returncode == 0:
                pr_url = stdout.decode().strip()
                return ToolResult(
                    success=True,
                    output=pr_url,
                    metadata={"title": title, "base": base}
                )
            else:
                return ToolResult(
                    success=False,
                    output=None,
                    error=stderr.decode().strip()
                )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _rebase(
        self,
        target: str,
        interactive: bool = False,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Rebase current branch"""
        args = ["rebase"]
        if interactive:
            # Note: Interactive rebase won't work in automated context
            logger.warning("Interactive rebase not supported in automated mode")
        args.append(target)
        return asyncio.get_event_loop().run_until_complete(
            self._run_git(args, cwd)
        )

    def _reset(
        self,
        target: str = "HEAD",
        mode: str = "mixed",
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Reset to commit (soft, mixed, hard)"""
        args = ["reset", f"--{mode}", target]
        return asyncio.get_event_loop().run_until_complete(
            self._run_git(args, cwd)
        )

    def _cherry_pick(
        self,
        commits: List[str],
        no_commit: bool = False,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Cherry-pick commits"""
        args = ["cherry-pick"]
        if no_commit:
            args.append("-n")
        args.extend(commits)
        return asyncio.get_event_loop().run_until_complete(
            self._run_git(args, cwd)
        )

    def _tag(
        self,
        name: Optional[str] = None,
        message: Optional[str] = None,
        delete: bool = False,
        list_tags: bool = False,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Manage tags"""
        args = ["tag"]
        if list_tags or not name:
            pass  # Just list tags
        elif delete and name:
            args.extend(["-d", name])
        elif name:
            if message:
                args.extend(["-a", name, "-m", message])
            else:
                args.append(name)
        return asyncio.get_event_loop().run_until_complete(
            self._run_git(args, cwd)
        )


    def get_capabilities(self) -> List[Dict[str, str]]:
        """Return list of Git tool capabilities."""
        return [
            {"name": "status", "description": "Get repository status"},
            {"name": "log", "description": "View commit history"},
            {"name": "diff", "description": "Show changes"},
            {"name": "branch", "description": "List or create branches"},
            {"name": "checkout", "description": "Switch branches or restore files"},
            {"name": "add", "description": "Stage files for commit"},
            {"name": "commit", "description": "Commit staged changes"},
            {"name": "push", "description": "Push to remote"},
            {"name": "pull", "description": "Pull from remote"},
            {"name": "merge", "description": "Merge branches"},
            {"name": "stash", "description": "Stash changes"},
            {"name": "create_pr", "description": "Create pull request"},
        ]


@dataclass
class CommitSuggestion:
    """AI-generated commit suggestion"""
    message: str
    type: str  # feat, fix, docs, style, refactor, test, chore
    scope: Optional[str]
    breaking: bool
    files_analyzed: int
    confidence: float


class SmartGitTools(GitTools):
    """
    Enhanced Git tools with AI-powered features:
    - Automatic commit message generation
    - Change analysis and categorization
    - Smart branch naming suggestions
    - PR description generation
    """

    def __init__(
        self,
        permission_manager: Optional[PermissionManager] = None,
        default_cwd: Optional[str] = None,
        ai_callback: Optional[Callable] = None,
    ):
        super().__init__(permission_manager, default_cwd)
        self.ai_callback = ai_callback

        # Register smart operations
        self.register_operation("smart_commit", self._smart_commit, "AI-powered commit with auto-message")
        self.register_operation("analyze_changes", self._analyze_changes, "Analyze uncommitted changes")
        self.register_operation("suggest_branch", self._suggest_branch, "Suggest branch name for task")
        self.register_operation("generate_pr", self._generate_pr, "Generate PR with AI description")

    def _analyze_changes(self, cwd: Optional[str] = None) -> ToolResult:
        """Analyze uncommitted changes and categorize them"""
        try:
            # Get status
            status_result = self._status(cwd)
            if not status_result.success:
                return status_result

            # Get diff
            diff_result = self._diff(cwd=cwd)
            staged_diff = self._diff(staged=True, cwd=cwd)

            # Parse file changes
            status_lines = status_result.output.split('\n') if status_result.output else []

            added = []
            modified = []
            deleted = []
            renamed = []

            for line in status_lines:
                if line.startswith('##'):
                    continue
                if len(line) >= 3:
                    status_code = line[:2]
                    filepath = line[3:].strip()

                    if 'A' in status_code or '?' in status_code:
                        added.append(filepath)
                    elif 'M' in status_code:
                        modified.append(filepath)
                    elif 'D' in status_code:
                        deleted.append(filepath)
                    elif 'R' in status_code:
                        renamed.append(filepath)

            # Categorize by type
            categories = {
                'source': [],
                'tests': [],
                'docs': [],
                'config': [],
                'other': []
            }

            all_files = added + modified + deleted + renamed
            for f in all_files:
                if 'test' in f.lower() or 'spec' in f.lower():
                    categories['tests'].append(f)
                elif f.endswith('.md') or 'docs' in f.lower() or 'readme' in f.lower():
                    categories['docs'].append(f)
                elif f.endswith(('.json', '.yaml', '.yml', '.toml', '.ini', '.cfg')):
                    categories['config'].append(f)
                elif f.endswith(('.py', '.js', '.ts', '.tsx', '.jsx', '.go', '.rs', '.java')):
                    categories['source'].append(f)
                else:
                    categories['other'].append(f)

            analysis = {
                'total_files': len(all_files),
                'added': len(added),
                'modified': len(modified),
                'deleted': len(deleted),
                'renamed': len(renamed),
                'categories': {k: len(v) for k, v in categories.items() if v},
                'files': {
                    'added': added,
                    'modified': modified,
                    'deleted': deleted,
                    'renamed': renamed,
                },
                'diff_preview': (diff_result.output or '')[:1000],
                'staged_diff': (staged_diff.output or '')[:1000],
            }

            return ToolResult(
                success=True,
                output=str(analysis),
                metadata=analysis
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _generate_commit_message(self, analysis: dict) -> CommitSuggestion:
        """Generate a commit message from change analysis"""
        categories = analysis.get('categories', {})
        files = analysis.get('files', {})

        # Determine commit type
        if categories.get('tests', 0) > categories.get('source', 0):
            commit_type = 'test'
        elif categories.get('docs', 0) > 0 and not categories.get('source', 0):
            commit_type = 'docs'
        elif categories.get('config', 0) > 0 and not categories.get('source', 0):
            commit_type = 'chore'
        elif analysis.get('added', 0) > analysis.get('modified', 0):
            commit_type = 'feat'
        else:
            commit_type = 'fix'

        # Determine scope from common path
        all_files = files.get('added', []) + files.get('modified', [])
        if all_files:
            paths = [Path(f).parts for f in all_files if f]
            if paths and len(paths[0]) > 1:
                scope = paths[0][0]  # First directory
            else:
                scope = None
        else:
            scope = None

        # Generate message
        action_map = {
            'feat': 'Add',
            'fix': 'Fix',
            'docs': 'Update documentation for',
            'test': 'Add tests for',
            'chore': 'Update',
            'refactor': 'Refactor',
        }

        action = action_map.get(commit_type, 'Update')

        if scope:
            msg = f"{commit_type}({scope}): {action} {scope} functionality"
        else:
            total = analysis.get('total_files', 0)
            msg = f"{commit_type}: {action} {total} file{'s' if total != 1 else ''}"

        # Add details
        details = []
        if files.get('added'):
            details.append(f"Added: {', '.join(files['added'][:3])}")
        if files.get('modified'):
            details.append(f"Modified: {', '.join(files['modified'][:3])}")
        if files.get('deleted'):
            details.append(f"Deleted: {', '.join(files['deleted'][:3])}")

        if details:
            msg += "\n\n" + "\n".join(details)

        return CommitSuggestion(
            message=msg,
            type=commit_type,
            scope=scope,
            breaking=False,
            files_analyzed=analysis.get('total_files', 0),
            confidence=0.75
        )

    def _smart_commit(
        self,
        message: Optional[str] = None,
        add_all: bool = True,
        push: bool = False,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """
        Smart commit with AI-generated message.

        If no message provided, analyzes changes and generates one.
        Optionally stages all changes and pushes.
        """
        try:
            # Stage files if requested
            if add_all:
                add_result = self._add(all_files=True, cwd=cwd)
                if not add_result.success:
                    return add_result

            # Analyze changes
            analysis_result = self._analyze_changes(cwd)
            if not analysis_result.success:
                return analysis_result

            analysis = analysis_result.metadata

            if analysis.get('total_files', 0) == 0:
                return ToolResult(
                    success=False,
                    error="No changes to commit"
                )

            # Generate or use provided message
            if message:
                commit_msg = message
            else:
                suggestion = self._generate_commit_message(analysis)
                commit_msg = suggestion.message

            # Commit
            commit_result = self._commit(commit_msg, cwd=cwd)
            if not commit_result.success:
                return commit_result

            # Push if requested
            if push:
                push_result = self._push(cwd=cwd)
                if not push_result.success:
                    return ToolResult(
                        success=True,
                        output=f"Committed but push failed: {push_result.error}",
                        metadata={'commit': commit_result.output, 'push_error': push_result.error}
                    )
                return ToolResult(
                    success=True,
                    output=f"Committed and pushed:\n{commit_msg}",
                    metadata={'commit': commit_result.output, 'pushed': True}
                )

            return ToolResult(
                success=True,
                output=f"Committed:\n{commit_msg}",
                metadata={'commit': commit_result.output, 'message': commit_msg}
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _suggest_branch(self, task: str, cwd: Optional[str] = None) -> ToolResult:
        """Suggest a branch name for a task description"""
        # Clean and format task for branch name
        task_clean = task.lower()
        task_clean = re.sub(r'[^a-z0-9\s-]', '', task_clean)
        task_clean = re.sub(r'\s+', '-', task_clean)
        task_clean = task_clean[:50]  # Limit length

        # Determine prefix
        prefixes = {
            'fix': ['fix', 'bug', 'error', 'issue', 'patch'],
            'feat': ['add', 'feature', 'implement', 'create', 'new'],
            'docs': ['doc', 'readme', 'documentation'],
            'refactor': ['refactor', 'cleanup', 'improve', 'optimize'],
            'test': ['test', 'spec', 'coverage'],
        }

        prefix = 'feat'  # default
        for p, keywords in prefixes.items():
            if any(kw in task.lower() for kw in keywords):
                prefix = p
                break

        branch_name = f"{prefix}/{task_clean}"

        return ToolResult(
            success=True,
            output=branch_name,
            metadata={'prefix': prefix, 'task': task}
        )

    def _generate_pr(
        self,
        title: Optional[str] = None,
        base: str = "main",
        draft: bool = False,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Generate and create a PR with AI-generated description"""
        try:
            # Get commits since base
            log_result = asyncio.get_event_loop().run_until_complete(
                self._run_git(["log", f"{base}..HEAD", "--oneline"], cwd)
            )

            commits = log_result.output.split('\n') if log_result.output else []

            # Get diff summary
            diff_result = asyncio.get_event_loop().run_until_complete(
                self._run_git(["diff", f"{base}..HEAD", "--stat"], cwd)
            )

            # Generate title from first commit or branch name
            if not title:
                branch_result = asyncio.get_event_loop().run_until_complete(
                    self._run_git(["branch", "--show-current"], cwd)
                )
                branch = branch_result.output or "feature"
                # Convert branch name to title
                title = branch.split('/')[-1].replace('-', ' ').title()

            # Generate body
            body_parts = ["## Summary\n"]

            if commits:
                body_parts.append("### Commits")
                for commit in commits[:10]:
                    body_parts.append(f"- {commit}")
                body_parts.append("")

            if diff_result.output:
                body_parts.append("### Changes")
                body_parts.append("```")
                body_parts.append(diff_result.output[:1000])
                body_parts.append("```")

            body_parts.append("\n## Test Plan")
            body_parts.append("- [ ] Tested locally")
            body_parts.append("- [ ] Unit tests pass")
            body_parts.append("")
            body_parts.append("---")
            body_parts.append("*Generated by AI Team Platform*")

            body = "\n".join(body_parts)

            # Create PR
            return self._create_pr(title, body, base, draft, cwd)

        except Exception as e:
            return ToolResult(success=False, error=str(e))


# Convenience functions
def create_git_tools(cwd: Optional[str] = None) -> GitTools:
    """Create Git tools instance"""
    return GitTools(default_cwd=cwd)


def create_smart_git_tools(
    cwd: Optional[str] = None,
    ai_callback: Optional[Callable] = None
) -> SmartGitTools:
    """Create Smart Git tools with AI features"""
    return SmartGitTools(default_cwd=cwd, ai_callback=ai_callback)
