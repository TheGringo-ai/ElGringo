#!/usr/bin/env python3
"""
El Gringo Coding Agent - Autonomous Code Generation & Editing
===========================================================

This agent can:
- Read existing code
- Write new files
- Edit existing files
- Run tests
- Debug issues
- Review code

Usage:
    python coding_agent.py create "Create a FastAPI endpoint for user auth"
    python coding_agent.py edit "Fix the bug in auth.py line 45"
    python coding_agent.py review "Review all Python files for security"
    python coding_agent.py test "Run tests and fix failures"
"""

import asyncio
import sys
from pathlib import Path
from ai_dev_team.orchestrator import AIDevTeam
from ai_dev_team.tools.filesystem import FileSystemTools
from ai_dev_team.tools.base import PermissionManager


class CodingAgent:
    """Autonomous coding agent powered by El Gringo team"""
    
    def __init__(self, project_path: str = "."):
        self.project_path = Path(project_path).resolve()
        
        # Initialize AI team with file access
        self.team = AIDevTeam(
            project_name=self.project_path.name,
            enable_memory=True,
            enable_learning=True
        )
        
        # Initialize file tools with permissions for this project
        self.permission_manager = PermissionManager()
        # Tools will check permissions, but we'll work within safe paths
        self.fs_tools = FileSystemTools(self.permission_manager)
        
        print(f"🤖 El Gringo Coding Agent initialized")
        print(f"📁 Project: {self.project_path}")
        print(f"👥 AI Team: {', '.join(self.team.agents.keys())}")
        print()
    
    async def create_code(self, description: str):
        """Create new code files based on description"""
        print(f"📝 Creating code: {description}\n")
        
        # Get file structure first
        task = f"""You are a coding agent. Create the following:

{description}

IMPORTANT: You have access to filesystem tools. Use them to:
1. Create necessary directories
2. Write the code files
3. Provide a summary of what was created

Project root: {self.project_path}

Think step by step:
1. What files need to be created?
2. What directories are needed?
3. What should each file contain?

Then use the filesystem tools to actually create the files.
"""
        
        result = await self.team.collaborate(
            task,
            mode="sequential",  # Sequential ensures proper ordering
            tools=[self.fs_tools]
        )
        
        print("\n" + "="*80)
        print("✅ RESULT")
        print("="*80)
        print(result.final_answer)
        print()
        
        return result
    
    async def edit_code(self, description: str, file_path: str = None):
        """Edit existing code based on description"""
        print(f"✏️  Editing code: {description}\n")
        
        # If specific file provided, read it first
        file_context = ""
        if file_path:
            full_path = self.project_path / file_path
            read_result = self.fs_tools.execute("read", path=str(full_path))
            if read_result.success:
                file_context = f"""
Current file contents of {file_path}:
```
{read_result.output}
```
"""
            else:
                file_context = f"Note: Could not read {file_path} - {read_result.error}"
        
        task = f"""You are a coding agent. Make the following changes:

{description}

{file_context}

Project root: {self.project_path}

IMPORTANT: Use filesystem tools to:
1. Read the relevant files
2. Make the changes
3. Write the updated files back

Provide a clear summary of what you changed.
"""
        
        result = await self.team.collaborate(
            task,
            mode="consensus",  # Consensus for better decision making
            tools=[self.fs_tools]
        )
        
        print("\n" + "="*80)
        print("✅ RESULT")
        print("="*80)
        print(result.final_answer)
        print()
        
        return result
    
    async def review_code(self, pattern: str = "**/*.py"):
        """Review code for issues"""
        print(f"🔍 Reviewing code matching: {pattern}\n")
        
        # Find matching files
        files = list(self.project_path.glob(pattern))
        
        if not files:
            print(f"❌ No files found matching: {pattern}")
            return
        
        print(f"📋 Found {len(files)} files to review\n")
        
        # Review each file
        reviews = []
        for file in files[:10]:  # Limit to first 10 for now
            relative_path = file.relative_to(self.project_path)
            read_result = self.fs_tools.execute("read", path=str(file))
            
            if not read_result.success:
                continue
            
            task = f"""Review this Python file for:
1. Security vulnerabilities
2. Code quality issues
3. Performance problems
4. Best practice violations

File: {relative_path}
```python
{read_result.output[:2000]}  # First 2000 chars
```

Provide specific, actionable feedback.
"""
            
            result = await self.team.collaborate(task, mode="peer_review")
            reviews.append(f"\n{'='*80}\n📄 {relative_path}\n{'='*80}\n{result.final_answer}")
        
        # Combine reviews
        print("\n".join(reviews))
        return reviews
    
    async def fix_issues(self, error_message: str, context: str = ""):
        """Debug and fix issues"""
        print(f"🐛 Fixing issue: {error_message}\n")
        
        task = f"""You are a debugging agent. Fix this issue:

Error: {error_message}

Context: {context}

Project root: {self.project_path}

Steps:
1. Analyze the error
2. Find the relevant code files
3. Identify the root cause
4. Fix the issue using filesystem tools
5. Explain what you fixed

Use filesystem tools to read and write files as needed.
"""
        
        result = await self.team.collaborate(
            task,
            mode="sequential",
            tools=[self.fs_tools]
        )
        
        print("\n" + "="*80)
        print("✅ RESULT")
        print("="*80)
        print(result.final_answer)
        print()
        
        return result
    
    async def run_tests(self):
        """Run tests and fix failures"""
        print("🧪 Running tests and fixing failures\n")
        
        # This would integrate with pytest/unittest
        # For now, just show the pattern
        task = f"""You are a testing agent. Do the following:

1. Find test files in {self.project_path}
2. Run them (use shell tools if available)
3. If any fail, analyze the failures
4. Fix the code causing failures
5. Re-run tests to verify

Provide a summary of test results and fixes applied.
"""
        
        result = await self.team.collaborate(
            task,
            mode="sequential",
            tools=[self.fs_tools]
        )
        
        print(result.final_answer)
        return result


async def main():
    """CLI interface"""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1]
    
    # Get project path (current directory by default)
    project_path = sys.argv[2] if len(sys.argv) > 2 and Path(sys.argv[2]).is_dir() else "."
    
    # Get description/pattern
    description = " ".join(sys.argv[2:]) if command in ["create", "edit", "fix"] else None
    
    agent = CodingAgent(project_path)
    
    try:
        if command == "create":
            if not description:
                print("❌ Usage: coding_agent.py create <description>")
                sys.exit(1)
            await agent.create_code(description)
        
        elif command == "edit":
            if not description:
                print("❌ Usage: coding_agent.py edit <description> [file_path]")
                sys.exit(1)
            # Check if last arg is a file path
            parts = description.split()
            file_path = parts[-1] if Path(parts[-1]).exists() else None
            desc = " ".join(parts[:-1]) if file_path else description
            await agent.edit_code(desc, file_path)
        
        elif command == "review":
            pattern = sys.argv[2] if len(sys.argv) > 2 else "**/*.py"
            await agent.review_code(pattern)
        
        elif command == "fix":
            if not description:
                print("❌ Usage: coding_agent.py fix <error_message> [context]")
                sys.exit(1)
            await agent.fix_issues(description)
        
        elif command == "test":
            await agent.run_tests()
        
        else:
            print(f"❌ Unknown command: {command}")
            print(__doc__)
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
