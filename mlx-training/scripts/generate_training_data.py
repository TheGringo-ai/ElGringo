#!/usr/bin/env python3
"""
Training Data Generator for AI Team Platform
=============================================

Extracts training examples from:
1. Python/TypeScript source code (functions, classes, patterns)
2. CodingKnowledgeHub (snippets, error fixes, patterns)
3. RAG conversation history
4. Documentation and docstrings

Outputs in multiple formats:
- MLX (messages format)
- OpenAI (messages format for fine-tuning)
- Google (text format for Gemini)
- Alpaca (instruction/input/output format)

Usage:
    python generate_training_data.py --source /path/to/project --output ./data/training
    python generate_training_data.py --all  # Generate from AITeamPlatform
"""

import argparse
import ast
import hashlib
import json
import logging
import random
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@dataclass
class TrainingExample:
    """A single training example."""
    instruction: str
    response: str
    source: str  # file, snippet, conversation, etc.
    category: str  # coding, debugging, explanation, etc.
    language: str = "python"
    quality_score: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_mlx_format(self) -> Dict:
        """Convert to MLX messages format."""
        return {
            "messages": [
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": self.instruction},
                {"role": "assistant", "content": self.response}
            ]
        }

    def to_openai_format(self) -> Dict:
        """Convert to OpenAI fine-tuning format."""
        return {
            "messages": [
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": self.instruction},
                {"role": "assistant", "content": self.response}
            ]
        }

    def to_alpaca_format(self) -> Dict:
        """Convert to Alpaca instruction format."""
        return {
            "instruction": self.instruction,
            "input": "",
            "output": self.response
        }

    def to_text_format(self) -> str:
        """Convert to plain text format (for Gemini)."""
        return f"### Instruction:\n{self.instruction}\n\n### Response:\n{self.response}"

    def _get_system_prompt(self) -> str:
        """Get appropriate system prompt based on category."""
        prompts = {
            "coding": "You are an expert software developer. Write clean, efficient, and well-documented code.",
            "debugging": "You are an expert debugger. Analyze errors and provide clear solutions with explanations.",
            "explanation": "You are a technical educator. Explain concepts clearly with examples.",
            "firebase": "You are an expert Firebase and Firestore developer. Write secure, efficient Firebase code.",
            "react": "You are an expert React developer. Write modern, type-safe React components.",
            "architecture": "You are a software architect. Design scalable, maintainable systems.",
        }
        return prompts.get(self.category, prompts["coding"])

    def get_hash(self) -> str:
        """Get unique hash for deduplication."""
        content = f"{self.instruction}|{self.response}"
        return hashlib.md5(content.encode()).hexdigest()[:12]


