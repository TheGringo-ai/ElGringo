"""
Frontend Development Tools - Comprehensive frontend tooling for AI agents
==========================================================================

Capabilities:
- Package managers: npm, pnpm, yarn, bun
- Build tools: Vite, Next.js, Turbopack
- Component scaffolding: React, Vue, Svelte
- Linting & formatting: ESLint, Prettier, Biome
- Testing: Vitest, Playwright, Testing Library
- Tailwind CSS utilities
- Bundle analysis & performance
- Storybook
"""

import asyncio
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import Tool, ToolResult, PermissionManager

logger = logging.getLogger(__name__)


class FrontendTools(Tool):
    """
    Comprehensive frontend development tools for AI-powered development.

    Supports modern frontend workflows with React, Next.js, Vue, Svelte,
    Tailwind CSS, and modern build tools.
    """

    def __init__(
        self,
        permission_manager: Optional[PermissionManager] = None,
        default_cwd: Optional[str] = None
    ):
        super().__init__(
            name="frontend",
            description="Frontend development tools (React, Next.js, Vue, Tailwind, Vite)",
            permission_manager=permission_manager,
        )

        self.default_cwd = default_cwd or os.getcwd()

        # Package manager operations (pnpm, yarn, bun)
        self.register_operation("pnpm_install", self._pnpm_install, "Install with pnpm")
        self.register_operation("pnpm_add", self._pnpm_add, "Add package with pnpm")
        self.register_operation("pnpm_run", self._pnpm_run, "Run pnpm script")
        self.register_operation("yarn_install", self._yarn_install, "Install with yarn")
        self.register_operation("yarn_add", self._yarn_add, "Add package with yarn")
        self.register_operation("bun_install", self._bun_install, "Install with bun")
        self.register_operation("bun_add", self._bun_add, "Add package with bun")
        self.register_operation("bun_run", self._bun_run, "Run bun script")

        # Build tools
        self.register_operation("vite_dev", self._vite_dev, "Start Vite dev server")
        self.register_operation("vite_build", self._vite_build, "Build with Vite")
        self.register_operation("vite_preview", self._vite_preview, "Preview Vite build")
        self.register_operation("next_dev", self._next_dev, "Start Next.js dev server")
        self.register_operation("next_build", self._next_build, "Build Next.js app")
        self.register_operation("next_start", self._next_start, "Start Next.js production")
        self.register_operation("turbo_run", self._turbo_run, "Run Turborepo task")

        # Linting & Formatting
        self.register_operation("eslint", self._eslint, "Run ESLint")
        self.register_operation("eslint_fix", self._eslint_fix, "Run ESLint with auto-fix")
        self.register_operation("prettier", self._prettier, "Run Prettier")
        self.register_operation("prettier_write", self._prettier_write, "Run Prettier with write")
        self.register_operation("biome_check", self._biome_check, "Run Biome check")
        self.register_operation("biome_format", self._biome_format, "Run Biome format")
        self.register_operation("tsc", self._tsc, "Run TypeScript compiler")
        self.register_operation("tsc_watch", self._tsc_watch, "Run TypeScript watch mode")

        # Testing
        self.register_operation("vitest", self._vitest, "Run Vitest tests")
        self.register_operation("vitest_watch", self._vitest_watch, "Run Vitest watch mode")
        self.register_operation("vitest_coverage", self._vitest_coverage, "Run Vitest with coverage")
        self.register_operation("playwright_test", self._playwright_test, "Run Playwright tests")
        self.register_operation("playwright_codegen", self._playwright_codegen, "Generate Playwright tests")
        self.register_operation("cypress_run", self._cypress_run, "Run Cypress tests")
        self.register_operation("cypress_open", self._cypress_open, "Open Cypress UI")

        # Tailwind CSS
        self.register_operation("tailwind_init", self._tailwind_init, "Initialize Tailwind CSS")
        self.register_operation("tailwind_build", self._tailwind_build, "Build Tailwind CSS")
        self.register_operation("tailwind_watch", self._tailwind_watch, "Watch Tailwind CSS")

        # Component scaffolding
        self.register_operation("create_component", self._create_component, "Create React/Vue component")
        self.register_operation("create_page", self._create_page, "Create Next.js/Nuxt page")
        self.register_operation("create_hook", self._create_hook, "Create React hook")
        self.register_operation("create_store", self._create_store, "Create Zustand/Pinia store")
        self.register_operation("create_api_route", self._create_api_route, "Create API route")

        # Storybook
        self.register_operation("storybook_dev", self._storybook_dev, "Start Storybook")
        self.register_operation("storybook_build", self._storybook_build, "Build Storybook")
        self.register_operation("create_story", self._create_story, "Create component story")

        # Bundle analysis & performance
        self.register_operation("analyze_bundle", self._analyze_bundle, "Analyze bundle size")
        self.register_operation("lighthouse", self._lighthouse, "Run Lighthouse audit", requires_permission=False)
        self.register_operation("check_deps", self._check_deps, "Check dependencies", requires_permission=False)
        self.register_operation("find_unused", self._find_unused, "Find unused dependencies", requires_permission=False)

        # Project scaffolding
        self.register_operation("create_next_app", self._create_next_app, "Create Next.js app")
        self.register_operation("create_vite_app", self._create_vite_app, "Create Vite app")
        self.register_operation("create_astro_app", self._create_astro_app, "Create Astro app")
        self.register_operation("create_remix_app", self._create_remix_app, "Create Remix app")

    async def _run_cmd(
        self,
        cmd: List[str],
        cwd: Optional[str] = None,
        timeout: int = 300,
        env: Optional[Dict[str, str]] = None
    ) -> ToolResult:
        """Execute a command"""
        try:
            work_dir = cwd or self.default_cwd
            process_env = os.environ.copy()
            if env:
                process_env.update(env)

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=work_dir,
                env=process_env
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
                    error=stderr_str or f"Command failed with code {process.returncode}",
                    metadata={"command": " ".join(cmd)}
                )

        except asyncio.TimeoutError:
            return ToolResult(success=False, output=None, error=f"Command timed out after {timeout}s")
        except FileNotFoundError:
            return ToolResult(success=False, output=None, error=f"Command not found: {cmd[0]}")
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _sync_run(self, *args, **kwargs) -> ToolResult:
        """Synchronous wrapper for async command execution"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self._run_cmd(*args, **kwargs))

    # ========== Package Managers ==========

    def _pnpm_install(self, cwd: Optional[str] = None) -> ToolResult:
        """Install dependencies with pnpm"""
        return self._sync_run(["pnpm", "install"], cwd)

    def _pnpm_add(
        self,
        packages: List[str],
        dev: bool = False,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Add packages with pnpm"""
        args = ["pnpm", "add"]
        if dev:
            args.append("-D")
        args.extend(packages)
        return self._sync_run(args, cwd)

    def _pnpm_run(self, script: str, cwd: Optional[str] = None) -> ToolResult:
        """Run pnpm script"""
        return self._sync_run(["pnpm", "run", script], cwd)

    def _yarn_install(self, cwd: Optional[str] = None) -> ToolResult:
        """Install dependencies with yarn"""
        return self._sync_run(["yarn", "install"], cwd)

    def _yarn_add(
        self,
        packages: List[str],
        dev: bool = False,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Add packages with yarn"""
        args = ["yarn", "add"]
        if dev:
            args.append("-D")
        args.extend(packages)
        return self._sync_run(args, cwd)

    def _bun_install(self, cwd: Optional[str] = None) -> ToolResult:
        """Install dependencies with bun"""
        return self._sync_run(["bun", "install"], cwd)

    def _bun_add(
        self,
        packages: List[str],
        dev: bool = False,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Add packages with bun"""
        args = ["bun", "add"]
        if dev:
            args.append("-d")
        args.extend(packages)
        return self._sync_run(args, cwd)

    def _bun_run(self, script: str, cwd: Optional[str] = None) -> ToolResult:
        """Run bun script"""
        return self._sync_run(["bun", "run", script], cwd)

    # ========== Build Tools ==========

    def _vite_dev(self, cwd: Optional[str] = None, port: int = 5173) -> ToolResult:
        """Start Vite dev server"""
        return self._sync_run(["npx", "vite", "--port", str(port)], cwd, timeout=10)

    def _vite_build(self, cwd: Optional[str] = None) -> ToolResult:
        """Build with Vite"""
        return self._sync_run(["npx", "vite", "build"], cwd, timeout=300)

    def _vite_preview(self, cwd: Optional[str] = None) -> ToolResult:
        """Preview Vite build"""
        return self._sync_run(["npx", "vite", "preview"], cwd, timeout=10)

    def _next_dev(self, cwd: Optional[str] = None, port: int = 3000) -> ToolResult:
        """Start Next.js dev server"""
        return self._sync_run(["npx", "next", "dev", "-p", str(port)], cwd, timeout=10)

    def _next_build(self, cwd: Optional[str] = None) -> ToolResult:
        """Build Next.js app"""
        return self._sync_run(["npx", "next", "build"], cwd, timeout=600)

    def _next_start(self, cwd: Optional[str] = None, port: int = 3000) -> ToolResult:
        """Start Next.js production server"""
        return self._sync_run(["npx", "next", "start", "-p", str(port)], cwd, timeout=10)

    def _turbo_run(self, task: str, cwd: Optional[str] = None) -> ToolResult:
        """Run Turborepo task"""
        return self._sync_run(["npx", "turbo", "run", task], cwd, timeout=600)

    # ========== Linting & Formatting ==========

    def _eslint(self, path: str = ".", cwd: Optional[str] = None) -> ToolResult:
        """Run ESLint"""
        return self._sync_run(["npx", "eslint", path], cwd)

    def _eslint_fix(self, path: str = ".", cwd: Optional[str] = None) -> ToolResult:
        """Run ESLint with auto-fix"""
        return self._sync_run(["npx", "eslint", "--fix", path], cwd)

    def _prettier(self, path: str = ".", cwd: Optional[str] = None) -> ToolResult:
        """Run Prettier check"""
        return self._sync_run(["npx", "prettier", "--check", path], cwd)

    def _prettier_write(self, path: str = ".", cwd: Optional[str] = None) -> ToolResult:
        """Run Prettier with write"""
        return self._sync_run(["npx", "prettier", "--write", path], cwd)

    def _biome_check(self, path: str = ".", cwd: Optional[str] = None) -> ToolResult:
        """Run Biome check"""
        return self._sync_run(["npx", "@biomejs/biome", "check", path], cwd)

    def _biome_format(self, path: str = ".", cwd: Optional[str] = None) -> ToolResult:
        """Run Biome format"""
        return self._sync_run(["npx", "@biomejs/biome", "format", "--write", path], cwd)

    def _tsc(self, cwd: Optional[str] = None, no_emit: bool = True) -> ToolResult:
        """Run TypeScript compiler"""
        args = ["npx", "tsc"]
        if no_emit:
            args.append("--noEmit")
        return self._sync_run(args, cwd)

    def _tsc_watch(self, cwd: Optional[str] = None) -> ToolResult:
        """Run TypeScript watch mode"""
        return self._sync_run(["npx", "tsc", "--watch", "--noEmit"], cwd, timeout=10)

    # ========== Testing ==========

    def _vitest(self, cwd: Optional[str] = None, filter: Optional[str] = None) -> ToolResult:
        """Run Vitest tests"""
        args = ["npx", "vitest", "run"]
        if filter:
            args.append(filter)
        return self._sync_run(args, cwd)

    def _vitest_watch(self, cwd: Optional[str] = None) -> ToolResult:
        """Run Vitest watch mode"""
        return self._sync_run(["npx", "vitest"], cwd, timeout=10)

    def _vitest_coverage(self, cwd: Optional[str] = None) -> ToolResult:
        """Run Vitest with coverage"""
        return self._sync_run(["npx", "vitest", "run", "--coverage"], cwd)

    def _playwright_test(
        self,
        cwd: Optional[str] = None,
        headed: bool = False,
        project: Optional[str] = None
    ) -> ToolResult:
        """Run Playwright tests"""
        args = ["npx", "playwright", "test"]
        if headed:
            args.append("--headed")
        if project:
            args.extend(["--project", project])
        return self._sync_run(args, cwd, timeout=600)

    def _playwright_codegen(self, url: str = "http://localhost:3000", cwd: Optional[str] = None) -> ToolResult:
        """Generate Playwright tests"""
        return self._sync_run(["npx", "playwright", "codegen", url], cwd, timeout=10)

    def _cypress_run(self, cwd: Optional[str] = None, spec: Optional[str] = None) -> ToolResult:
        """Run Cypress tests"""
        args = ["npx", "cypress", "run"]
        if spec:
            args.extend(["--spec", spec])
        return self._sync_run(args, cwd, timeout=600)

    def _cypress_open(self, cwd: Optional[str] = None) -> ToolResult:
        """Open Cypress UI"""
        return self._sync_run(["npx", "cypress", "open"], cwd, timeout=10)

    # ========== Tailwind CSS ==========

    def _tailwind_init(self, cwd: Optional[str] = None, full: bool = False) -> ToolResult:
        """Initialize Tailwind CSS"""
        args = ["npx", "tailwindcss", "init"]
        if full:
            args.append("--full")
        return self._sync_run(args, cwd)

    def _tailwind_build(
        self,
        input_file: str = "src/styles.css",
        output_file: str = "dist/styles.css",
        minify: bool = False,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Build Tailwind CSS"""
        args = ["npx", "tailwindcss", "-i", input_file, "-o", output_file]
        if minify:
            args.append("--minify")
        return self._sync_run(args, cwd)

    def _tailwind_watch(
        self,
        input_file: str = "src/styles.css",
        output_file: str = "dist/styles.css",
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Watch Tailwind CSS"""
        return self._sync_run(
            ["npx", "tailwindcss", "-i", input_file, "-o", output_file, "--watch"],
            cwd,
            timeout=10
        )

    # ========== Component Scaffolding ==========

    def _create_component(
        self,
        name: str,
        framework: str = "react",
        typescript: bool = True,
        with_styles: bool = True,
        with_test: bool = True,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Create a component with optional styles and test files"""
        try:
            work_dir = Path(cwd or self.default_cwd)
            ext = "tsx" if typescript else "jsx"
            style_ext = "module.css"

            # Determine component directory
            if framework == "react":
                comp_dir = work_dir / "src" / "components" / name
            elif framework == "vue":
                comp_dir = work_dir / "src" / "components" / name
                ext = "vue"
            elif framework == "svelte":
                comp_dir = work_dir / "src" / "lib" / "components"
                ext = "svelte"
            else:
                comp_dir = work_dir / "src" / "components" / name

            comp_dir.mkdir(parents=True, exist_ok=True)

            # Create component file
            if framework == "react":
                comp_content = self._react_component_template(name, typescript)
            elif framework == "vue":
                comp_content = self._vue_component_template(name, typescript)
            elif framework == "svelte":
                comp_content = self._svelte_component_template(name, typescript)
            else:
                comp_content = self._react_component_template(name, typescript)

            comp_file = comp_dir / f"{name}.{ext}"
            comp_file.write_text(comp_content)

            created_files = [str(comp_file)]

            # Create styles if requested
            if with_styles and framework == "react":
                style_file = comp_dir / f"{name}.{style_ext}"
                style_file.write_text(f".container {{\n  /* {name} styles */\n}}\n")
                created_files.append(str(style_file))

            # Create test if requested
            if with_test:
                test_file = comp_dir / f"{name}.test.{ext}"
                test_content = self._component_test_template(name, framework, typescript)
                test_file.write_text(test_content)
                created_files.append(str(test_file))

            # Create index file for exports
            if framework == "react":
                index_file = comp_dir / f"index.{ext[:-1]}"  # .ts or .js
                index_file.write_text(f'export {{ {name} }} from "./{name}";\nexport {{ default }} from "./{name}";\n')
                created_files.append(str(index_file))

            return ToolResult(
                success=True,
                output=f"Created {framework} component '{name}':\n" + "\n".join(f"  - {f}" for f in created_files),
                metadata={"component": name, "framework": framework, "files": created_files}
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _react_component_template(self, name: str, typescript: bool) -> str:
        """Generate React component template"""
        if typescript:
            return f'''import {{ type FC }} from 'react';
import styles from './{name}.module.css';

interface {name}Props {{
  className?: string;
  children?: React.ReactNode;
}}

export const {name}: FC<{name}Props> = ({{ className, children }}) => {{
  return (
    <div className={{`${{styles.container}} ${{className ?? ''}}`}}>
      {{children}}
    </div>
  );
}};

export default {name};
'''
        else:
            return f'''import styles from './{name}.module.css';

export const {name} = ({{ className, children }}) => {{
  return (
    <div className={{`${{styles.container}} ${{className ?? ''}}`}}>
      {{children}}
    </div>
  );
}};

export default {name};
'''

    def _vue_component_template(self, name: str, typescript: bool) -> str:
        """Generate Vue component template"""
        script_setup = "script setup lang=\"ts\"" if typescript else "script setup"
        return f'''<{script_setup}>
defineProps<{{
  className?: string;
}}>();
</{script_setup.split()[0]}>

<template>
  <div :class="['container', className]">
    <slot />
  </div>
</template>

<style scoped>
.container {{
  /* {name} styles */
}}
</style>
'''

    def _svelte_component_template(self, name: str, typescript: bool) -> str:
        """Generate Svelte component template"""
        script_lang = 'script lang="ts"' if typescript else "script"
        return f'''<{script_lang}>
  export let className: string = '';
</{script_lang.split()[0]}>

<div class="container {{className}}">
  <slot />
</div>

<style>
  .container {{
    /* {name} styles */
  }}
</style>
'''

    def _component_test_template(self, name: str, framework: str, typescript: bool) -> str:
        """Generate component test template"""
        if framework == "react":
            return f'''import {{ render, screen }} from '@testing-library/react';
import {{ describe, it, expect }} from 'vitest';
import {{ {name} }} from './{name}';

describe('{name}', () => {{
  it('renders children', () => {{
    render(<{name}>Test Content</{name}>);
    expect(screen.getByText('Test Content')).toBeInTheDocument();
  }});

  it('applies custom className', () => {{
    render(<{name} className="custom">Content</{name}>);
    expect(screen.getByText('Content').parentElement).toHaveClass('custom');
  }});
}});
'''
        elif framework == "vue":
            return f'''import {{ mount }} from '@vue/test-utils';
import {{ describe, it, expect }} from 'vitest';
import {name} from './{name}.vue';

describe('{name}', () => {{
  it('renders slot content', () => {{
    const wrapper = mount({name}, {{
      slots: {{ default: 'Test Content' }}
    }});
    expect(wrapper.text()).toContain('Test Content');
  }});
}});
'''
        else:
            return f'''import {{ render }} from '@testing-library/svelte';
import {{ describe, it, expect }} from 'vitest';
import {name} from './{name}.svelte';

describe('{name}', () => {{
  it('renders', () => {{
    const {{ container }} = render({name});
    expect(container).toBeTruthy();
  }});
}});
'''

    def _create_page(
        self,
        name: str,
        framework: str = "next",
        typescript: bool = True,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Create a page component"""
        try:
            work_dir = Path(cwd or self.default_cwd)
            ext = "tsx" if typescript else "jsx"

            if framework == "next":
                # Next.js App Router
                page_dir = work_dir / "app" / name.lower()
                page_dir.mkdir(parents=True, exist_ok=True)
                page_file = page_dir / f"page.{ext}"
                page_content = self._next_page_template(name, typescript)
            elif framework == "nuxt":
                page_dir = work_dir / "pages"
                page_dir.mkdir(parents=True, exist_ok=True)
                page_file = page_dir / f"{name.lower()}.vue"
                page_content = self._nuxt_page_template(name, typescript)
            else:
                page_dir = work_dir / "src" / "pages"
                page_dir.mkdir(parents=True, exist_ok=True)
                page_file = page_dir / f"{name}.{ext}"
                page_content = self._react_page_template(name, typescript)

            page_file.write_text(page_content)

            return ToolResult(
                success=True,
                output=f"Created {framework} page '{name}' at {page_file}",
                metadata={"page": name, "framework": framework, "file": str(page_file)}
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _next_page_template(self, name: str, typescript: bool) -> str:
        """Generate Next.js App Router page template"""
        return f'''import type {{ Metadata }} from 'next';

export const metadata: Metadata = {{
  title: '{name}',
  description: '{name} page',
}};

export default function {name}Page() {{
  return (
    <main className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold">{name}</h1>
    </main>
  );
}}
'''

    def _nuxt_page_template(self, name: str, typescript: bool) -> str:
        """Generate Nuxt page template"""
        script_lang = 'script setup lang="ts"' if typescript else "script setup"
        return f'''<{script_lang}>
useHead({{
  title: '{name}',
}});
</{script_lang.split()[0]}>

<template>
  <main class="container mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold">{name}</h1>
  </main>
</template>
'''

    def _react_page_template(self, name: str, typescript: bool) -> str:
        """Generate React page template"""
        return f'''export default function {name}Page() {{
  return (
    <main className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold">{name}</h1>
    </main>
  );
}}
'''

    def _create_hook(
        self,
        name: str,
        typescript: bool = True,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Create a React hook"""
        try:
            work_dir = Path(cwd or self.default_cwd)
            hooks_dir = work_dir / "src" / "hooks"
            hooks_dir.mkdir(parents=True, exist_ok=True)

            ext = "ts" if typescript else "js"
            hook_name = name if name.startswith("use") else f"use{name}"

            hook_file = hooks_dir / f"{hook_name}.{ext}"
            hook_content = self._hook_template(hook_name, typescript)
            hook_file.write_text(hook_content)

            # Create test file
            test_file = hooks_dir / f"{hook_name}.test.{ext}"
            test_content = self._hook_test_template(hook_name, typescript)
            test_file.write_text(test_content)

            return ToolResult(
                success=True,
                output=f"Created hook '{hook_name}':\n  - {hook_file}\n  - {test_file}",
                metadata={"hook": hook_name, "files": [str(hook_file), str(test_file)]}
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _hook_template(self, name: str, typescript: bool) -> str:
        """Generate React hook template"""
        state_name = name[3:] if len(name) > 3 else name
        interface_block = f"interface {state_name}State {{\n  // Define your state type\n}}\n" if typescript else ""
        state_type = f"<{state_name}State | null>(null)" if typescript else "(null)"
        error_type = "<Error | null>(null)" if typescript else "(null)"
        catch_cast = " as Error" if typescript else ""

        return f'''import {{ useState, useCallback }} from 'react';

{interface_block}
export function {name}() {{
  const [state, setState] = useState{state_type};
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState{error_type};

  const execute = useCallback(async () => {{
    setIsLoading(true);
    setError(null);
    try {{
      // Implement your logic here
    }} catch (e) {{
      setError(e{catch_cast});
    }} finally {{
      setIsLoading(false);
    }}
  }}, []);

  return {{ state, isLoading, error, execute }};
}}
'''

    def _hook_test_template(self, name: str, typescript: bool) -> str:
        """Generate React hook test template"""
        return f'''import {{ renderHook, act }} from '@testing-library/react';
import {{ describe, it, expect }} from 'vitest';
import {{ {name} }} from './{name}';

describe('{name}', () => {{
  it('returns initial state', () => {{
    const {{ result }} = renderHook(() => {name}());
    expect(result.current.state).toBeNull();
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
  }});

  it('handles execution', async () => {{
    const {{ result }} = renderHook(() => {name}());
    await act(async () => {{
      await result.current.execute();
    }});
    // Add assertions based on your hook's behavior
  }});
}});
'''

    def _create_store(
        self,
        name: str,
        library: str = "zustand",
        typescript: bool = True,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Create a state store (Zustand/Pinia)"""
        try:
            work_dir = Path(cwd or self.default_cwd)
            stores_dir = work_dir / "src" / "stores"
            stores_dir.mkdir(parents=True, exist_ok=True)

            ext = "ts" if typescript else "js"
            store_name = name.lower().replace("store", "") + "Store"

            store_file = stores_dir / f"{store_name}.{ext}"

            if library == "zustand":
                store_content = self._zustand_store_template(store_name, name, typescript)
            elif library == "pinia":
                store_content = self._pinia_store_template(store_name, name, typescript)
            else:
                return ToolResult(success=False, output=None, error=f"Unknown library: {library}")

            store_file.write_text(store_content)

            return ToolResult(
                success=True,
                output=f"Created {library} store '{store_name}' at {store_file}",
                metadata={"store": store_name, "library": library, "file": str(store_file)}
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _zustand_store_template(self, store_name: str, entity_name: str, typescript: bool) -> str:
        """Generate Zustand store template"""
        interface_name = entity_name.title().replace(" ", "")
        store_state_name = store_name.title() + "State"

        if typescript:
            entity_interface = f"""interface {interface_name} {{
  id: string;
  // Add your entity fields
}}

interface {store_state_name} {{
  items: {interface_name}[];
  isLoading: boolean;
  error: string | null;
  // Actions
  addItem: (item: {interface_name}) => void;
  removeItem: (id: string) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}}

"""
            generic_type = f"<{store_state_name}>"
        else:
            entity_interface = ""
            generic_type = ""

        return f'''import {{ create }} from 'zustand';
import {{ devtools, persist }} from 'zustand/middleware';

{entity_interface}export const {store_name} = create{generic_type}()(
  devtools(
    persist(
      (set) => ({{
        items: [],
        isLoading: false,
        error: null,

        addItem: (item) =>
          set((state) => ({{ items: [...state.items, item] }})),

        removeItem: (id) =>
          set((state) => ({{
            items: state.items.filter((item) => item.id !== id),
          }})),

        setLoading: (isLoading) => set({{ isLoading }}),
        setError: (error) => set({{ error }}),
      }}),
      {{ name: '{store_name}' }}
    )
  )
);
'''

    def _pinia_store_template(self, store_name: str, entity_name: str, typescript: bool) -> str:
        """Generate Pinia store template"""
        interface_name = entity_name.title().replace(" ", "")

        if typescript:
            entity_interface = f"""interface {interface_name} {{
  id: string;
  // Add your entity fields
}}

"""
            state_return = ": ({"
            items_type = f" as {interface_name}[]"
            error_type = " as string | null"
            id_type = ": string"
            item_type = f": {interface_name}"
        else:
            entity_interface = ""
            state_return = " => ({"
            items_type = ""
            error_type = ""
            id_type = ""
            item_type = ""

        return f'''import {{ defineStore }} from 'pinia';

{entity_interface}export const {store_name} = defineStore('{store_name}', {{
  state: (){state_return}
    items: []{items_type},
    isLoading: false,
    error: null{error_type},
  }}),

  getters: {{
    getById: (state) => (id{id_type}) =>
      state.items.find((item) => item.id === id),
  }},

  actions: {{
    addItem(item{item_type}) {{
      this.items.push(item);
    }},

    removeItem(id{id_type}) {{
      const index = this.items.findIndex((item) => item.id === id);
      if (index > -1) {{
        this.items.splice(index, 1);
      }}
    }},
  }},
}});
'''

    def _create_api_route(
        self,
        name: str,
        method: str = "GET",
        framework: str = "next",
        typescript: bool = True,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Create an API route"""
        try:
            work_dir = Path(cwd or self.default_cwd)
            ext = "ts" if typescript else "js"

            if framework == "next":
                api_dir = work_dir / "app" / "api" / name.lower()
                api_dir.mkdir(parents=True, exist_ok=True)
                api_file = api_dir / f"route.{ext}"
                api_content = self._next_api_route_template(name, method, typescript)
            else:
                api_dir = work_dir / "src" / "api"
                api_dir.mkdir(parents=True, exist_ok=True)
                api_file = api_dir / f"{name.lower()}.{ext}"
                api_content = self._express_api_template(name, method, typescript)

            api_file.write_text(api_content)

            return ToolResult(
                success=True,
                output=f"Created API route '{name}' at {api_file}",
                metadata={"route": name, "method": method, "file": str(api_file)}
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _next_api_route_template(self, name: str, method: str, typescript: bool) -> str:
        """Generate Next.js API route template"""
        methods = method.upper().split(",")
        handlers = []

        for m in methods:
            m = m.strip()
            handlers.append(f'''
export async function {m}(request{":" if typescript else ""} Request) {{
  try {{
    // Implement your {m} logic here
    return Response.json({{ message: '{name} {m} handler' }});
  }} catch (error) {{
    return Response.json(
      {{ error: 'Internal server error' }},
      {{ status: 500 }}
    );
  }}
}}''')

        return f'''import {{ NextRequest }} from 'next/server';
{"".join(handlers)}
'''

    def _express_api_template(self, name: str, method: str, typescript: bool) -> str:
        """Generate Express-style API template"""
        return f'''import {{ Router }} from 'express';

const router = Router();

router.{method.lower()}('/', async (req, res) => {{
  try {{
    // Implement your logic here
    res.json({{ message: '{name} handler' }});
  }} catch (error) {{
    res.status(500).json({{ error: 'Internal server error' }});
  }}
}});

export default router;
'''

    # ========== Storybook ==========

    def _storybook_dev(self, cwd: Optional[str] = None, port: int = 6006) -> ToolResult:
        """Start Storybook dev server"""
        return self._sync_run(["npx", "storybook", "dev", "-p", str(port)], cwd, timeout=10)

    def _storybook_build(self, cwd: Optional[str] = None) -> ToolResult:
        """Build Storybook"""
        return self._sync_run(["npx", "storybook", "build"], cwd, timeout=600)

    def _create_story(
        self,
        component_name: str,
        component_path: str,
        typescript: bool = True,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Create a Storybook story for a component"""
        try:
            work_dir = Path(cwd or self.default_cwd)
            comp_path = Path(component_path)
            ext = "tsx" if typescript else "jsx"

            story_file = comp_path.parent / f"{component_name}.stories.{ext}"

            story_content = f'''import type {{ Meta, StoryObj }} from '@storybook/react';
import {{ {component_name} }} from './{component_name}';

const meta: Meta<typeof {component_name}> = {{
  title: 'Components/{component_name}',
  component: {component_name},
  parameters: {{
    layout: 'centered',
  }},
  tags: ['autodocs'],
  argTypes: {{
    // Define your arg types here
  }},
}};

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {{
  args: {{
    // Default props
  }},
}};

export const WithContent: Story = {{
  args: {{
    children: 'Example content',
  }},
}};
'''

            (work_dir / story_file).write_text(story_content)

            return ToolResult(
                success=True,
                output=f"Created story for '{component_name}' at {story_file}",
                metadata={"component": component_name, "file": str(story_file)}
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    # ========== Bundle Analysis & Performance ==========

    def _analyze_bundle(self, cwd: Optional[str] = None) -> ToolResult:
        """Analyze bundle size"""
        return self._sync_run(["npx", "source-map-explorer", "dist/**/*.js"], cwd, timeout=120)

    def _lighthouse(self, url: str = "http://localhost:3000", cwd: Optional[str] = None) -> ToolResult:
        """Run Lighthouse audit"""
        return self._sync_run(
            ["npx", "lighthouse", url, "--output=json", "--output-path=./lighthouse-report.json"],
            cwd,
            timeout=120
        )

    def _check_deps(self, cwd: Optional[str] = None) -> ToolResult:
        """Check dependencies for issues"""
        return self._sync_run(["npx", "depcheck"], cwd)

    def _find_unused(self, cwd: Optional[str] = None) -> ToolResult:
        """Find unused dependencies"""
        return self._sync_run(["npx", "depcheck", "--json"], cwd)

    # ========== Project Scaffolding ==========

    def _create_next_app(
        self,
        name: str,
        typescript: bool = True,
        tailwind: bool = True,
        app_router: bool = True,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Create a Next.js app"""
        args = ["npx", "create-next-app@latest", name]
        if typescript:
            args.append("--typescript")
        if tailwind:
            args.append("--tailwind")
        if app_router:
            args.append("--app")
        args.append("--eslint")
        return self._sync_run(args, cwd, timeout=600)

    def _create_vite_app(
        self,
        name: str,
        template: str = "react-ts",
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Create a Vite app"""
        return self._sync_run(
            ["npm", "create", "vite@latest", name, "--", "--template", template],
            cwd,
            timeout=300
        )

    def _create_astro_app(
        self,
        name: str,
        template: str = "minimal",
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Create an Astro app"""
        return self._sync_run(
            ["npm", "create", "astro@latest", name, "--", "--template", template],
            cwd,
            timeout=300
        )

    def _create_remix_app(
        self,
        name: str,
        cwd: Optional[str] = None
    ) -> ToolResult:
        """Create a Remix app"""
        return self._sync_run(
            ["npx", "create-remix@latest", name],
            cwd,
            timeout=300
        )

    def get_capabilities(self) -> List[Dict[str, str]]:
        """Return list of Frontend tool capabilities."""
        return [
            {"name": "pnpm_install", "description": "Install with pnpm"},
            {"name": "vite_build", "description": "Build with Vite"},
            {"name": "next_build", "description": "Build Next.js app"},
            {"name": "eslint_fix", "description": "Run ESLint with auto-fix"},
            {"name": "prettier_write", "description": "Format with Prettier"},
            {"name": "vitest", "description": "Run Vitest tests"},
            {"name": "playwright_test", "description": "Run Playwright tests"},
            {"name": "tailwind_init", "description": "Initialize Tailwind CSS"},
            {"name": "create_component", "description": "Create component"},
            {"name": "create_page", "description": "Create page"},
            {"name": "create_hook", "description": "Create React hook"},
            {"name": "create_store", "description": "Create state store"},
            {"name": "storybook_dev", "description": "Start Storybook"},
            {"name": "analyze_bundle", "description": "Analyze bundle size"},
            {"name": "create_next_app", "description": "Create Next.js app"},
        ]


# Convenience function
def create_frontend_tools(cwd: Optional[str] = None) -> FrontendTools:
    """Create Frontend tools instance"""
    return FrontendTools(default_cwd=cwd)
