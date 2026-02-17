"""
Code Analyzer
=============
AST-based code analysis for understanding code structure.

This helps the AI team:
- Understand code structure without ML
- Find dependencies and relationships
- Detect patterns and anti-patterns
- Generate better code suggestions

Usage:
    analyzer = CodeAnalyzer()

    # Analyze a file
    analysis = analyzer.analyze_file("app.py")
    print(analysis.functions)
    print(analysis.imports)
    print(analysis.complexity)

    # Analyze a project
    project_analysis = analyzer.analyze_project("/path/to/project")
"""

import ast
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class FunctionInfo:
    """Information about a function/method"""
    name: str
    start_line: int
    end_line: int
    args: List[str]
    returns: Optional[str]
    docstring: Optional[str]
    is_async: bool
    is_method: bool
    decorators: List[str]
    complexity: int  # Cyclomatic complexity estimate
    calls: List[str]  # Functions called within


@dataclass
class ClassInfo:
    """Information about a class"""
    name: str
    start_line: int
    end_line: int
    bases: List[str]
    methods: List[FunctionInfo]
    attributes: List[str]
    docstring: Optional[str]
    decorators: List[str]


@dataclass
class ImportInfo:
    """Information about imports"""
    module: str
    names: List[str]
    is_from: bool
    line: int


@dataclass
class FileAnalysis:
    """Complete analysis of a file"""
    path: str
    language: str
    lines: int
    functions: List[FunctionInfo]
    classes: List[ClassInfo]
    imports: List[ImportInfo]
    global_vars: List[str]
    todos: List[Tuple[int, str]]  # (line, comment)
    complexity_score: float
    issues: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "path": self.path,
            "language": self.language,
            "lines": self.lines,
            "functions": len(self.functions),
            "classes": len(self.classes),
            "imports": len(self.imports),
            "complexity_score": self.complexity_score,
            "issues": self.issues,
        }

    def get_summary(self) -> str:
        """Get human-readable summary"""
        return f"""
File: {self.path}
Language: {self.language}
Lines: {self.lines}
Functions: {len(self.functions)}
Classes: {len(self.classes)}
Imports: {len(self.imports)}
Complexity: {self.complexity_score:.1f}
Issues: {len(self.issues)}
""".strip()


@dataclass
class ProjectAnalysis:
    """Analysis of an entire project"""
    path: str
    files: List[FileAnalysis]
    total_lines: int
    total_functions: int
    total_classes: int
    languages: Dict[str, int]  # language -> file count
    dependency_graph: Dict[str, List[str]]  # file -> imports from project
    issues: List[Dict[str, Any]]

    def get_summary(self) -> str:
        """Get project summary"""
        return f"""
Project: {self.path}
Files: {len(self.files)}
Total Lines: {self.total_lines}
Functions: {self.total_functions}
Classes: {self.total_classes}
Languages: {', '.join(f'{k}: {v}' for k, v in self.languages.items())}
Issues: {len(self.issues)}
""".strip()