class PythonCodeExtractor:
    """Extract training examples from Python source files."""

    def __init__(self):
        self.instruction_templates = {
            "function": [
                "Write a Python function called '{name}' that {description}",
                "Implement a function named '{name}' to {description}",
                "Create a Python function '{name}' that {description}",
            ],
            "class": [
                "Write a Python class called '{name}' that {description}",
                "Implement a class named '{name}' to {description}",
                "Create a Python class '{name}' for {description}",
            ],
            "method": [
                "Write a method called '{name}' for the {class_name} class that {description}",
                "Implement the '{name}' method that {description}",
                "Add a method '{name}' to {description}",
            ],
        }

    def extract_from_file(self, file_path: str) -> List[TrainingExample]:
        """Extract training examples from a Python file."""
        examples = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()

            tree = ast.parse(source)
            lines = source.split('\n')

            # Extract functions
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    example = self._extract_function(node, lines, file_path)
                    if example:
                        examples.append(example)

                elif isinstance(node, ast.ClassDef):
                    example = self._extract_class(node, lines, file_path)
                    if example:
                        examples.append(example)

        except Exception as e:
            logger.debug(f"Error parsing {file_path}: {e}")

        return examples

    def _extract_function(self, node: ast.FunctionDef, lines: List[str], file_path: str) -> Optional[TrainingExample]:
        """Extract a training example from a function."""
        # Skip private/magic methods and very short functions
        if node.name.startswith('_') and not node.name.startswith('__init__'):
            return None

        # Get function code
        start_line = node.lineno - 1
        end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line + 20
        code = '\n'.join(lines[start_line:end_line])

        # Skip trivial functions
        if len(code.strip()) < 50 or code.count('\n') < 3:
            return None

        # Get docstring for description
        docstring = ast.get_docstring(node) or ""
        description = self._extract_description(docstring, node.name)

        if not description:
            return None

        # Generate instruction
        template = random.choice(self.instruction_templates["function"])
        instruction = template.format(name=node.name, description=description)

        # Detect category from content
        category = self._detect_category(code, docstring)

        return TrainingExample(
            instruction=instruction,
            response=code,
            source=file_path,
            category=category,
            language="python",
            quality_score=self._calculate_quality(code, docstring),
            metadata={"function_name": node.name, "has_docstring": bool(docstring)}
        )

    def _extract_class(self, node: ast.ClassDef, lines: List[str], file_path: str) -> Optional[TrainingExample]:
        """Extract a training example from a class."""
        # Skip private classes
        if node.name.startswith('_'):
            return None

        # Get class code
        start_line = node.lineno - 1
        end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line + 50
        code = '\n'.join(lines[start_line:end_line])

        # Skip very short or very long classes
        if len(code.strip()) < 100 or len(code) > 5000:
            return None

        # Get docstring
        docstring = ast.get_docstring(node) or ""
        description = self._extract_description(docstring, node.name)

        if not description:
            return None

        # Generate instruction
        template = random.choice(self.instruction_templates["class"])
        instruction = template.format(name=node.name, description=description)

        category = self._detect_category(code, docstring)

        return TrainingExample(
            instruction=instruction,
            response=code,
            source=file_path,
            category=category,
            language="python",
            quality_score=self._calculate_quality(code, docstring),
            metadata={"class_name": node.name, "has_docstring": bool(docstring)}
        )

    def _extract_description(self, docstring: str, name: str) -> str:
        """Extract a clean description from docstring or generate from name."""
        if docstring:
            # Get first sentence/line
            first_line = docstring.split('\n')[0].strip()
            if first_line and len(first_line) > 10:
                return first_line.lower().rstrip('.')

        # Generate from name
        # Convert camelCase/snake_case to description
        words = re.sub(r'([A-Z])', r' \1', name)
        words = words.replace('_', ' ').lower().strip()

        if len(words) > 3:
            return words

        return ""

    def _detect_category(self, code: str, docstring: str) -> str:
        """Detect the category of code."""
        combined = (code + " " + docstring).lower()

        if any(k in combined for k in ['firebase', 'firestore', 'auth.', 'storage.']):
            return "firebase"
        elif any(k in combined for k in ['react', 'component', 'usestate', 'useeffect']):
            return "react"
        elif any(k in combined for k in ['test', 'assert', 'mock', 'pytest']):
            return "testing"
        elif any(k in combined for k in ['error', 'exception', 'debug', 'fix']):
            return "debugging"
        elif any(k in combined for k in ['api', 'endpoint', 'request', 'response']):
            return "api"
        elif any(k in combined for k in ['async', 'await', 'concurrent']):
            return "async"
        else:
            return "coding"

    def _calculate_quality(self, code: str, docstring: str) -> float:
        """Calculate quality score for the example."""
        score = 0.5

        # Has docstring
        if docstring:
            score += 0.2

        # Has type hints
        if ':' in code and '->' in code:
            score += 0.1

        # Reasonable length
        lines = code.count('\n')
        if 5 <= lines <= 50:
            score += 0.1

        # Has comments
        if '#' in code:
            score += 0.05

        # No print statements (cleaner code)
        if 'print(' not in code:
            score += 0.05

        return min(score, 1.0)


