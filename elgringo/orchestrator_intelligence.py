"""
Post-Collaboration Intelligence — Extracted from AIDevTeam orchestrator
========================================================================

Handles all post-response processing: memory storage, learning, cost
tracking, quality scoring, transparency, failure detection, ROI, watchdog,
caching, and session learning.
"""

import asyncio
import logging
import re
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from .agents import AgentResponse, AIAgent

if TYPE_CHECKING:
    from .orchestrator import AIDevTeam, CollaborationResult

logger = logging.getLogger(__name__)


class PostCollaborationIntelligence:
    """
    Processes collaboration results: stores memories, tracks costs,
    scores quality, detects failures, updates ROI, and caches responses.

    Extracted from AIDevTeam.collaborate() — the ~400 lines after synthesis.
    """

    def __init__(self, orchestrator: "AIDevTeam"):
        self._o = orchestrator

    async def process(
        self,
        result: "CollaborationResult",
        prompt: str,
        context: str,
        final_answer: str,
        agent_responses: List[AgentResponse],
        active_agents: List[AIAgent],
        task_type: str,
        complexity: str,
        mode: str,
        relevant_domains: List[str],
        intel: Dict[str, Any],
        collaboration_log: List[str],
        session_id: Optional[str] = None,
    ):
        """Run all post-collaboration intelligence. Mutates intel and collaboration_log."""
        successful_responses = [r for r in agent_responses if r.success]
        task_id = result.task_id
        avg_confidence = result.confidence_score
        total_time = result.total_time

        # Build agent perspectives
        self._build_agent_perspectives(agent_responses, intel)

        # Detect agreement/disagreement
        self._detect_consensus(successful_responses, avg_confidence, intel)

        # Save to session
        if session_id:
            self._save_session(session_id, final_answer, active_agents, task_type, avg_confidence, task_id, intel)

        # Memory storage and learning
        await self._store_and_learn(
            result, prompt, context, final_answer, agent_responses,
            active_agents, task_type, mode, avg_confidence, task_id,
            relevant_domains, total_time, intel, collaboration_log,
        )

        # Code validation
        self._validate_code(final_answer, task_type, prompt, relevant_domains, result, collaboration_log)

        # Performance tracking
        self._track_performance(successful_responses, task_type, task_id, collaboration_log)

        # Cost tracking
        self._track_costs(successful_responses, task_type, task_id, intel, collaboration_log)

        # Cost arbitrage
        self._record_arbitrage(successful_responses, task_type, intel, collaboration_log)

        # Quality watchdog
        self._record_watchdog(successful_responses, task_type, intel, collaboration_log)

        # Smart cache
        self._cache_response(prompt, final_answer, successful_responses, mode, task_type, avg_confidence, intel)

        # Session learning
        self._record_session_learning(successful_responses, task_type, task_id, prompt, collaboration_log)

        # Intelligence v2: quality, transparency, failure detection, ROI
        self._score_quality(agent_responses, prompt, final_answer, task_type, successful_responses, intel, collaboration_log)
        self._analyze_transparency(agent_responses, prompt, final_answer, task_type, task_id, intel)
        self._detect_failures(final_answer, task_id, task_type, active_agents, intel, collaboration_log, prompt=prompt)
        self._record_roi(task_id, task_type, complexity, active_agents, mode, total_time, avg_confidence, result, intel)

    def _build_agent_perspectives(self, agent_responses: List[AgentResponse], intel: Dict):
        """Build agent perspective entries for intelligence report."""
        intel.setdefault("agents", [])
        for resp in agent_responses:
            perspective = {
                "name": resp.agent_name,
                "model": resp.metadata.get("model", resp.model_type.value) if resp.metadata else resp.model_type.value,
                "success": resp.success,
                "confidence": round(resp.confidence, 2),
                "response_time": round(resp.response_time, 2),
                "tokens": {"input": resp.input_tokens, "output": resp.output_tokens},
                "summary": (resp.content or "")[:200].replace("\n", " ").strip(),
            }
            intel["agents"].append(perspective)

    def _detect_consensus(
        self, successful_responses: List[AgentResponse], avg_confidence: float, intel: Dict
    ):
        """Detect agreement/disagreement among agents."""
        intel.setdefault("consensus", {})
        if len(successful_responses) >= 2:
            confidences = [r.confidence for r in successful_responses]
            spread = max(confidences) - min(confidences)
            avg_len = sum(len(r.content or "") for r in successful_responses) / len(successful_responses)
            len_spread = max(abs(len(r.content or "") - avg_len) for r in successful_responses)

            if spread < 0.15 and len_spread < avg_len * 0.5:
                intel["consensus"]["level"] = "high"
                intel["consensus"]["description"] = "Agents broadly agree"
            elif spread < 0.3:
                intel["consensus"]["level"] = "moderate"
                intel["consensus"]["description"] = "Some variation in confidence — agents may have different approaches"
            else:
                intel["consensus"]["level"] = "low"
                intel["consensus"]["description"] = "Significant disagreement — agents have divergent perspectives"
                for r in successful_responses:
                    if abs(r.confidence - avg_confidence) > 0.2:
                        intel["consensus"].setdefault("divergent_agents", []).append(r.agent_name)
        elif len(successful_responses) == 1:
            intel["consensus"]["level"] = "single-agent"
            intel["consensus"]["description"] = "Only one agent responded"

    def _save_session(
        self, session_id: str, final_answer: str, active_agents: List[AIAgent],
        task_type: str, avg_confidence: float, task_id: str, intel: Dict
    ):
        """Save team response to session."""
        from .core.sessions import get_session_manager
        sm = get_session_manager()
        session = sm.get_or_create(session_id, project=self._o.project_name)
        session.add_team_turn(
            content=final_answer[:2000],
            agents=[a.name for a in active_agents],
            task_type=task_type,
            confidence=avg_confidence,
            task_id=task_id,
        )
        sm.save(session)
        intel["session"] = {
            "id": session_id,
            "turns": session.turn_count,
            "has_summary": bool(session.summary),
        }

    async def _store_and_learn(
        self, result, prompt, context, final_answer, agent_responses,
        active_agents, task_type, mode, avg_confidence, task_id,
        relevant_domains, total_time, intel, collaboration_log,
    ):
        """Store in memory and learn from outcome."""
        if not (self._o.enable_memory and self._o._memory_system):
            return

        await self._o._memory_system.capture_interaction(result, self._o.project_name)

        # Learn from successful outcomes
        if self._o.enable_learning and self._o._learning_engine and result.success:
            extractor = None
            for pref in ["gemini-coder", "ollama-local", "chatgpt-coder"]:
                if pref in self._o.agents:
                    extractor = self._o.agents[pref]
                    break

            learn_result = await self._o._learning_engine.learn_from_success(
                result, prompt, self._o.project_name,
                extractor_agent=extractor,
            )
            if learn_result and isinstance(learn_result, dict):
                intel["learning"]["patterns_extracted"] = len(learn_result.get("solution_steps", []))
                intel["learning"]["tags"] = learn_result.get("tags", [])
            elif learn_result:
                intel["learning"]["stored"] = True

            mem_stats = self._o._memory_system.get_statistics() if self._o._memory_system else {}
            intel["learning"]["total_patterns"] = mem_stats.get("total_solutions", 0)

            # Cross-project nexus
            if learn_result and isinstance(learn_result, dict):
                try:
                    from .intelligence.cross_project import get_nexus
                    nexus = get_nexus()
                    nexus.index_solution(
                        project=self._o.project_name,
                        problem=prompt[:200],
                        solution=final_answer[:500],
                        tags=learn_result.get("tags", []),
                        confidence=avg_confidence,
                    )
                except Exception as e:
                    logger.debug(f"Cross-project indexing skipped: {e}")

        # Neural memory — store both successes AND failures, create relationships
        if self._o._neural_memory:
            try:
                nm = self._o._neural_memory
                node_type = "solution" if result.success else "mistake"
                content_prefix = "Task" if result.success else "Failed Task"
                node_id = nm.store(
                    content=f"{content_prefix}: {prompt[:300]}\nAnswer: {final_answer[:500]}",
                    node_type=node_type,
                    metadata={
                        "task_type": task_type,
                        "mode": mode,
                        "confidence": avg_confidence,
                        "agents": [a.name for a in active_agents],
                    },
                    tags=[task_type, mode],
                    confidence=avg_confidence,
                )
                intel["memory"]["neural_stored"] = node_id

                # Record outcome for confidence learning
                nm.record_outcome(node_id, success=result.success)

                # Create edges to related nodes (find similar past tasks)
                try:
                    similar = nm.search(prompt[:200], limit=3)
                    for recall in similar:
                        match_id = recall.node.node_id if hasattr(recall, 'node') else ""
                        if match_id and match_id != node_id:
                            relevance = recall.relevance_score if hasattr(recall, 'relevance_score') else 0.5
                            if relevance > 0.5:
                                rel = "similar_to"
                                match_type = recall.node.node_type if hasattr(recall, 'node') else ""
                                if node_type == "solution" and match_type == "mistake":
                                    rel = "solves"
                                elif node_type == "mistake" and match_type == "solution":
                                    rel = "related_to"
                                nm.add_edge(node_id, match_id, rel, weight=relevance)
                except Exception:
                    pass  # Edge creation is best-effort
            except Exception as e:
                logger.debug(f"Neural store skipped: {e}")

        # Auto-learner
        if self._o.enable_auto_learning and self._o._auto_learner:
            await self._o._auto_learner.capture_interaction(
                user_prompt=prompt,
                ai_responses=[
                    {
                        "agent_name": r.agent_name,
                        "content": r.content,
                        "success": r.success,
                        "confidence": r.confidence,
                        "model_type": r.model_type.value,
                    }
                    for r in agent_responses
                ],
                outcome="success" if result.success else "failure",
                task_type=task_type,
                domains=relevant_domains,
                models_used=[r.model_type.value for r in agent_responses],
                duration_seconds=total_time,
                metadata={
                    "mode": mode,
                    "complexity": result.metadata.get("complexity", ""),
                    "project": self._o.project_name,
                },
            )

        # Auto-learn code to coding hub
        if result.success and task_type in ["coding", "debugging"]:
            code_blocks = re.findall(r'```(\w+)?\n(.*?)```', final_answer, re.DOTALL)
            for lang, code in code_blocks:
                code_stripped = code.strip()
                if (code_stripped
                        and len(code_stripped) > 100
                        and lang
                        and any(kw in code_stripped for kw in ['def ', 'class ', 'import ', 'function ', 'const ', 'return ', 'async '])):
                    self._o._coding_hub.learn_from_successful_code(
                        code=code_stripped,
                        language=lang,
                        task_description=prompt[:100],
                    )
                    collaboration_log.append(f"Learned code snippet to hub ({lang})")

    def _validate_code(
        self, final_answer: str, task_type: str, prompt: str,
        relevant_domains: List[str], result, collaboration_log: List[str],
    ):
        """Validate generated code and add warnings."""
        if task_type not in ["coding", "debugging", "testing"]:
            return

        validation_results = self._o._code_validator.validate_response(final_answer)
        validation_warnings = []
        for val_result in validation_results:
            if val_result.warnings:
                validation_warnings.extend([str(w) for w in val_result.warnings[:3]])
            if not val_result.valid:
                validation_warnings.extend([str(e) for e in val_result.errors[:3]])

        if validation_warnings:
            result.metadata["validation_warnings"] = validation_warnings[:5]
            collaboration_log.append(f"Code validation: {len(validation_warnings)} issue(s) found")

            try:
                self._o._rag.index_conversation(
                    prompt=prompt,
                    response=final_answer,
                    outcome="success" if result.success else "failure",
                    task_type=task_type,
                    tags=relevant_domains,
                )
            except Exception as e:
                logger.debug(f"RAG conversation indexing skipped: {e}")

    def _track_performance(
        self, successful_responses: List[AgentResponse], task_type: str,
        task_id: str, collaboration_log: List[str],
    ):
        """Record performance outcomes for each agent."""
        if not self._o._performance_tracker:
            return
        for response in successful_responses:
            self._o._performance_tracker.record_outcome(
                model_name=response.agent_name,
                task_type=task_type,
                success=response.success,
                confidence=response.confidence,
                response_time=response.response_time,
                domain=self._o.project_name,
                task_id=task_id,
            )
        collaboration_log.append(f"Recorded performance for {len(successful_responses)} agents")

    def _track_costs(
        self, successful_responses: List[AgentResponse], task_type: str,
        task_id: str, intel: Dict, collaboration_log: List[str],
    ):
        """Record costs for each agent response."""
        if not self._o._cost_tracker:
            return
        total_cost = 0.0
        for response in successful_responses:
            if response.input_tokens or response.output_tokens:
                model_name = response.metadata.get("model", "") or response.agent_name
                estimate = self._o._cost_tracker.record_usage(
                    model=model_name,
                    agent_name=response.agent_name,
                    task_type=task_type,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    task_id=task_id,
                )
                total_cost += estimate.estimated_cost
                intel["cost"]["breakdown"].append({
                    "agent": response.agent_name,
                    "model": model_name,
                    "cost": round(estimate.estimated_cost, 6),
                })
        intel["cost"]["total"] = round(total_cost, 6)
        if total_cost > 0:
            collaboration_log.append(f"Cost: ${total_cost:.4f} for {len(successful_responses)} agents")

    def _record_arbitrage(
        self, successful_responses: List[AgentResponse], task_type: str,
        intel: Dict, collaboration_log: List[str],
    ):
        """Record to cost arbitrage engine."""
        try:
            from .intelligence.cost_arbitrage import get_optimizer
            optimizer = get_optimizer()
            for response in successful_responses:
                tokens = (response.input_tokens or 0) + (response.output_tokens or 0)
                cost_entry = next(
                    (c for c in intel["cost"]["breakdown"] if c["agent"] == response.agent_name),
                    None,
                )
                cost = cost_entry["cost"] if cost_entry else 0.0
                optimizer.record_usage(
                    provider=response.agent_name,
                    task_type=task_type,
                    cost=cost,
                    quality_score=response.confidence * 10,
                    tokens=tokens,
                )
            collaboration_log.append(f"Cost arbitrage: recorded {len(successful_responses)} usage entries")
        except Exception as e:
            logger.debug(f"Cost arbitrage recording skipped: {e}")

    def _record_watchdog(
        self, successful_responses: List[AgentResponse], task_type: str,
        intel: Dict, collaboration_log: List[str],
    ):
        """Record to quality watchdog."""
        try:
            from .intelligence.quality_watchdog import get_watchdog
            watchdog = get_watchdog()
            for response in successful_responses:
                watchdog.record(
                    agent_name=response.agent_name,
                    quality_score=response.confidence * 10,
                    response_time=response.response_time,
                    success=response.success,
                    task_type=task_type,
                    tokens=(response.input_tokens or 0) + (response.output_tokens or 0),
                )
            demoted = watchdog.get_demoted_agents()
            if demoted:
                collaboration_log.append(f"Watchdog: agents demoted: {demoted}")
                intel["watchdog"] = {"demoted": demoted}
        except Exception as e:
            logger.debug(f"Quality watchdog recording skipped: {e}")

    def _cache_response(
        self, prompt: str, final_answer: str, successful_responses: List[AgentResponse],
        mode: str, task_type: str, avg_confidence: float, intel: Dict,
    ):
        """Cache the response for future similar prompts."""
        try:
            from .intelligence.smart_cache import get_smart_cache
            cache = get_smart_cache()
            cache.put(
                prompt=prompt,
                response=final_answer,
                cost=intel["cost"]["total"],
                tokens=sum((r.input_tokens or 0) + (r.output_tokens or 0) for r in successful_responses),
                agent=successful_responses[0].agent_name if successful_responses else "",
                mode=mode,
                task_type=task_type,
                confidence=avg_confidence,
            )
        except Exception as e:
            logger.debug(f"Smart cache store skipped: {e}")

    def _record_session_learning(
        self, successful_responses: List[AgentResponse], task_type: str,
        task_id: str, prompt: str, collaboration_log: List[str],
    ):
        """Record session learning outcomes."""
        if not (self._o.enable_session_learning and self._o._session_learner):
            return
        from .autonomous import TaskOutcome
        for response in successful_responses:
            outcome = TaskOutcome(
                task_id=task_id,
                task_type=task_type,
                agent_id=response.agent_name,
                prompt=prompt,
                response=response.content[:1000] if response.content else "",
                success=response.success,
                confidence=response.confidence,
                execution_time=response.response_time,
            )
            self._o._session_learner.record_outcome(outcome)
        self._o._session_learner.save()
        collaboration_log.append("Session learning updated and saved")

    def _score_quality(
        self, agent_responses, prompt, final_answer, task_type,
        successful_responses, intel, collaboration_log,
    ):
        """Run quality scoring."""
        try:
            expertise_weights = {
                r.agent_name: self._o._weighted_consensus.get_expertise_weight(r.agent_name, task_type)
                for r in successful_responses
            }
            quality_report = self._o._quality_scorer.score(
                responses=agent_responses,
                prompt=prompt,
                final_answer=final_answer,
                task_type=task_type,
                expertise_weights=expertise_weights,
            )
            intel["quality"] = quality_report.to_dict()
            collaboration_log.append(f"Quality: {quality_report.grade} ({quality_report.overall_score:.0%})")
        except Exception as e:
            logger.debug(f"Quality scoring skipped: {e}")

    def _analyze_transparency(
        self, agent_responses, prompt, final_answer, task_type, task_id, intel,
    ):
        """Run reasoning transparency analysis."""
        try:
            transparency_report = self._o._reasoning_transparency.analyze(
                responses=agent_responses,
                prompt=prompt,
                final_answer=final_answer,
                task_type=task_type,
                task_id=task_id,
            )
            intel["transparency"] = transparency_report.to_dict()
        except Exception as e:
            logger.debug(f"Transparency analysis skipped: {e}")

    def _detect_failures(
        self, final_answer, task_id, task_type, active_agents, intel, collaboration_log,
        prompt: str = "",
    ):
        """Run auto-failure detection."""
        try:
            detection = self._o._failure_detector.check(
                content=final_answer,
                task_id=task_id,
                task_type=task_type,
            )
            if not detection.passed:
                intel["failure_detection"] = detection.to_dict()
                collaboration_log.append(
                    f"Auto-detected {len(detection.failures)} issue(s) in response"
                )
                critical = [f for f in detection.failures if f.severity == "critical"]
                if critical:
                    asyncio.ensure_future(
                        self._o._feedback_loop.auto_detect_failure(
                            task_id=task_id,
                            error="; ".join(f.description for f in critical[:3]),
                            agents=[a.name for a in active_agents],
                            task_type=task_type,
                            prompt=prompt,
                            project=self._o.project_name,
                        )
                    )
            else:
                intel["failure_detection"] = {"passed": True, "code_blocks_checked": detection.code_blocks_checked}
        except Exception as e:
            logger.debug(f"Failure detection skipped: {e}")

    def _record_roi(
        self, task_id, task_type, complexity, active_agents, mode,
        total_time, avg_confidence, result, intel,
    ):
        """Record ROI data."""
        try:
            api_cost = intel.get("cost", {}).get("total", 0.0)
            self._o._roi_dashboard.record_task(
                task_id=task_id,
                task_type=task_type,
                complexity=complexity,
                agents_used=[a.name for a in active_agents],
                mode=mode,
                duration_seconds=total_time,
                api_cost=api_cost,
                success=result.success,
                confidence=avg_confidence,
            )
        except Exception as e:
            logger.debug(f"ROI recording skipped: {e}")