class CodeAnalyzer:
    """
    Analyzes code structure using AST parsing.

    Supports:
    - Python (full AST analysis)
    - JavaScript/TypeScript (regex-based)
    - Other languages (basic analysis)
    """

    def __init__(self):
        self._cache: Dict[str, FileAnalysis] = {}

    def analyze_code(
        self,
        code: str,
        language: str = "python",
        file_path: str = "<string>",
    ) -> FileAnalysis:
        """
        Analyze code content.

        Args:
            code: Source code
            language: Programming language
            file_path: File path for reference

        Returns:
            FileAnalysis with structure information
        """
        if language == "python":
            return self._analyze_python(code, file_path)
        elif language in ["javascript", "typescript"]:
            return self._analyze_javascript(code, file_path, language)
        else:
            return self._analyze_generic(code, file_path, language)

    def analyze_file(self, file_path: str) -> FileAnalysis:
        """
        Analyze a file.

        Args:
            file_path: Path to file

        Returns:
            FileAnalysis
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Check cache
        cache_key = f"{path.resolve()}:{path.stat().st_mtime}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Detect language
        ext = path.suffix.lower()
        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".rs": "rust",
            ".go": "go",
            ".java": "java",
        }
        language = language_map.get(ext, "unknown")

        # Read and analyze
        content = path.read_text(errors="ignore")
        analysis = self.analyze_code(content, language, str(path))

        # Cache result
        self._cache[cache_key] = analysis
        return analysis

    def analyze_project(
        self,
        project_path: str,
        exclude_patterns: Optional[List[str]] = None,
    ) -> ProjectAnalysis:
        """
        Analyze an entire project.

        Args:
            project_path: Path to project root
            exclude_patterns: Patterns to exclude

        Returns:
            ProjectAnalysis
        """
        project_path = Path(project_path).resolve()
        exclude_patterns = exclude_patterns or [
            "node_modules", ".git", "venv", "__pycache__",
            "dist", "build", ".egg-info",
        ]

        # Find all code files
        extensions = [".py", ".js", ".jsx", ".ts", ".tsx", ".rs", ".go", ".java"]
        files = []
        for ext in extensions:
            for f in project_path.rglob(f"*{ext}"):
                # Check exclusions
                if any(excl in str(f) for excl in exclude_patterns):
                    continue
                files.append(f)

        # Analyze each file
        analyses = []
        languages: Dict[str, int] = defaultdict(int)

        for file_path in files:
            try:
                analysis = self.analyze_file(str(file_path))
                analyses.append(analysis)
                languages[analysis.language] += 1
            except Exception as e:
                logger.warning(f"Failed to analyze {file_path}: {e}")

        # Build dependency graph (for Python)
        dep_graph = self._build_dependency_graph(analyses, project_path)

        # Aggregate statistics
        total_lines = sum(a.lines for a in analyses)
        total_functions = sum(len(a.functions) for a in analyses)
        total_classes = sum(len(a.classes) for a in analyses)

        # Collect all issues
        all_issues = []
        for a in analyses:
            for issue in a.issues:
                issue["file"] = a.path
                all_issues.append(issue)

        return ProjectAnalysis(
            path=str(project_path),
            files=analyses,
            total_lines=total_lines,
            total_functions=total_functions,
            total_classes=total_classes,
            languages=dict(languages),
            dependency_graph=dep_graph,
            issues=all_issues,
        )

    def _analyze_python(self, code: str, file_path: str) -> FileAnalysis:
        """Analyze Python code using AST"""
        functions = []
        classes = []
        imports = []
        global_vars = []
        todos = []
        issues = []

        lines = code.split('\n')
        line_count = len(lines)

        # Find TODOs in comments
        for i, line in enumerate(lines, 1):
            if '#' in line and 'TODO' in line.upper():
                comment = line.split('#', 1)[1].strip()
                todos.append((i, comment))

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            issues.append({
                "type": "syntax_error",
                "message": str(e),
                "line": e.lineno,
            })
            return FileAnalysis(
                path=file_path,
                language="python",
                lines=line_count,
                functions=[],
                classes=[],
                imports=[],
                global_vars=[],
                todos=todos,
                complexity_score=0,
                issues=issues,
            )

        # Walk the AST - process top-level items
        for node in tree.body:
            # Functions at module level
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_info = self._extract_function_info(node, code)
                functions.append(func_info)

            # Classes
            elif isinstance(node, ast.ClassDef):
                class_info = self._extract_class_info(node, code)
                classes.append(class_info)

            # Imports
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(ImportInfo(
                        module=alias.name,
                        names=[alias.asname or alias.name],
                        is_from=False,
                        line=node.lineno,
                    ))

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                imports.append(ImportInfo(
                    module=module,
                    names=[alias.name for alias in node.names],
                    is_from=True,
                    line=node.lineno,
                ))

            # Global assignments (module level)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        global_vars.append(target.id)

        # Calculate complexity
        complexity = self._calculate_complexity(tree)

        # Check for common issues
        issues.extend(self._check_python_issues(tree, code))

        return FileAnalysis(
            path=file_path,
            language="python",
            lines=line_count,
            functions=functions,
            classes=classes,
            imports=imports,
            global_vars=global_vars,
            todos=todos,
            complexity_score=complexity,
            issues=issues,
        )

    def _extract_function_info(self, node: ast.FunctionDef, code: str) -> FunctionInfo:
        """Extract function information from AST node"""
        # Get arguments
        args = []
        for arg in node.args.args:
            args.append(arg.arg)

        # Get return annotation
        returns = None
        if node.returns:
            returns = ast.unparse(node.returns) if hasattr(ast, 'unparse') else str(node.returns)

        # Get docstring
        docstring = ast.get_docstring(node)

        # Get decorators
        decorators = []
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                decorators.append(dec.id)
            elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name):
                decorators.append(dec.func.id)

        # Calculate complexity
        complexity = self._node_complexity(node)

        # Find function calls
        calls = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    calls.append(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    calls.append(child.func.attr)

        return FunctionInfo(
            name=node.name,
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            args=args,
            returns=returns,
            docstring=docstring,
            is_async=isinstance(node, ast.AsyncFunctionDef),
            is_method=False,
            decorators=decorators,
            complexity=complexity,
            calls=list(set(calls)),
        )

    def _extract_class_info(self, node: ast.ClassDef, code: str) -> ClassInfo:
        """Extract class information from AST node"""
        # Get base classes
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(f"{base.value.id}.{base.attr}" if isinstance(base.value, ast.Name) else base.attr)

        # Get methods
        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_info = self._extract_function_info(item, code)
                func_info.is_method = True
                methods.append(func_info)

        # Get class attributes
        attributes = []
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        attributes.append(target.id)

        # Get docstring
        docstring = ast.get_docstring(node)

        # Get decorators
        decorators = []
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                decorators.append(dec.id)

        return ClassInfo(
            name=node.name,
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            bases=bases,
            methods=methods,
            attributes=attributes,
            docstring=docstring,
            decorators=decorators,
        )

    def _node_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity of a node"""
        complexity = 1

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, (ast.And, ast.Or)):
                complexity += 1
            elif isinstance(child, ast.comprehension):
                complexity += 1

        return complexity

    def _calculate_complexity(self, tree: ast.AST) -> float:
        """Calculate overall file complexity"""
        total = 0
        count = 0

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                total += self._node_complexity(node)
                count += 1

        return total / max(count, 1)

    def _check_python_issues(self, tree: ast.AST, code: str) -> List[Dict[str, Any]]:
        """Check for common Python issues"""
        issues = []

        for node in ast.walk(tree):
            # Check for bare except
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                issues.append({
                    "type": "bare_except",
                    "message": "Bare 'except:' clause catches all exceptions",
                    "line": node.lineno,
                    "severity": "warning",
                })

            # Check for mutable default arguments
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for default in node.args.defaults + node.args.kw_defaults:
                    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        issues.append({
                            "type": "mutable_default",
                            "message": f"Mutable default argument in function '{node.name}'",
                            "line": node.lineno,
                            "severity": "warning",
                        })
                        break

            # Check for unused imports (simplified)
            # Would need more sophisticated analysis

        return issues

    def _analyze_javascript(self, code: str, file_path: str, language: str) -> FileAnalysis:
        """Analyze JavaScript/TypeScript using regex"""
        functions = []
        classes = []
        imports = []
        todos = []
        issues = []

        lines = code.split('\n')
        line_count = len(lines)

        # Find functions
        func_pattern = r'(?:async\s+)?function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function|\([^)]*\)\s*=>)'
        for match in re.finditer(func_pattern, code):
            name = match.group(1) or match.group(2)
            line = code[:match.start()].count('\n') + 1
            functions.append(FunctionInfo(
                name=name,
                start_line=line,
                end_line=line,
                args=[],
                returns=None,
                docstring=None,
                is_async='async' in match.group(0),
                is_method=False,
                decorators=[],
                complexity=1,
                calls=[],
            ))

        # Find classes
        class_pattern = r'class\s+(\w+)(?:\s+extends\s+(\w+))?'
        for match in re.finditer(class_pattern, code):
            name = match.group(1)
            base = match.group(2)
            line = code[:match.start()].count('\n') + 1
            classes.append(ClassInfo(
                name=name,
                start_line=line,
                end_line=line,
                bases=[base] if base else [],
                methods=[],
                attributes=[],
                docstring=None,
                decorators=[],
            ))

        # Find imports
        import_pattern = r'import\s+(?:{\s*([^}]+)\s*}|\*\s+as\s+(\w+)|(\w+))\s+from\s+[\'"]([^\'"]+)[\'"]'
        for match in re.finditer(import_pattern, code):
            names = match.group(1) or match.group(2) or match.group(3)
            module = match.group(4)
            line = code[:match.start()].count('\n') + 1
            imports.append(ImportInfo(
                module=module,
                names=names.split(',') if ',' in (names or '') else [names] if names else [],
                is_from=True,
                line=line,
            ))

        # Find TODOs
        for i, line in enumerate(lines, 1):
            if '//' in line and 'TODO' in line.upper():
                comment = line.split('//', 1)[1].strip()
                todos.append((i, comment))

        return FileAnalysis(
            path=file_path,
            language=language,
            lines=line_count,
            functions=functions,
            classes=classes,
            imports=imports,
            global_vars=[],
            todos=todos,
            complexity_score=len(functions) * 1.5,  # Rough estimate
            issues=issues,
        )

    def _analyze_generic(self, code: str, file_path: str, language: str) -> FileAnalysis:
        """Basic analysis for other languages"""
        lines = code.split('\n')
        line_count = len(lines)

        # Count approximate functions/methods
        func_count = len(re.findall(r'\bfn\s+\w+|\bfunc\s+\w+|\bdef\s+\w+|function\s+\w+', code))

        # Find TODOs
        todos = []
        for i, line in enumerate(lines, 1):
            if 'TODO' in line.upper():
                todos.append((i, line.strip()))

        return FileAnalysis(
            path=file_path,
            language=language,
            lines=line_count,
            functions=[],
            classes=[],
            imports=[],
            global_vars=[],
            todos=todos,
            complexity_score=func_count * 2.0,
            issues=[],
        )

    def _build_dependency_graph(
        self,
        analyses: List[FileAnalysis],
        project_path: Path,
    ) -> Dict[str, List[str]]:
        """Build internal dependency graph"""
        graph = {}

        # Get all module names
        module_names = set()
        for a in analyses:
            if a.language == "python":
                rel_path = Path(a.path).relative_to(project_path)
                module = str(rel_path.with_suffix('')).replace('/', '.')
                module_names.add(module)

        # Build graph
        for a in analyses:
            deps = []
            for imp in a.imports:
                if imp.module in module_names or any(
                    imp.module.startswith(m + '.') for m in module_names
                ):
                    deps.append(imp.module)
            graph[a.path] = deps

        return graph

    def find_function(
        self,
        project_path: str,
        function_name: str,
    ) -> List[Dict[str, Any]]:
        """Find a function by name across the project"""
        analysis = self.analyze_project(project_path)
        results = []

        for file_analysis in analysis.files:
            for func in file_analysis.functions:
                if func.name == function_name:
                    results.append({
                        "file": file_analysis.path,
                        "function": func,
                    })
            for cls in file_analysis.classes:
                for method in cls.methods:
                    if method.name == function_name:
                        results.append({
                            "file": file_analysis.path,
                            "class": cls.name,
                            "method": method,
                        })

        return results

    def get_function_context(
        self,
        file_path: str,
        function_name: str,
    ) -> Optional[str]:
        """Get the full context of a function"""
        analysis = self.analyze_file(file_path)

        # Find the function
        for func in analysis.functions:
            if func.name == function_name:
                # Read the actual code
                with open(file_path) as f:
                    lines = f.readlines()
                return ''.join(lines[func.start_line - 1:func.end_line])

        # Check methods
        for cls in analysis.classes:
            for method in cls.methods:
                if method.name == function_name:
                    with open(file_path) as f:
                        lines = f.readlines()
                    return ''.join(lines[method.start_line - 1:method.end_line])

        return None