class TypeScriptExtractor:
    """Extract training examples from TypeScript/JavaScript files."""

    def extract_from_file(self, file_path: str) -> List[TrainingExample]:
        """Extract training examples from a TypeScript file."""
        examples = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract functions with JSDoc
            examples.extend(self._extract_functions(content, file_path))

            # Extract React components
            examples.extend(self._extract_components(content, file_path))

            # Extract interfaces/types
            examples.extend(self._extract_types(content, file_path))

        except Exception as e:
            logger.debug(f"Error parsing {file_path}: {e}")

        return examples

    def _extract_functions(self, content: str, file_path: str) -> List[TrainingExample]:
        """Extract functions with JSDoc comments."""
        examples = []

        # Match JSDoc + function
        pattern = r'/\*\*\s*(.*?)\s*\*/\s*((?:export\s+)?(?:async\s+)?function\s+(\w+)[^}]+\})'
        matches = re.findall(pattern, content, re.DOTALL)

        for jsdoc, func_code, func_name in matches:
            if len(func_code) < 50:
                continue

            # Clean JSDoc
            description = re.sub(r'\n\s*\*\s*', ' ', jsdoc).strip()
            description = re.sub(r'@\w+.*', '', description).strip()

            if not description:
                continue

            instruction = f"Write a TypeScript function called '{func_name}' that {description.lower()}"

            examples.append(TrainingExample(
                instruction=instruction,
                response=func_code,
                source=file_path,
                category="coding",
                language="typescript",
                quality_score=0.8,
                metadata={"function_name": func_name}
            ))

        return examples

    def _extract_components(self, content: str, file_path: str) -> List[TrainingExample]:
        """Extract React components."""
        examples = []

        # Match React functional components
        pattern = r'((?:export\s+)?(?:const|function)\s+(\w+)(?::\s*React\.FC[^=]*)?[^{]*\{[^}]+return\s*\([^)]+\)[^}]+\})'
        matches = re.findall(pattern, content, re.DOTALL)

        for component_code, component_name in matches:
            if len(component_code) < 100 or not component_name[0].isupper():
                continue

            instruction = f"Write a React component called '{component_name}'"

            examples.append(TrainingExample(
                instruction=instruction,
                response=component_code,
                source=file_path,
                category="react",
                language="typescript",
                quality_score=0.7,
                metadata={"component_name": component_name}
            ))

        return examples

    def _extract_types(self, content: str, file_path: str) -> List[TrainingExample]:
        """Extract TypeScript interfaces and types."""
        examples = []

        # Match interfaces
        pattern = r'((?:export\s+)?interface\s+(\w+)\s*\{[^}]+\})'
        matches = re.findall(pattern, content, re.DOTALL)

        for interface_code, interface_name in matches:
            instruction = f"Write a TypeScript interface called '{interface_name}'"

            examples.append(TrainingExample(
                instruction=instruction,
                response=interface_code,
                source=file_path,
                category="coding",
                language="typescript",
                quality_score=0.6,
                metadata={"interface_name": interface_name}
            ))

        return examples


