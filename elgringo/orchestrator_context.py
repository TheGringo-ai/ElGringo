"""
Context Enrichment Manager — Extracted from AIDevTeam orchestrator
===================================================================

Handles all pre-collaboration context injection: memory patterns, neural
memory, RAG, domain knowledge, coding hub, prevention context, and
session history.
"""

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from .orchestrator import AIDevTeam

logger = logging.getLogger(__name__)

# Task types that benefit from context injection
CONTEXT_TASK_TYPES = {"coding", "debugging", "testing", "optimization", "architecture", "security"}

# Domain knowledge mapping
DOMAIN_MAPPING = {
    "coding": ["backend", "frontend"],
    "debugging": ["backend", "testing"],
    "architecture": ["architecture", "backend"],
    "security": ["security", "backend"],
    "creative": ["frontend", "architecture"],
    "ui_ux": ["frontend"],
    "testing": ["testing", "backend"],
    "optimization": ["backend", "devops"],
    "documentation": ["backend", "frontend"],
}


class ContextEnrichmentManager:
    """
    Enriches prompts with relevant context from memory, knowledge, and RAG.

    Extracted from AIDevTeam.collaborate() to reduce the 900-line method
    to a single call: `enriched = await context_mgr.enrich(prompt, ...)`.
    """

    def __init__(self, orchestrator: "AIDevTeam"):
        self._o = orchestrator

    async def enrich(
        self,
        prompt: str,
        context: str,
        task_type: str,
        complexity: str,
        task_id: str,
        session_id: Optional[str] = None,
    ) -> Tuple[str, str, List[str], Dict[str, Any]]:
        """
        Enrich prompt and context with all available intelligence.

        Returns:
            (enhanced_prompt, context, collaboration_log_entries, intel_dict)
        """
        enhanced_prompt = prompt
        log: List[str] = []
        intel: Dict[str, Any] = {
            "memory": {"patterns_injected": 0, "patterns": [], "prevention_applied": False},
        }

        needs_context = task_type in CONTEXT_TASK_TYPES and complexity != "low"
        relevant_domains = DOMAIN_MAPPING.get(task_type, [task_type])

        # Session history injection
        context = self._inject_session(context, session_id, log)

        # Prevention context from past mistakes
        if needs_context:
            enhanced_prompt = await self._inject_prevention(enhanced_prompt, task_type, log, intel)

        # Solution patterns from memory
        if needs_context:
            enhanced_prompt = await self._inject_solution_patterns(
                enhanced_prompt, prompt, task_id, log, intel
            )

        # Neural memory contextual recall
        enhanced_prompt = await self._inject_neural_memory(enhanced_prompt, prompt, context, log, intel)

        # Live codebase RAG auto-index
        if needs_context:
            self._auto_index_project(log)

        # Domain knowledge + coding hub + RAG
        if needs_context:
            enhanced_prompt = self._inject_domain_knowledge(
                enhanced_prompt, prompt, relevant_domains, task_type, complexity, log
            )
        else:
            log.append(f"Skipped context injection (task_type={task_type}, complexity={complexity})")

        return enhanced_prompt, context, log, intel

    def _inject_session(self, context: str, session_id: Optional[str], log: List[str]) -> str:
        """Inject conversation history from session."""
        if not session_id:
            return context

        from .core.sessions import get_session_manager
        sm = get_session_manager()
        session = sm.get_or_create(session_id, project=self._o.project_name)
        session.add_user_turn("")  # Record user turn
        session_context = session.get_context_block()
        if session_context:
            context = f"{session_context}\n{context}" if context else session_context
            log.append(f"Session {session_id}: injected {session.turn_count} turns of history")
        return context

    async def _inject_prevention(
        self, prompt: str, task_type: str, log: List[str], intel: Dict
    ) -> str:
        """Inject prevention context from past mistakes."""
        if not self._o._prevention:
            return prompt
        try:
            prevention_context = await self._o._prevention.get_prevention_context(
                task_type, self._o.project_name
            )
            if prevention_context:
                prompt = f"{prevention_context}\n\n{prompt}"
                log.append("Applied prevention context from past mistakes")
                intel["memory"]["prevention_applied"] = True
                intel["memory"]["prevention_summary"] = prevention_context[:200]
        except Exception as e:
            logger.debug(f"Prevention context skipped: {e}")
        return prompt

    async def _inject_solution_patterns(
        self, prompt: str, original_prompt: str, task_id: str,
        log: List[str], intel: Dict
    ) -> str:
        """Inject relevant solution patterns from memory."""
        if not self._o._memory_system:
            return prompt
        try:
            solutions = await self._o._memory_system.find_solution_patterns(original_prompt[:200], limit=6)
            project_solutions = await self._o._memory_system.find_solution_patterns(
                self._o.project_name, limit=6
            )
            # Merge and deduplicate
            seen_ids = set()
            all_solutions = []
            for s in solutions + project_solutions:
                if s.solution_id not in seen_ids:
                    seen_ids.add(s.solution_id)
                    all_solutions.append(s)

            curated = [s for s in all_solutions if s.best_practices]
            auto = [s for s in all_solutions if not s.best_practices]
            selected = curated[:3] + auto[:max(0, 3 - len(curated))]

            if selected:
                solution_lines = ["MANDATORY PROJECT CONVENTIONS — You MUST follow these rules:"]
                for sol in selected:
                    solution_lines.append(f"\n## {sol.problem_pattern}")
                    for step in sol.solution_steps:
                        if len(step) > 200:
                            continue
                        solution_lines.append(f"  - {step}")
                    if sol.best_practices:
                        solution_lines.append("  REQUIREMENTS (do not ignore):")
                        for bp in sol.best_practices:
                            solution_lines.append(f"    * {bp}")

                solution_context = "\n".join(solution_lines)
                if len(solution_context) > 3000:
                    solution_context = solution_context[:3000] + "\n..."
                prompt = f"{solution_context}\n\n{prompt}"
                log.append(f"Injected {len(selected)} solution patterns from memory ({len(curated)} curated)")

                self._o._memory_system.track_injection(task_id, [s.solution_id for s in selected])

                intel["memory"]["patterns_injected"] = len(selected)
                intel["memory"]["curated_count"] = len(curated)
                for sol in selected:
                    intel["memory"]["patterns"].append({
                        "name": sol.problem_pattern[:80],
                        "quality": round(getattr(sol, 'quality_score', 0.5), 2),
                        "times_used": getattr(sol, 'access_count', 0),
                        "has_best_practices": bool(sol.best_practices),
                    })
        except Exception as e:
            logger.debug(f"Memory solution search skipped: {e}")
        return prompt

    async def _inject_neural_memory(
        self, prompt: str, original_prompt: str, context: str,
        log: List[str], intel: Dict
    ) -> str:
        """Inject neural memory contextual recall."""
        if not self._o._neural_memory:
            return prompt
        try:
            recalls = self._o._neural_memory.contextual_recall(
                task_description=original_prompt,
                error_message=context[:500] if "error" in context.lower() else None,
                limit=3,
            )
            if recalls:
                neural_context = "\n".join(
                    f"- [{r.node.node_type}] {r.node.content[:200]} (confidence: {r.node.confidence:.0%})"
                    for r in recalls
                )
                prompt = f"RELEVANT PAST EXPERIENCE:\n{neural_context}\n\n{prompt}"
                log.append(f"Neural memory: injected {len(recalls)} relevant memories")
                intel["memory"]["neural_recalls"] = len(recalls)
        except Exception as e:
            logger.debug(f"Neural recall skipped: {e}")
        return prompt

    def _auto_index_project(self, log: List[str]):
        """Auto-index project for RAG if stale."""
        if not self._o._rag or self._o.project_name == "default":
            return
        try:
            from .workflows.project_context import ProjectContextManager
            pctx = ProjectContextManager()
            profile = pctx.get_profile(self._o.project_name)
            if profile and profile.project_path:
                indexed = self._o._rag.index_project_if_stale(
                    project_name=self._o.project_name,
                    project_path=profile.project_path,
                )
                if indexed:
                    log.append(f"Auto-indexed project '{self._o.project_name}' for RAG")
        except Exception as e:
            logger.debug(f"Auto-index skipped: {e}")

    def _inject_domain_knowledge(
        self, prompt: str, original_prompt: str, relevant_domains: List[str],
        task_type: str, complexity: str, log: List[str],
    ) -> str:
        """Inject domain knowledge, coding hub, and RAG context."""
        from .knowledge import get_domain_context

        # Built-in domain knowledge
        domain_context = get_domain_context(relevant_domains)

        # Custom teaching knowledge
        teaching_context = self._o._teaching_system.generate_teaching_context(
            domains=relevant_domains, topics=[task_type]
        )

        if domain_context or teaching_context:
            knowledge_context = "\n".join(filter(None, [domain_context, teaching_context]))
            if len(knowledge_context) > 2000:
                knowledge_context = knowledge_context[:2000] + "\n..."
            prompt = f"DOMAIN EXPERTISE:\n{knowledge_context}\n\nTASK:\n{prompt}"
            log.append(f"Applied domain knowledge: {', '.join(relevant_domains)}")

        # Coding knowledge hub (code-related tasks only)
        if task_type in ["coding", "debugging"]:
            coding_context = self._o._coding_hub.generate_coding_context(
                task_description=original_prompt,
                language=None,
                framework=None,
                max_items=2,
            )
            if coding_context and len(coding_context) <= 1500:
                prompt = f"{coding_context}\n\n{prompt}"
                log.append("Applied coding knowledge hub context")

        # RAG context (medium+ complexity only)
        if complexity in ("medium", "high"):
            try:
                rag_context = self._o._rag.get_context_for_task(
                    task_description=original_prompt,
                    max_results=3,
                    max_tokens=800,
                )
                if rag_context.results:
                    prompt = f"{rag_context.context_text}\n\n{prompt}"
                    log.append(f"Applied RAG context ({len(rag_context.results)} sources)")
            except Exception as e:
                logger.debug(f"RAG context retrieval skipped: {e}")

        return prompt