class KnowledgeHubExtractor:
    """Extract training examples from CodingKnowledgeHub."""

    def extract_all(self) -> List[TrainingExample]:
        """Extract all examples from the knowledge hub."""
        examples = []

        try:
            from elgringo.knowledge import get_coding_hub
            hub = get_coding_hub()

            # Extract snippets
            for snippet in hub._snippets:
                instruction = f"Write {snippet.language} code to {snippet.title.lower()}"
                if snippet.description:
                    instruction = f"{snippet.description}"

                examples.append(TrainingExample(
                    instruction=instruction,
                    response=snippet.code,
                    source="coding_hub:snippet",
                    category=snippet.category,
                    language=snippet.language,
                    quality_score=min(0.5 + snippet.success_count * 0.1, 1.0),
                    metadata={"snippet_id": snippet.snippet_id, "tags": snippet.tags}
                ))

            # Extract error fixes
            for fix in hub._error_fixes:
                instruction = f"How do I fix this error: {fix.error_pattern}"
                response = "To fix this error:\n\n"
                response += "\n".join(f"{i+1}. {step}" for i, step in enumerate(fix.fix_steps))
                if fix.fix_code:
                    response += f"\n\nExample fix:\n```{fix.language}\n{fix.fix_code}\n```"
                if fix.explanation:
                    response += f"\n\nExplanation: {fix.explanation}"

                examples.append(TrainingExample(
                    instruction=instruction,
                    response=response,
                    source="coding_hub:error_fix",
                    category="debugging",
                    language=fix.language,
                    quality_score=min(0.5 + fix.success_count * 0.1, 1.0),
                    metadata={"fix_id": fix.fix_id, "error_type": fix.error_type}
                ))

            # Extract patterns
            for pattern in hub._patterns:
                instruction = f"Show me the {pattern.pattern_name} pattern for {pattern.framework}"
                response = f"{pattern.description}\n\n```\n{pattern.code_template}\n```"
                if pattern.use_cases:
                    response += "\n\nUse cases:\n" + "\n".join(f"- {uc}" for uc in pattern.use_cases)
                if pattern.anti_patterns:
                    response += "\n\nAvoid:\n" + "\n".join(f"- {ap}" for ap in pattern.anti_patterns)

                examples.append(TrainingExample(
                    instruction=instruction,
                    response=response,
                    source="coding_hub:pattern",
                    category=pattern.framework,
                    language="python",
                    quality_score=0.8,
                    metadata={"pattern_id": pattern.pattern_id}
                ))

            logger.info(f"Extracted {len(examples)} examples from CodingKnowledgeHub")

        except Exception as e:
            logger.warning(f"Could not extract from CodingKnowledgeHub: {e}")

        return examples


class RAGConversationExtractor:
    """Extract training examples from RAG conversation history."""

    def extract_all(self) -> List[TrainingExample]:
        """Extract all conversation examples from RAG."""
        examples = []

        try:
            from elgringo.knowledge import get_rag
            rag = get_rag()

            for doc in rag._index.get_all_documents():
                if doc.source_type != "conversation":
                    continue

                # Parse conversation format
                content = doc.content
                if "Question:" in content and "Answer:" in content:
                    parts = content.split("Answer:", 1)
                    instruction = parts[0].replace("Question:", "").strip()
                    response = parts[1].strip()

                    if len(instruction) > 20 and len(response) > 50:
                        examples.append(TrainingExample(
                            instruction=instruction,
                            response=response,
                            source="rag:conversation",
                            category=doc.metadata.get("task_type", "coding"),
                            language=doc.language or "python",
                            quality_score=0.9 if doc.metadata.get("outcome") == "success" else 0.5,
                            metadata={"doc_id": doc.doc_id}
                        ))

            logger.info(f"Extracted {len(examples)} examples from RAG conversations")

        except Exception as e:
            logger.warning(f"Could not extract from RAG: {e}")

        return examples


class TrainingDataGenerator:
    """Main training data generator."""

    def __init__(self, output_dir: str = "./data/training"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.python_extractor = PythonCodeExtractor()
        self.typescript_extractor = TypeScriptExtractor()
        self.knowledge_hub_extractor = KnowledgeHubExtractor()
        self.rag_extractor = RAGConversationExtractor()

        self.examples: List[TrainingExample] = []
        self.seen_hashes: Set[str] = set()

    def add_example(self, example: TrainingExample) -> bool:
        """Add an example with deduplication."""
        hash_id = example.get_hash()
        if hash_id in self.seen_hashes:
            return False

        self.seen_hashes.add(hash_id)
        self.examples.append(example)
        return True

    def extract_from_project(self, project_path: str, extensions: List[str] = None):
        """Extract examples from a project directory."""
        if extensions is None:
            extensions = [".py", ".ts", ".tsx"]

        project_path = Path(project_path)
        exclude_patterns = [
            "node_modules", "__pycache__", ".git", "venv", ".venv",
            "dist", "build", "test", "tests", "migrations"
        ]

        logger.info(f"Extracting from project: {project_path}")

        for ext in extensions:
            for file_path in project_path.rglob(f"*{ext}"):
                # Skip excluded paths
                if any(p in str(file_path) for p in exclude_patterns):
                    continue

                if ext == ".py":
                    examples = self.python_extractor.extract_from_file(str(file_path))
                elif ext in [".ts", ".tsx"]:
                    examples = self.typescript_extractor.extract_from_file(str(file_path))
                else:
                    continue

                for example in examples:
                    self.add_example(example)

        logger.info(f"Extracted {len(self.examples)} examples from project files")

    def extract_from_knowledge_sources(self):
        """Extract from CodingKnowledgeHub and RAG."""
        # From CodingKnowledgeHub
        for example in self.knowledge_hub_extractor.extract_all():
            self.add_example(example)

        # From RAG conversations
        for example in self.rag_extractor.extract_all():
            self.add_example(example)

    def load_existing_examples(self, file_path: str):
        """Load existing training examples from a JSONL file."""
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    data = json.loads(line)
                    # Handle different formats
                    if "messages" in data:
                        # MLX/OpenAI format
                        messages = data["messages"]
                        instruction = next((m["content"] for m in messages if m["role"] == "user"), "")
                        response = next((m["content"] for m in messages if m["role"] == "assistant"), "")
                    elif "instruction" in data:
                        # Alpaca format
                        instruction = data["instruction"]
                        response = data.get("output", data.get("response", ""))
                    else:
                        continue

                    example = TrainingExample(
                        instruction=instruction,
                        response=response,
                        source=f"loaded:{file_path}",
                        category="coding",
                    )
                    self.add_example(example)

            logger.info(f"Loaded {len(self.examples)} existing examples from {file_path}")

        except Exception as e:
            logger.warning(f"Could not load existing examples: {e}")

    def filter_by_quality(self, min_score: float = 0.5):
        """Filter examples by quality score."""
        before = len(self.examples)
        self.examples = [e for e in self.examples if e.quality_score >= min_score]
        logger.info(f"Filtered {before - len(self.examples)} low-quality examples (min_score={min_score})")

    def balance_categories(self, max_per_category: int = 200):
        """Balance examples across categories."""
        from collections import defaultdict

        by_category = defaultdict(list)
        for example in self.examples:
            by_category[example.category].append(example)

        balanced = []
        for category, examples in by_category.items():
            random.shuffle(examples)
            balanced.extend(examples[:max_per_category])
            logger.info(f"  {category}: {len(examples)} -> {min(len(examples), max_per_category)}")

        self.examples = balanced

    def generate_outputs(self, train_ratio: float = 0.9):
        """Generate output files in all formats."""
        random.shuffle(self.examples)

        split_idx = int(len(self.examples) * train_ratio)
        train_examples = self.examples[:split_idx]
        valid_examples = self.examples[split_idx:]

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Generate MLX format
        self._write_jsonl(
            train_examples,
            self.output_dir / f"train_mlx_{timestamp}.jsonl",
            lambda e: e.to_mlx_format()
        )
        self._write_jsonl(
            valid_examples,
            self.output_dir / f"valid_mlx_{timestamp}.jsonl",
            lambda e: e.to_mlx_format()
        )

        # Generate OpenAI format
        self._write_jsonl(
            train_examples,
            self.output_dir / f"train_openai_{timestamp}.jsonl",
            lambda e: e.to_openai_format()
        )

        # Generate Alpaca format
        self._write_jsonl(
            train_examples,
            self.output_dir / f"train_alpaca_{timestamp}.jsonl",
            lambda e: e.to_alpaca_format()
        )

        # Generate text format (for Gemini)
        self._write_text(
            train_examples,
            self.output_dir / f"train_text_{timestamp}.txt",
            lambda e: e.to_text_format()
        )

        # Create symlinks to latest
        for name in ["train_mlx", "valid_mlx", "train_openai", "train_alpaca"]:
            latest = self.output_dir / f"{name}_latest.jsonl"
            source = self.output_dir / f"{name}_{timestamp}.jsonl"
            latest.unlink(missing_ok=True)
            latest.symlink_to(source.name)

        # Write statistics
        stats = {
            "generated_at": timestamp,
            "total_examples": len(self.examples),
            "train_examples": len(train_examples),
            "valid_examples": len(valid_examples),
            "categories": {},
            "languages": {},
            "sources": {},
        }

        for example in self.examples:
            stats["categories"][example.category] = stats["categories"].get(example.category, 0) + 1
            stats["languages"][example.language] = stats["languages"].get(example.language, 0) + 1
            source_type = example.source.split(":")[0] if ":" in example.source else "file"
            stats["sources"][source_type] = stats["sources"].get(source_type, 0) + 1

        with open(self.output_dir / "stats.json", "w") as f:
            json.dump(stats, f, indent=2)

        logger.info("\nGenerated training data:")
        logger.info(f"  Total examples: {len(self.examples)}")
        logger.info(f"  Training: {len(train_examples)}")
        logger.info(f"  Validation: {len(valid_examples)}")
        logger.info(f"  Output directory: {self.output_dir}")

        return stats

    def _write_jsonl(self, examples: List[TrainingExample], path: Path, formatter):
        """Write examples to JSONL file."""
        with open(path, 'w') as f:
            for example in examples:
                f.write(json.dumps(formatter(example)) + "\n")
        logger.info(f"  Wrote {len(examples)} examples to {path.name}")

    def _write_text(self, examples: List[TrainingExample], path: Path, formatter):
        """Write examples to text file."""
        with open(path, 'w') as f:
            for example in examples:
                f.write(formatter(example) + "\n\n---\n\n")
        logger.info(f"  Wrote {len(examples)} examples to {path.name}")


def main():
    parser = argparse.ArgumentParser(description="Generate training data from codebase")
    parser.add_argument("--source", type=str, help="Source project directory")
    parser.add_argument("--output", type=str, default="./data/training", help="Output directory")
    parser.add_argument("--all", action="store_true", help="Extract from AITeamPlatform")
    parser.add_argument("--include-firebase", action="store_true", help="Include Firebase examples")
    parser.add_argument("--min-quality", type=float, default=0.5, help="Minimum quality score")
    parser.add_argument("--max-per-category", type=int, default=200, help="Max examples per category")

    args = parser.parse_args()

    # Determine project path
    if args.all:
        project_path = Path(__file__).parent.parent.parent
    elif args.source:
        project_path = Path(args.source)
    else:
        project_path = Path.cwd()

    output_dir = Path(args.output)
    if not output_dir.is_absolute():
        output_dir = Path(__file__).parent.parent / args.output

    logger.info("=" * 60)
    logger.info("Training Data Generator")
    logger.info("=" * 60)

    generator = TrainingDataGenerator(str(output_dir))

    # Extract from project files
    logger.info(f"\n1. Extracting from project: {project_path}")
    generator.extract_from_project(str(project_path))

    # Extract from knowledge sources
    logger.info("\n2. Extracting from knowledge sources...")
    generator.extract_from_knowledge_sources()

    # Load existing Firebase examples
    if args.include_firebase:
        firebase_path = Path(__file__).parent.parent / "data" / "firebase" / "train.jsonl"
        if firebase_path.exists():
            logger.info(f"\n3. Loading Firebase examples from {firebase_path}")
            generator.load_existing_examples(str(firebase_path))

    # Filter and balance
    logger.info(f"\n4. Filtering (min_quality={args.min_quality})...")
    generator.filter_by_quality(args.min_quality)

    logger.info(f"\n5. Balancing categories (max={args.max_per_category})...")
    generator.balance_categories(args.max_per_category)

    # Generate outputs
    logger.info("\n6. Generating output files...")
    stats = generator.generate_outputs()

    logger.info("\n" + "=" * 60)
    logger.info("Summary")
    logger.info("=" * 60)
    logger.info(f"Total examples: {stats['total_examples']}")
    logger.info("\nBy category:")
    for cat, count in sorted(stats['categories'].items(), key=lambda x: -x[1]):
        logger.info(f"  {cat}: {count}")
    logger.info("\nBy language:")
    for lang, count in sorted(stats['languages'].items(), key=lambda x: -x[1]):
        logger.info(f"  {lang}: {count}")
    logger.info(f"\nOutput: {output_dir}")


if __name__ == "__main__":
    main()
