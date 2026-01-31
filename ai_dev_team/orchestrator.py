"""
AI Development Team Orchestrator
=================================

Main orchestration engine that coordinates multiple AI models for collaborative
software development tasks. Integrates memory, learning, and collaboration systems.
"""

import asyncio
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .agents import (
    AIAgent,
    AgentConfig,
    AgentResponse,
    ChatGPTAgent,
    ClaudeAgent,
    GeminiAgent,
    GrokAgent,
    OllamaAgent,
    ModelType,
    # Llama Cloud agents
    LlamaCloudAgent,
    create_llama_70b,
    create_llama_fast,
)
from .agents.ollama import create_local_agent, create_local_coder, LOCAL_MODELS
from .routing import TaskRouter, CostOptimizer, get_performance_tracker, RoutingDecision, get_decision_logger
from .preferences import get_preference_store, DevConstraints
from .monitoring import get_health_monitor
from .failover import get_failover_manager, get_circuit_breaker
from .memory import MemorySystem, LearningEngine, MistakePrevention
from .collaboration import WeightedConsensus
from .knowledge import TeachingSystem, get_domain_context, AutoLearner, get_coding_hub, get_rag
from .tools import FileSystemTools, BrowserTools, ShellTools, PermissionManager
from .security import validate_tool_call, get_security_validator, ThreatLevel
from .validation import get_validator
from .framework import (
    ReActAgent,
    ReActTrace,
    TaskPlanner,
    ExecutionPlan,
    ChainOfThought,
    ReasoningChain,
    ContextManager,
    get_tool_registry,
)

logger = logging.getLogger(__name__)


@dataclass
class CollaborationResult:
    """Result of a collaborative AI team task"""
    task_id: str
    success: bool
    final_answer: str
    agent_responses: List[AgentResponse]
    collaboration_log: List[str]
    total_time: float
    confidence_score: float
    participating_agents: List[str]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


class AIDevTeam:
    """
    AI Development Team - Multi-Model Orchestration Platform

    Coordinates Claude, ChatGPT, Gemini, and Grok for collaborative
    software development. Supports multiple collaboration modes,
    intelligent task routing, and persistent learning.

    Usage:
        team = AIDevTeam()
        result = await team.collaborate("Build a user authentication API")
        print(result.final_answer)
    """

    def __init__(
        self,
        project_name: str = "default",
        auto_setup: bool = True,
        enable_memory: bool = True,
        enable_learning: bool = True,
        enable_auto_learning: bool = True,
    ):
        self.project_name = project_name
        self.agents: Dict[str, AIAgent] = {}
        self.enable_memory = enable_memory
        self.enable_learning = enable_learning
        self.enable_auto_learning = enable_auto_learning

        # Initialize task router, cost optimizer, and performance tracker
        self._task_router = TaskRouter()
        self._cost_optimizer = CostOptimizer()
        self._weighted_consensus = WeightedConsensus()
        self._performance_tracker = get_performance_tracker()

        # v2: Preference store and decision logger
        self._preference_store = get_preference_store()
        self._decision_logger = get_decision_logger()
        self._constraints: DevConstraints = self._preference_store.get_constraints(project_name)

        # Initialize health monitoring and failover
        self._health_monitor = get_health_monitor()
        self._failover_manager = get_failover_manager()
        self._circuit_breaker = get_circuit_breaker()

        # Initialize memory and learning systems
        if enable_memory:
            self._memory_system = MemorySystem()
            self._learning_engine = LearningEngine(self._memory_system)
            self._prevention = MistakePrevention(self._memory_system)
        else:
            self._memory_system = None
            self._learning_engine = None
            self._prevention = None

        # Initialize knowledge/teaching system
        self._teaching_system = TeachingSystem()

        # Initialize coding knowledge hub
        self._coding_hub = get_coding_hub()

        # Initialize Universal RAG system
        self._rag = get_rag()
        # Index coding hub into RAG on startup
        try:
            self._rag.index_coding_hub(self._coding_hub)
        except Exception as e:
            logger.debug(f"RAG indexing deferred: {e}")

        # Initialize code validator
        self._code_validator = get_validator()

        # Initialize auto-learning system (always learns from interactions)
        if enable_auto_learning:
            self._auto_learner = AutoLearner(teaching_system=self._teaching_system)
        else:
            self._auto_learner = None

        # Initialize tools with permission manager
        self._permission_manager = PermissionManager()
        self._tools = {
            "filesystem": FileSystemTools(self._permission_manager),
            "browser": BrowserTools(self._permission_manager),
            "shell": ShellTools(self._permission_manager),
        }

        self._collaboration_engine = None

        if auto_setup:
            self.setup_agents()

    def setup_agents(self):
        """Setup default AI team based on available API keys"""
        # Claude - Lead Analyst
        if os.getenv("ANTHROPIC_API_KEY"):
            self.register_agent(ClaudeAgent())
            logger.info("Registered Claude agent (Lead Analyst)")

        # ChatGPT - Senior Developer
        if os.getenv("OPENAI_API_KEY"):
            self.register_agent(ChatGPTAgent())
            logger.info("Registered ChatGPT agent (Senior Developer)")

        # Gemini - Creative Director
        if os.getenv("GEMINI_API_KEY"):
            self.register_agent(GeminiAgent())
            logger.info("Registered Gemini agent (Creative Director)")

        # Grok - Strategic Thinker + Speed Coder
        if os.getenv("XAI_API_KEY"):
            self.register_agent(GrokAgent(fast_mode=False))  # Reasoner
            self.register_agent(GrokAgent(fast_mode=True))   # Fast coder
            logger.info("Registered Grok agents (Reasoner + Coder)")

        # Llama Cloud - via Groq, Together, or Fireworks APIs
        self._setup_llama_cloud_agents()

        # Local models via Ollama (free, private, offline)
        self._setup_local_agents()

        if not self.agents:
            logger.warning(
                "No AI agents configured. Set API keys: "
                "ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY, XAI_API_KEY"
            )

    def _setup_llama_cloud_agents(self):
        """Setup Llama Cloud agents via Groq, Together, or Fireworks"""
        # Priority order: Groq (fastest) -> Together (most models) -> Fireworks
        llama_registered = False

        # Groq - Ultra-fast Llama inference
        if os.getenv("GROQ_API_KEY"):
            self.register_agent(create_llama_70b(provider="groq"))
            logger.info("Registered Llama 3.3 70B agent (via Groq - ultra-fast)")
            llama_registered = True

        # Together AI - Most model variety including 405B
        if os.getenv("TOGETHER_API_KEY"):
            if not llama_registered:
                self.register_agent(create_llama_70b(provider="together"))
                logger.info("Registered Llama 3.3 70B agent (via Together AI)")
            # Also register 8B for fast tasks
            self.register_agent(create_llama_fast(provider="together"))
            logger.info("Registered Llama 3.1 8B agent (via Together AI - fast)")

        # Fireworks - Good for function calling
        if os.getenv("FIREWORKS_API_KEY") and not llama_registered:
            self.register_agent(create_llama_70b(provider="fireworks"))
            logger.info("Registered Llama 3.3 70B agent (via Fireworks)")

    def _setup_local_agents(self):
        """Setup local Ollama agents if available"""
        import asyncio
        import concurrent.futures

        async def check_ollama():
            try:
                agent = OllamaAgent()
                if await agent.is_available():
                    models = await agent.list_models()
                    return models
            except Exception:
                pass
            return []

        def run_in_new_loop():
            """Run async code in a new event loop (for thread pool)"""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(check_ollama())
            finally:
                loop.close()

        # Check if Ollama is running using various strategies
        models = []
        try:
            # Try to get existing loop
            try:
                loop = asyncio.get_running_loop()
                # Loop is running, use thread pool to avoid blocking
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_new_loop)
                    models = future.result(timeout=5)
            except RuntimeError:
                # No running loop, safe to create one
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_closed():
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    models = loop.run_until_complete(check_ollama())
                except RuntimeError:
                    # Fall back to asyncio.run()
                    models = asyncio.run(check_ollama())
        except Exception as e:
            logger.debug(f"Could not check Ollama availability: {e}")
            return

        if models:
            # Register Llama 3.2 as general purpose
            if any("llama3" in m.lower() for m in models):
                self.register_agent(create_local_agent("llama3"))
                logger.info("Registered local agent: Llama 3.2 (General)")

            # Register Qwen Coder (prefer custom fine-tuned version)
            if any("qwen-coder-custom" in m.lower() for m in models):
                self.register_agent(create_local_coder())
                logger.info("Registered local agent: Qwen Coder Custom (Fine-tuned)")
            elif any("qwen" in m.lower() and "coder" in m.lower() for m in models):
                self.register_agent(create_local_agent("qwen-coder-7b"))
                logger.info("Registered local agent: Qwen Coder (Code Specialist)")

            # Register Llama Coder if available
            if any("llama-coder-custom" in m.lower() for m in models):
                self.register_agent(create_local_agent("llama-coder-custom"))
                logger.info("Registered local agent: Llama Coder Custom (Fine-tuned)")

    def register_agent(self, agent: AIAgent):
        """Register an AI agent with the team"""
        self.agents[agent.name] = agent

    def get_agent(self, name: str) -> Optional[AIAgent]:
        """Get agent by name"""
        return self.agents.get(name)

    @property
    def available_agents(self) -> List[str]:
        """List of available agent names"""
        return list(self.agents.keys())

    @property
    def constraints(self) -> DevConstraints:
        """Current developer constraints"""
        return self._constraints

    def update_constraints(self, **kwargs):
        """
        Update developer constraints for this project.

        Examples:
            team.update_constraints(prefer_local=True)
            team.update_constraints(blocked_providers=["openai"])
            team.update_constraints(verbose_routing=True)
        """
        for key, value in kwargs.items():
            if hasattr(self._constraints, key):
                setattr(self._constraints, key, value)
            else:
                logger.warning(f"Unknown constraint: {key}")
        self._preference_store.save_constraints(self._constraints, self.project_name)
        logger.info(f"Updated constraints for {self.project_name}: {kwargs}")

    def set_constraint(self, key: str, value: Any):
        """Set a single constraint (supports nested keys like 'preferred_agents.coding')"""
        self._preference_store.set_constraint(key, value, self.project_name)
        self._constraints = self._preference_store.get_constraints(self.project_name)

    def _filter_agents_by_constraints(self, agent_names: List[str]) -> List[str]:
        """Filter agents based on developer constraints"""
        filtered = []
        for name in agent_names:
            agent = self.agents.get(name)
            if not agent:
                continue

            # Check if agent is local
            is_local = "local" in name.lower() or "ollama" in name.lower()

            # Estimate cost (0 for local)
            estimated_cost = 0.0 if is_local else 0.01  # Basic estimation

            allowed, reason = self._constraints.should_use_agent(name, is_local, estimated_cost)
            if allowed:
                filtered.append(name)
            elif self._constraints.verbose_routing:
                logger.info(f"Agent {name} filtered: {reason}")

        return filtered

    def _create_routing_decision(
        self,
        selected: str,
        candidates: List[str],
        classification,
        start_time: float,
    ) -> RoutingDecision:
        """Create an explainable routing decision"""
        import time
        from .routing import AgentScore

        # Build candidate scores
        agent_scores = []
        for name in candidates:
            is_local = "local" in name.lower() or "ollama" in name.lower()
            allowed, reason = self._constraints.should_use_agent(name, is_local, 0)
            agent_scores.append(AgentScore(
                agent_name=name,
                total_score=0.8 if name == selected else 0.5,
                breakdown={"task_match": 0.6, "performance": 0.2},
                eligible=allowed,
                rejection_reason=None if allowed else reason,
            ))

        # Determine primary reason
        if self._constraints.prefer_local and "local" in selected.lower():
            reason = "Local agent preferred (privacy/cost)"
        elif selected in self._constraints.preferred_agents.values():
            reason = "User-preferred agent for task type"
        else:
            reason = f"Best match for {classification.primary_type.value} task"

        # Build fallback chain (excluding selected)
        fallbacks = [n for n in candidates if n != selected][:3]

        decision = RoutingDecision(
            selected_agent=selected,
            task_type=classification.primary_type.value,
            complexity=classification.complexity,
            confidence=classification.confidence,
            candidates=agent_scores,
            decision_factors=["task_type", "constraints", "performance"],
            primary_reason=reason,
            constraints_applied=self._constraints.to_dict(),
            constraints_matched=self._constraints.get_matched(),
            fallback_order=fallbacks,
            decision_time_ms=(time.time() - start_time) * 1000,
        )

        # Log the decision
        self._decision_logger.log(decision)

        # Show explanation if verbose
        if self._constraints.verbose_routing or self._constraints.auto_explain:
            logger.info(f"Routing Decision:\n{decision.explain(verbose=True)}")

        return decision

    async def collaborate(
        self,
        prompt: str,
        context: str = "",
        agents: Optional[List[str]] = None,
        mode: Optional[str] = None,
        max_iterations: int = 2,
    ) -> CollaborationResult:
        """
        Execute a collaborative task with the AI team.

        Args:
            prompt: The task or question for the team
            context: Additional context (code, documentation, etc.)
            agents: Specific agents to use (None = auto-select via router)
            mode: Collaboration mode (None = auto-select via router)
            max_iterations: Maximum collaboration rounds

        Returns:
            CollaborationResult with final answer and agent responses
        """
        task_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        collaboration_log = []
        agent_responses = []

        # Use task router for intelligent agent selection and mode
        classification = self._task_router.classify(prompt, context)
        collaboration_log.append(
            f"Task classified: {classification.primary_type.value} "
            f"(complexity: {classification.complexity}, confidence: {classification.confidence:.2f})"
        )

        # Auto-select agents if not specified
        routing_start_time = time.time()
        if not agents:
            available = list(self.agents.keys())

            # v2: Apply developer constraints to filter agents
            available = self._filter_agents_by_constraints(available)
            if not available:
                # Allow cloud fallback if all filtered
                if self._constraints.allow_cloud_fallback:
                    available = list(self.agents.keys())
                    collaboration_log.append("Constraints filtered all local agents, using cloud fallback")

            # Check for user-preferred agent for this task type
            task_type_str = classification.primary_type.value
            if task_type_str in self._constraints.preferred_agents:
                preferred = self._constraints.preferred_agents[task_type_str]
                if preferred in available:
                    agents = [preferred]
                    collaboration_log.append(f"Using user-preferred agent: {preferred}")

            # Use performance-enhanced routing if we have data
            if not agents and self._performance_tracker:
                ranked = self._task_router.get_performance_enhanced_agents(
                    task_type=classification.primary_type,
                    available_agents=available,
                    domain=self.project_name,
                )
                # Select top 3 agents by performance-enhanced score
                agents = [name for name, _, _ in ranked[:3]]
                collaboration_log.append(
                    f"Performance-based selection: {[(n, round(s, 2)) for n, s, _ in ranked[:3]]}"
                )
            elif not agents:
                # Fallback to router's recommendations
                recommended = classification.recommended_agents
                agents = [name for name in recommended if name in available][:3]

            if not agents:
                # Fallback to all available
                agents = available if available else list(self.agents.keys())

            # Apply cost optimization to select best agent for complexity
            if self._cost_optimizer and agents:
                agent_models = {
                    name: getattr(self.agents[name], 'model', '')
                    for name in agents if name in self.agents
                }
                optimal_agent = self._cost_optimizer.select_optimal_agent(
                    available_agents=agents,
                    agent_models=agent_models,
                    complexity=classification.complexity,
                )
                if optimal_agent and optimal_agent in agents:
                    # Move optimal agent to front
                    agents = [optimal_agent] + [a for a in agents if a != optimal_agent]
                collaboration_log.append(
                    f"Cost-optimized for {classification.complexity} complexity"
                )

            collaboration_log.append(f"Auto-selected agents: {agents}")

            # v2: Create and log routing decision
            routing_decision = self._create_routing_decision(
                selected=agents[0] if agents else "none",
                candidates=list(self.agents.keys()),
                classification=classification,
                start_time=routing_start_time,
            )

            # Log to preference store for history
            self._preference_store.log_routing(
                project=self.project_name,
                agent=agents[0] if agents else "none",
                task_type=classification.primary_type.value,
                success=True,  # Will update after completion
                response_time=routing_decision.decision_time_ms / 1000,
            )

        # Auto-select mode if not specified
        if not mode:
            mode = classification.recommended_mode
            collaboration_log.append(f"Auto-selected mode: {mode}")

        # Get prevention context from memory system
        enhanced_prompt = prompt
        if self._prevention:
            prevention_context = await self._prevention.get_prevention_context(
                classification.primary_type.value, self.project_name
            )
            if prevention_context:
                enhanced_prompt = f"{prevention_context}\n\n{prompt}"
                collaboration_log.append("Applied prevention context from past mistakes")

        # Add domain knowledge context
        task_type = classification.primary_type.value
        domain_mapping = {
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
        relevant_domains = domain_mapping.get(task_type, [task_type])

        # Get built-in domain knowledge
        domain_context = get_domain_context(relevant_domains)

        # Get custom teaching knowledge
        teaching_context = self._teaching_system.generate_teaching_context(
            domains=relevant_domains, topics=[task_type]
        )

        if domain_context or teaching_context:
            knowledge_context = "\n".join(filter(None, [domain_context, teaching_context]))
            enhanced_prompt = f"DOMAIN EXPERTISE:\n{knowledge_context}\n\nTASK:\n{enhanced_prompt}"
            collaboration_log.append(f"Applied domain knowledge: {', '.join(relevant_domains)}")

        # Add coding knowledge hub context for coding tasks
        if task_type in ["coding", "debugging", "testing", "optimization"]:
            coding_context = self._coding_hub.generate_coding_context(
                task_description=prompt,
                language=None,  # Auto-detect
                framework=None,  # Auto-detect
                max_items=3,
            )
            if coding_context:
                enhanced_prompt = f"{coding_context}\n\n{enhanced_prompt}"
                collaboration_log.append("Applied coding knowledge hub context")

        # Add RAG context for comprehensive knowledge retrieval
        try:
            rag_context = self._rag.get_context_for_task(
                task_description=prompt,
                max_results=5,
                max_tokens=1500,
            )
            if rag_context.results:
                enhanced_prompt = f"{rag_context.context_text}\n\n{enhanced_prompt}"
                collaboration_log.append(f"Applied RAG context ({len(rag_context.results)} sources)")
        except Exception as e:
            logger.debug(f"RAG context retrieval skipped: {e}")

        # Select active agents
        active_agents = [self.agents[name] for name in agents if name in self.agents]

        if not active_agents:
            return CollaborationResult(
                task_id=task_id,
                success=False,
                final_answer="No agents available for collaboration",
                agent_responses=[],
                collaboration_log=["ERROR: No agents available"],
                total_time=0.0,
                confidence_score=0.0,
                participating_agents=[],
            )

        collaboration_log.append(
            f"Starting {mode} collaboration with {len(active_agents)} agents"
        )

        try:
            if mode == "parallel":
                agent_responses = await self._parallel_collaboration(
                    active_agents, enhanced_prompt, context, collaboration_log
                )
            elif mode == "sequential":
                agent_responses = await self._sequential_collaboration(
                    active_agents, enhanced_prompt, context, collaboration_log
                )
            elif mode == "consensus":
                agent_responses = await self._consensus_collaboration(
                    active_agents, enhanced_prompt, context, max_iterations, collaboration_log,
                    task_type=classification.primary_type.value
                )
            else:
                # Default to parallel
                agent_responses = await self._parallel_collaboration(
                    active_agents, enhanced_prompt, context, collaboration_log
                )

            # Synthesize final answer
            final_answer = await self._synthesize_responses(
                agent_responses, prompt, context
            )

            # Calculate confidence
            successful_responses = [r for r in agent_responses if r.success]
            if successful_responses:
                avg_confidence = sum(r.confidence for r in successful_responses) / len(
                    successful_responses
                )
            else:
                avg_confidence = 0.0

            total_time = time.time() - start_time
            collaboration_log.append(f"Completed in {total_time:.2f}s")

            result = CollaborationResult(
                task_id=task_id,
                success=bool(successful_responses),
                final_answer=final_answer,
                agent_responses=agent_responses,
                collaboration_log=collaboration_log,
                total_time=total_time,
                confidence_score=avg_confidence,
                participating_agents=[a.name for a in active_agents],
                metadata={
                    "mode": mode,
                    "iterations": max_iterations,
                    "prompt": prompt,
                    "context": context,
                    "task_type": classification.primary_type.value,
                    "complexity": classification.complexity,
                },
            )

            # Store in memory and learn from outcome
            if self.enable_memory and self._memory_system:
                await self._memory_system.capture_interaction(result, self.project_name)

                # Learn from successful outcomes
                if self.enable_learning and self._learning_engine and result.success:
                    await self._learning_engine.learn_from_success(
                        result, prompt, self.project_name
                    )

            # Auto-learn from this interaction (extracts prompts, patterns, lessons)
            if self.enable_auto_learning and self._auto_learner:
                await self._auto_learner.capture_interaction(
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
                    task_type=classification.primary_type.value,
                    domains=relevant_domains,
                    models_used=[r.model_type.value for r in agent_responses],
                    duration_seconds=total_time,
                    metadata={
                        "mode": mode,
                        "complexity": classification.complexity,
                        "project": self.project_name,
                    }
                )

            # Auto-learn code to coding hub if successful coding task
            if result.success and task_type in ["coding", "debugging"]:
                # Extract code blocks from the final answer
                import re
                code_blocks = re.findall(r'```(\w+)?\n(.*?)```', final_answer, re.DOTALL)
                for lang, code in code_blocks:
                    if code and len(code.strip()) > 50:
                        self._coding_hub.learn_from_successful_code(
                            code=code.strip(),
                            language=lang or "python",
                            task_description=prompt[:100],
                        )
                        collaboration_log.append(f"Learned code snippet to hub ({lang or 'python'})")

            # Validate generated code and add warnings
            if task_type in ["coding", "debugging", "testing"]:
                validation_results = self._code_validator.validate_response(final_answer)
                validation_warnings = []
                for val_result in validation_results:
                    if val_result.warnings:
                        validation_warnings.extend([str(w) for w in val_result.warnings[:3]])
                    if not val_result.valid:
                        validation_warnings.extend([str(e) for e in val_result.errors[:3]])

                if validation_warnings:
                    result.metadata["validation_warnings"] = validation_warnings[:5]
                    collaboration_log.append(f"Code validation: {len(validation_warnings)} issue(s) found")

                    # Also index the conversation for RAG learning
                    try:
                        self._rag.index_conversation(
                            prompt=prompt,
                            response=final_answer,
                            outcome="success" if result.success else "failure",
                            task_type=task_type,
                            tags=relevant_domains,
                        )
                    except Exception as e:
                        logger.debug(f"RAG conversation indexing skipped: {e}")

            # Record performance outcomes for each agent
            if self._performance_tracker:
                for response in successful_responses:
                    self._performance_tracker.record_outcome(
                        model_name=response.agent_name,
                        task_type=task_type,
                        success=response.success,
                        confidence=response.confidence,
                        response_time=response.response_time,
                        domain=self.project_name,
                        task_id=task_id,
                    )
                collaboration_log.append(f"Recorded performance for {len(successful_responses)} agents")

            return result

        except Exception as e:
            logger.error(f"Collaboration error: {e}")

            # Learn from error
            if self.enable_learning and self._learning_engine:
                await self._learning_engine.learn_from_error(
                    e,
                    {
                        "prompt": prompt,
                        "context": context,
                        "task_type": classification.primary_type.value,
                    },
                    self.project_name,
                )

            return CollaborationResult(
                task_id=task_id,
                success=False,
                final_answer=f"Collaboration failed: {str(e)}",
                agent_responses=agent_responses,
                collaboration_log=collaboration_log + [f"ERROR: {str(e)}"],
                total_time=time.time() - start_time,
                confidence_score=0.0,
                participating_agents=[a.name for a in active_agents],
            )

    async def _parallel_collaboration(
        self,
        agents: List[AIAgent],
        prompt: str,
        context: str,
        log: List[str],
    ) -> List[AgentResponse]:
        """All agents work simultaneously"""
        log.append("Phase 1: Parallel response generation")

        # Filter agents based on circuit breaker state
        available_agents = []
        for agent in agents:
            if self._circuit_breaker.can_execute(agent.name):
                available_agents.append(agent)
            else:
                log.append(f"{agent.name}: SKIPPED (circuit open)")

        if not available_agents:
            log.append("WARNING: All circuits open, trying anyway")
            available_agents = agents

        # Create tasks for available agents
        tasks = [agent.generate_response(prompt, context) for agent in available_agents]

        # Execute in parallel
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Process responses and record health metrics
        agent_responses = []
        for i, response in enumerate(responses):
            agent_name = available_agents[i].name

            if isinstance(response, Exception):
                # Record failure in health monitor
                self._health_monitor.record_request(
                    agent_name, latency=0, success=False,
                    error_type=type(response).__name__,
                    error_message=str(response),
                )
                self._circuit_breaker.record_failure(agent_name, str(response))
                log.append(f"{agent_name}: ERROR - {str(response)}")

            elif isinstance(response, AgentResponse):
                # Record success/failure in health monitor
                self._health_monitor.record_request(
                    agent_name,
                    latency=response.response_time,
                    success=response.success,
                    error_type=None if response.success else "agent_error",
                    error_message=response.error if not response.success else None,
                )

                if response.success:
                    self._circuit_breaker.record_success(agent_name)
                else:
                    self._circuit_breaker.record_failure(agent_name, response.error)

                agent_responses.append(response)
                status = "OK" if response.success else f"FAILED: {response.error}"
                log.append(f"{agent_name}: {status}")

        return agent_responses

    async def _sequential_collaboration(
        self,
        agents: List[AIAgent],
        prompt: str,
        context: str,
        log: List[str],
    ) -> List[AgentResponse]:
        """Agents work in sequence, each building on previous responses"""
        log.append("Phase 1: Sequential response generation")
        agent_responses = []
        accumulated_context = context

        for i, agent in enumerate(agents):
            # Add previous responses to context
            if agent_responses:
                prev_responses = "\n\n".join(
                    f"Previous response from {r.agent_name}:\n{r.content[:500]}..."
                    for r in agent_responses
                    if r.success
                )
                accumulated_context = f"{context}\n\nTeam Progress:\n{prev_responses}"

            response = await agent.generate_response(prompt, accumulated_context)
            agent_responses.append(response)

            status = "OK" if response.success else f"FAILED: {response.error}"
            log.append(f"Step {i + 1}/{len(agents)} - {agent.name}: {status}")

        return agent_responses

    async def _consensus_collaboration(
        self,
        agents: List[AIAgent],
        prompt: str,
        context: str,
        max_iterations: int,
        log: List[str],
        task_type: str = "general",
    ) -> List[AgentResponse]:
        """Multiple rounds to build consensus with weighted voting"""
        all_responses = []

        for iteration in range(max_iterations):
            log.append(f"Consensus round {iteration + 1}/{max_iterations}")

            # Build context from previous round
            if all_responses:
                prev_context = "\n\n".join(
                    f"{r.agent_name}:\n{r.content[:300]}..."
                    for r in all_responses[-len(agents) :]
                    if r.success
                )
                round_context = f"{context}\n\nPrevious Team Responses:\n{prev_context}"
                round_prompt = (
                    f"Review team responses and refine your answer:\n{prompt}"
                )
            else:
                round_context = context
                round_prompt = prompt

            # Get responses for this round
            tasks = [agent.generate_response(round_prompt, round_context) for agent in agents]
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            round_responses = []
            for i, response in enumerate(responses):
                if isinstance(response, AgentResponse):
                    all_responses.append(response)
                    round_responses.append(response)
                    log.append(f"  {agents[i].name}: {'OK' if response.success else 'FAILED'}")

            # Apply weighted consensus analysis after first round
            if self._weighted_consensus and round_responses:
                consensus_result = self._weighted_consensus.calculate_weighted_vote(
                    round_responses, task_type
                )
                log.append(
                    f"  Consensus level: {consensus_result.consensus_level:.0%} "
                    f"(threshold: {self._weighted_consensus.consensus_threshold:.0%})"
                )

                # If consensus reached early, we can stop
                if consensus_result.consensus_reached and iteration > 0:
                    log.append(f"  Consensus reached - stopping early")
                    break

                # If disagreements found, initiate debate
                if consensus_result.disagreements and iteration < max_iterations - 1:
                    log.append(f"  Disagreements detected: {len(consensus_result.disagreements)}")
                    debate_rounds = await self._weighted_consensus.initiate_debate(
                        consensus_result.disagreements[:1],  # Limit to 1 debate topic
                        agents[:3],
                        prompt,
                        context,
                    )
                    if debate_rounds:
                        log.append(f"  Completed {len(debate_rounds)} debate round(s)")

        return all_responses

    async def _synthesize_responses(
        self,
        responses: List[AgentResponse],
        prompt: str,
        context: str,
    ) -> str:
        """Synthesize multiple responses into a final answer"""
        successful_responses = [r for r in responses if r.success]

        if not successful_responses:
            return "No successful responses from the AI team."

        if len(successful_responses) == 1:
            return successful_responses[0].content

        # Use Claude for synthesis if available (try multiple name patterns)
        synthesis_agent = None
        claude_patterns = ["claude-analyst", "claude", "anthropic"]
        for pattern in claude_patterns:
            for agent_name, agent in self.agents.items():
                if pattern in agent_name.lower():
                    synthesis_agent = agent
                    break
            if synthesis_agent:
                break

        # Fall back to first available agent
        if not synthesis_agent:
            synthesis_agent = next(iter(self.agents.values()), None)

        if not synthesis_agent:
            # Fallback: concatenate responses
            return "\n\n---\n\n".join(
                f"**{r.agent_name}:**\n{r.content}" for r in successful_responses
            )

        # Build synthesis prompt
        responses_text = "\n\n".join(
            f"[{r.agent_name} - {r.model_type.value}]:\n{r.content}"
            for r in successful_responses
        )

        synthesis_prompt = f"""Synthesize these AI team responses into one comprehensive answer.
Combine the best insights from each response. Be concise but complete.

Original Task: {prompt}

Team Responses:
{responses_text}

Provide a unified, synthesized response:"""

        synthesis_response = await synthesis_agent.generate_response(
            synthesis_prompt, context
        )

        if synthesis_response.success:
            return synthesis_response.content
        else:
            # Fallback to best single response
            best = max(successful_responses, key=lambda r: r.confidence)
            return best.content

    async def ask(
        self,
        prompt: str,
        agent: Optional[str] = None,
        context: str = "",
    ) -> AgentResponse:
        """
        Quick single-agent query.

        Args:
            prompt: Question or task
            agent: Specific agent name (None = auto-select via router)
            context: Additional context

        Returns:
            AgentResponse from the selected agent
        """
        if agent and agent in self.agents:
            selected_agent = self.agents[agent]
        elif self.agents:
            # Use task router to select best agent for the task
            classification = self._task_router.classify(prompt, context)
            recommended = classification.recommended_agents

            # Find first available recommended agent
            selected_agent = None
            for agent_name in recommended:
                if agent_name in self.agents:
                    selected_agent = self.agents[agent_name]
                    break

            # Fallback to Claude (try multiple patterns) or first available
            if not selected_agent:
                for pattern in ["claude-analyst", "claude", "anthropic"]:
                    for agent_name, agent in self.agents.items():
                        if pattern in agent_name.lower():
                            selected_agent = agent
                            break
                    if selected_agent:
                        break

            if not selected_agent:
                selected_agent = next(iter(self.agents.values()), None)
        else:
            return AgentResponse(
                agent_name="none",
                model_type=ModelType.LOCAL,
                content="",
                confidence=0.0,
                response_time=0.0,
                error="No agents available",
            )

        start_time = time.time()
        response = await selected_agent.generate_response(prompt, context)

        # Auto-learn from single-agent queries too
        if self.enable_auto_learning and self._auto_learner:
            # Detect task type for single queries
            classification = self._task_router.classify(prompt, context)
            await self._auto_learner.capture_interaction(
                user_prompt=prompt,
                ai_responses=[
                    {
                        "agent_name": response.agent_name,
                        "content": response.content,
                        "success": response.success,
                        "confidence": response.confidence,
                        "model_type": response.model_type.value,
                    }
                ],
                outcome="success" if response.success else "failure",
                task_type=classification.primary_type.value,
                models_used=[response.model_type.value],
                duration_seconds=time.time() - start_time,
            )

        return response

    def get_team_status(self) -> Dict[str, Any]:
        """Get status of all team members"""
        status = {
            "project": self.project_name,
            "total_agents": len(self.agents),
            "memory_enabled": self.enable_memory,
            "learning_enabled": self.enable_learning,
            "auto_learning_enabled": self.enable_auto_learning,
            "agents": {name: agent.get_stats() for name, agent in self.agents.items()},
        }

        # Add auto-learning stats if enabled
        if self._auto_learner:
            status["auto_learning"] = self._auto_learner.get_statistics()

        # Add teaching system stats
        status["knowledge"] = self._teaching_system.get_statistics()

        # Add cost optimization stats
        if self._cost_optimizer:
            budget_status = self._cost_optimizer.get_budget_status()
            status["cost_optimization"] = {
                "daily_spent": budget_status.daily_spent,
                "daily_remaining": budget_status.remaining_daily,
                "monthly_spent": budget_status.monthly_spent,
                "monthly_remaining": budget_status.remaining_monthly,
            }

        # Add performance tracking stats
        if self._performance_tracker:
            status["performance_tracking"] = self._performance_tracker.get_statistics()

        # Add health monitoring stats
        if self._health_monitor:
            status["health_monitoring"] = self._health_monitor.get_statistics()

        # Add failover stats
        if self._failover_manager:
            status["failover"] = self._failover_manager.get_statistics()

        # v2: Add routing and constraints info
        status["v2_routing"] = {
            "constraints": self._constraints.to_dict(),
            "decision_stats": self._decision_logger.get_stats(),
            "verbose_routing": self._constraints.verbose_routing,
        }

        return status

    def get_cost_report(self) -> Dict[str, Any]:
        """Get detailed cost report"""
        if self._cost_optimizer:
            return self._cost_optimizer.get_cost_report()
        return {"error": "Cost optimizer not enabled"}

    def set_budget(self, daily: float = None, monthly: float = None):
        """Set cost budgets"""
        if self._cost_optimizer:
            if daily is not None:
                self._cost_optimizer.daily_budget = daily
            if monthly is not None:
                self._cost_optimizer.monthly_budget = monthly

    # =================
    # v2: Explainable Routing
    # =================

    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing decision statistics"""
        return {
            "decision_logger": self._decision_logger.get_stats(),
            "agent_performance": self._preference_store.get_agent_stats(self.project_name),
            "constraints": self._constraints.to_dict(),
        }

    def get_recent_decisions(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent routing decisions with explanations"""
        decisions = self._decision_logger.get_recent(count)
        return [d.to_dict() for d in decisions]

    def explain_last_decision(self, verbose: bool = False) -> str:
        """Get explanation of the most recent routing decision"""
        decisions = self._decision_logger.get_recent(1)
        if decisions:
            return decisions[0].explain(verbose=verbose)
        return "No routing decisions recorded yet"

    def why(self) -> str:
        """
        Quick shorthand to explain why the last agent was selected.

        Usage:
            result = await team.collaborate("Fix the bug")
            print(team.why())  # "Selected: local-llama3 for debugging (prefer_local=True)"
        """
        return self.explain_last_decision(verbose=False)

    def suggest_prompt(self, prompt: str) -> Optional[str]:
        """
        Suggest an improved prompt based on learned patterns.

        Args:
            prompt: The original prompt

        Returns:
            Improved prompt or None if no suggestions
        """
        if self._auto_learner:
            return self._auto_learner.suggest_prompt_improvement(prompt)
        return None

    def get_effective_prompts(
        self,
        task_type: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get prompts that have worked well in the past.

        Args:
            task_type: Filter by task type (coding, debugging, etc.)
            domain: Filter by domain (frontend, backend, etc.)

        Returns:
            List of effective prompt patterns
        """
        if not self._auto_learner:
            return []

        prompts = self._auto_learner.get_effective_prompts(
            task_type=task_type,
            domain=domain
        )

        return [
            {
                "original": p.original_prompt,
                "refined": p.refined_prompt,
                "task_type": p.task_type,
                "domains": p.domains,
                "success_rate": p.success_rate,
                "usage_count": p.usage_count,
            }
            for p in prompts[:10]  # Return top 10
        ]

    def get_learned_insights(
        self,
        insight_type: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get insights learned from interactions.

        Args:
            insight_type: "lesson", "pattern", "mistake", "solution"
            domain: Filter by domain

        Returns:
            List of learned insights
        """
        if not self._auto_learner:
            return []

        insights = self._auto_learner.get_insights(
            insight_type=insight_type,
            domain=domain
        )

        return [
            {
                "type": i.insight_type,
                "content": i.content,
                "confidence": i.confidence,
                "domains": i.domains,
            }
            for i in insights[:20]  # Return top 20
        ]

    async def start_background_learning(self):
        """Start background auto-learning process"""
        if self._auto_learner:
            await self._auto_learner.start_background_learning()
            logger.info("Background auto-learning started")

    async def code_review(
        self,
        code: str,
        language: str = "python",
        focus: Optional[List[str]] = None,
    ) -> CollaborationResult:
        """
        Collaborative code review.

        Args:
            code: Code to review
            language: Programming language
            focus: Specific aspects to focus on (security, performance, etc.)

        Returns:
            CollaborationResult with review feedback
        """
        focus_str = ", ".join(focus) if focus else "code quality, bugs, and improvements"

        prompt = f"""Review this {language} code. Focus on: {focus_str}

Provide:
1. Issues found (with severity)
2. Suggestions for improvement
3. Security concerns (if any)
4. Overall assessment

Code:
```{language}
{code}
```"""

        return await self.collaborate(prompt, mode="parallel")

    async def debug(
        self,
        error: str,
        code: str = "",
        context: str = "",
    ) -> CollaborationResult:
        """
        Collaborative debugging session.

        Args:
            error: Error message or description
            code: Related code (if any)
            context: Additional context

        Returns:
            CollaborationResult with debugging insights
        """
        prompt = f"""Debug this issue:

Error: {error}

{f'Code:```{code}```' if code else ''}

Provide:
1. Root cause analysis
2. Step-by-step fix
3. Prevention strategies"""

        return await self.collaborate(prompt, context=context, mode="consensus")

    async def architect(
        self,
        requirements: str,
        constraints: Optional[List[str]] = None,
    ) -> CollaborationResult:
        """
        Collaborative architecture design.

        Args:
            requirements: System requirements
            constraints: Technical constraints

        Returns:
            CollaborationResult with architecture proposal
        """
        constraints_str = "\n".join(f"- {c}" for c in constraints) if constraints else "None specified"

        prompt = f"""Design a system architecture for:

Requirements:
{requirements}

Constraints:
{constraints_str}

Provide:
1. High-level architecture
2. Component breakdown
3. Technology recommendations
4. Trade-offs and considerations"""

        return await self.collaborate(prompt, mode="consensus", max_iterations=2)

    # =================
    # Tool Access Methods
    # =================

    def get_tools(self) -> Dict[str, Any]:
        """Get all available tools"""
        return self._tools

    def get_tool_capabilities(self) -> Dict[str, List[Dict[str, str]]]:
        """
        Get capabilities of all registered tools.

        Returns:
            Dict mapping tool names to their operations
        """
        capabilities = {}
        for name, tool in self._tools.items():
            capabilities[name] = tool.get_capabilities()
        return capabilities

    async def execute_tool(
        self,
        tool_name: str,
        operation: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a tool operation.

        Args:
            tool_name: Name of tool (filesystem, browser, shell)
            operation: Operation to perform
            **kwargs: Operation parameters

        Returns:
            Dict with success, output, error keys
        """
        # Security validation before execution
        security_result = validate_tool_call({
            "tool": tool_name,
            "operation": operation,
            "params": kwargs
        })

        if not security_result.is_valid:
            logger.warning(
                f"SECURITY BLOCKED: {tool_name}.{operation} - "
                f"Threat: {security_result.threat_level.name}, Issues: {security_result.issues}"
            )
            return {
                "success": False,
                "output": None,
                "error": f"Security validation failed: {'; '.join(security_result.issues)}",
                "threat_level": security_result.threat_level.name,
            }

        if tool_name not in self._tools:
            return {
                "success": False,
                "output": None,
                "error": f"Unknown tool: {tool_name}. Available: {list(self._tools.keys())}"
            }

        tool = self._tools[tool_name]
        result = await tool.execute(operation, **kwargs)

        return {
            "success": result.success,
            "output": result.output,
            "error": result.error,
            "metadata": result.metadata,
            "execution_time": result.execution_time,
        }

    def grant_tool_permission(
        self,
        tool_name: str,
        operation: str,
        level: str = "session"
    ):
        """
        Grant permission for a tool operation.

        Args:
            tool_name: Tool name
            operation: Operation to grant
            level: "session" (temporary) or "always" (persistent)
        """
        from .tools.base import PermissionLevel

        perm_level = PermissionLevel.SESSION if level == "session" else PermissionLevel.ALWAYS
        self._permission_manager.grant_permission(tool_name, operation, perm_level)
        logger.info(f"Granted {level} permission for {tool_name}.{operation}")

    def revoke_tool_permission(self, tool_name: str, operation: str):
        """Revoke permission for a tool operation"""
        self._permission_manager.revoke_permission(tool_name, operation)
        logger.info(f"Revoked permission for {tool_name}.{operation}")

    def list_tool_permissions(self) -> List[Dict[str, Any]]:
        """List all granted tool permissions"""
        permissions = self._permission_manager.get_all_permissions()
        return [
            {
                "tool": p.tool_name,
                "operation": p.operation,
                "level": p.level.name,
                "granted_at": p.granted_at,
            }
            for p in permissions
        ]

    # =================
    # Agentic Tool Execution
    # =================

    async def agentic_task(
        self,
        task: str,
        allowed_tools: Optional[List[str]] = None,
        max_tool_calls: int = 10,
        agent_name: Optional[str] = None,
    ) -> CollaborationResult:
        """
        Execute a task where the AI agent can autonomously use tools.

        The agent will analyze the task, decide which tools to use,
        execute them, and synthesize results.

        Args:
            task: Task description
            allowed_tools: List of allowed tool names (default: all)
            max_tool_calls: Maximum tool calls allowed
            agent_name: Specific agent to use (auto-select if None)

        Returns:
            CollaborationResult with task outcome
        """
        start_time = time.time()
        task_id = str(uuid.uuid4())[:8]
        collaboration_log = []

        # Select agent
        if agent_name and agent_name in self.agents:
            agent = self.agents[agent_name]
        else:
            # Use task router to select best agent
            classification = self._task_router.classify(task, "")
            agent_name = classification.recommended_agents[0] if classification.recommended_agents else None
            agent = self.agents.get(agent_name) if agent_name else list(self.agents.values())[0]

        collaboration_log.append(f"Selected agent: {agent.name}")

        # Build tool context
        available_tools = allowed_tools or list(self._tools.keys())
        tool_info = self._build_tool_context(available_tools)

        # Initial prompt with tool capabilities
        agentic_prompt = f"""You are an AI agent with DIRECT ACCESS to real tools. You MUST use these tools to complete the task.
DO NOT write code to solve the problem - USE THE TOOLS DIRECTLY.

AVAILABLE TOOLS (you MUST use these):
{tool_info}

TASK: {task}

IMPORTANT: To use a tool, output EXACTLY this format (one per line):
TOOL_CALL: filesystem.list(path=".", pattern="*.py")
TOOL_CALL: filesystem.read(path="./file.py")
TOOL_CALL: shell.run_safe(command="pwd")

Start by making tool calls to gather information. Output your tool calls now:"""

        responses = []
        tool_calls_made = 0
        tool_results = []

        # Initial agent response
        response = await agent.generate_response(agentic_prompt)
        responses.append(response)
        collaboration_log.append(f"Agent initial response received")

        # Parse and execute tool calls
        while tool_calls_made < max_tool_calls:
            tool_calls = self._parse_tool_calls(response.content)

            if not tool_calls:
                break  # No more tool calls

            for call in tool_calls:
                if tool_calls_made >= max_tool_calls:
                    break

                tool_name = call.get("tool")
                operation = call.get("operation")
                params = call.get("params", {})

                if tool_name not in available_tools:
                    tool_results.append({
                        "call": call,
                        "result": {"success": False, "error": f"Tool {tool_name} not allowed"}
                    })
                    continue

                collaboration_log.append(f"Executing: {tool_name}.{operation}")
                result = await self.execute_tool(tool_name, operation, **params)
                tool_results.append({"call": call, "result": result})
                tool_calls_made += 1

            # If we made tool calls, send results back to agent
            if tool_results:
                results_str = self._format_tool_results(tool_results[-len(tool_calls):])
                followup_prompt = f"""Tool execution results:
{results_str}

Continue with the task. Make more tool calls if needed, or provide your final answer."""

                response = await agent.generate_response(followup_prompt, context=response.content)
                responses.append(response)

        # Get final answer
        final_answer = response.content

        # Record in auto-learner
        if self._auto_learner:
            await self._auto_learner.capture_interaction(
                user_prompt=task,
                ai_responses=[{"agent": agent.name, "content": final_answer}],
                outcome="completed",
                task_type="agentic_task",
                metadata={
                    "tools_used": [tr["call"]["tool"] for tr in tool_results],
                    "tool_calls_count": tool_calls_made,
                }
            )

        return CollaborationResult(
            task_id=task_id,
            success=True,
            final_answer=final_answer,
            agent_responses=responses,
            collaboration_log=collaboration_log,
            total_time=time.time() - start_time,
            confidence_score=response.confidence if hasattr(response, 'confidence') else 0.8,
            participating_agents=[agent.name],
            metadata={
                "tool_calls": tool_calls_made,
                "tool_results": tool_results,
                "mode": "agentic",
            }
        )

    def _build_tool_context(self, allowed_tools: List[str]) -> str:
        """Build tool context string for agent prompt"""
        lines = []
        for tool_name in allowed_tools:
            if tool_name in self._tools:
                tool = self._tools[tool_name]
                lines.append(f"\n{tool_name.upper()}:")
                for cap in tool.get_capabilities():
                    lines.append(f"  - {cap['operation']}: {cap['description']}")
        return "\n".join(lines)

    def _parse_tool_calls(self, content: str) -> List[Dict[str, Any]]:
        """Parse tool calls from agent response with security validation"""
        import re
        calls = []
        security_validator = get_security_validator()

        # Pattern: TOOL_CALL: tool.operation(param=value, ...)
        pattern = r'TOOL_CALL:\s*(\w+)\.(\w+)\(([^)]*)\)'
        matches = re.findall(pattern, content)

        for tool, operation, params_str in matches:
            params = {}
            if params_str.strip():
                # Parse params like: param1=value1, param2="value2"
                param_pattern = r'(\w+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^,\s]+))'
                for match in re.findall(param_pattern, params_str):
                    key = match[0]
                    value = match[1] or match[2] or match[3]
                    # Try to convert to appropriate type
                    if value.lower() == 'true':
                        value = True
                    elif value.lower() == 'false':
                        value = False
                    elif value.isdigit():
                        value = int(value)
                    params[key] = value

            # Build the call dict
            call = {
                "tool": tool,
                "operation": operation,
                "params": params,
            }

            # Security validation at parse time
            validation = security_validator.validate_tool_call(call)
            if validation.is_valid:
                calls.append(call)
            else:
                # Log blocked calls but don't include them
                logger.warning(
                    f"SECURITY: Blocked parsed tool call {tool}.{operation} - "
                    f"Threat: {validation.threat_level.name}, Issues: {validation.issues}"
                )

        return calls

    def _format_tool_results(self, tool_results: List[Dict]) -> str:
        """Format tool results for agent"""
        lines = []
        for tr in tool_results:
            call = tr["call"]
            result = tr["result"]
            lines.append(f"\n{call['tool']}.{call['operation']}:")
            if result["success"]:
                output = result.get("output", "")
                if isinstance(output, dict):
                    import json
                    output = json.dumps(output, indent=2)[:1000]
                elif isinstance(output, list):
                    import json
                    output = json.dumps(output[:10], indent=2)[:1000]
                else:
                    output = str(output)[:1000]
                lines.append(f"  SUCCESS: {output}")
            else:
                lines.append(f"  ERROR: {result.get('error', 'Unknown error')}")
        return "\n".join(lines)

    async def browse_and_analyze(
        self,
        url: str,
        question: str,
    ) -> CollaborationResult:
        """
        Fetch a web page and have the AI team analyze it.

        Args:
            url: URL to fetch
            question: What to analyze or extract

        Returns:
            CollaborationResult with analysis
        """
        # Grant temporary permission for browser fetch
        self.grant_tool_permission("browser", "fetch", "session")

        # Fetch the page
        result = await self.execute_tool("browser", "fetch", url=url)

        if not result["success"]:
            return CollaborationResult(
                task_id=str(uuid.uuid4())[:8],
                success=False,
                final_answer=f"Failed to fetch URL: {result['error']}",
                agent_responses=[],
                collaboration_log=[f"Browser fetch failed: {result['error']}"],
                total_time=0,
                confidence_score=0,
                participating_agents=[],
            )

        # Analyze with AI team
        page_content = result["output"].get("text", "")[:10000]  # Limit content
        prompt = f"""Analyze this web page content:

URL: {url}

Question: {question}

Page Content:
{page_content}

Provide a detailed analysis answering the question."""

        return await self.collaborate(prompt, mode="parallel")

    async def read_and_analyze_file(
        self,
        file_path: str,
        question: str,
    ) -> CollaborationResult:
        """
        Read a file and have the AI team analyze it.

        Args:
            file_path: Path to file
            question: What to analyze

        Returns:
            CollaborationResult with analysis
        """
        # Read the file
        result = await self.execute_tool("filesystem", "read", path=file_path)

        if not result["success"]:
            return CollaborationResult(
                task_id=str(uuid.uuid4())[:8],
                success=False,
                final_answer=f"Failed to read file: {result['error']}",
                agent_responses=[],
                collaboration_log=[f"File read failed: {result['error']}"],
                total_time=0,
                confidence_score=0,
                participating_agents=[],
            )

        # Analyze with AI team
        file_content = result["output"][:20000]  # Limit content
        prompt = f"""Analyze this file:

File: {file_path}

Question: {question}

Content:
```
{file_content}
```

Provide a detailed analysis."""

        return await self.collaborate(prompt, mode="parallel")

    # =================
    # Advanced Agent Framework
    # =================

    def _get_best_agent(self) -> Optional[AIAgent]:
        """Get the best available agent for framework tasks."""
        if not self.agents:
            return None

        # Prefer Claude for reasoning tasks
        for pattern in ["claude", "anthropic"]:
            for name, agent in self.agents.items():
                if pattern in name.lower():
                    return agent

        # Then try ChatGPT
        for pattern in ["chatgpt", "openai", "gpt"]:
            for name, agent in self.agents.items():
                if pattern in name.lower():
                    return agent

        # Then any cloud agent
        for name, agent in self.agents.items():
            if "local" not in name.lower():
                return agent

        # Finally, any agent
        return list(self.agents.values())[0]

    async def react(
        self,
        task: str,
        max_steps: int = 10,
        verbose: bool = False,
    ) -> ReActTrace:
        """
        Execute a task using ReAct (Reasoning + Acting) pattern.

        ReAct interleaves reasoning with tool use for complex problem solving.
        The agent will think step-by-step, decide on actions, observe results,
        and continue until the task is complete.

        Args:
            task: The task to solve
            max_steps: Maximum reasoning/action steps
            verbose: Print steps as they execute

        Returns:
            ReActTrace with complete execution history

        Example:
            trace = await team.react("Find all TODO comments in Python files")
            print(trace.final_answer)
        """
        # Create LLM call function using best available agent
        agent = self._get_best_agent()

        if not agent:
            return ReActTrace(
                task=task,
                success=False,
                final_answer="No agents available for ReAct execution",
            )

        async def llm_call(prompt: str, system: str) -> str:
            context = system if system else ""
            response = await agent.generate_response(prompt, context)
            return response.content if response.success else f"Error: {response.error}"

        # Create and run ReAct agent
        react_agent = ReActAgent(
            llm_call=llm_call,
            tools=get_tool_registry(),
            max_steps=max_steps,
            verbose=verbose,
        )

        trace = await react_agent.run(task)

        # Auto-learn from ReAct execution
        if self._auto_learner and trace.success:
            # Ensure final_answer is a string for auto-learner
            answer_str = trace.final_answer if isinstance(trace.final_answer, str) else str(trace.final_answer)
            await self._auto_learner.capture_interaction(
                user_prompt=task,
                ai_responses=[{"agent": "react", "content": answer_str}],
                outcome="success",
                task_type="react",
                metadata={
                    "steps": len(trace.steps),
                    "tools_used": trace.tools_used,
                }
            )

        return trace

    async def plan_and_execute(
        self,
        goal: str,
        context: str = "",
        available_tools: Optional[List[str]] = None,
    ) -> ExecutionPlan:
        """
        Create and execute a multi-step plan for achieving a goal.

        The planner will decompose the goal into steps, track dependencies,
        and execute steps in parallel when possible.

        Args:
            goal: The goal to achieve
            context: Additional context
            available_tools: List of available tool names

        Returns:
            ExecutionPlan with results

        Example:
            plan = await team.plan_and_execute("Set up a new Python project with tests")
            print(plan.to_markdown())
        """
        # Create LLM call function
        agent = self._get_best_agent()

        if not agent:
            return ExecutionPlan(
                id="error",
                goal=goal,
                steps=[],
                metadata={"error": "No agents available"},
            )

        async def llm_call(prompt: str) -> str:
            response = await agent.generate_response(prompt, context)
            return response.content if response.success else ""

        # Create planner
        planner = TaskPlanner(llm_call=llm_call)

        # Create plan
        plan = await planner.create_plan(
            goal=goal,
            context=context,
            available_tools=available_tools,
        )

        # Optimize plan for parallelization
        plan = await planner.optimize_plan(plan)

        # Execute plan with callbacks
        def on_step_start(step):
            logger.info(f"Starting step: {step.description}")

        def on_step_complete(step):
            logger.info(f"Completed step: {step.description}")

        def on_step_failed(step, error):
            logger.warning(f"Step failed: {step.description} - {error}")

        executed_plan = await planner.execute_plan(
            plan,
            on_step_start=on_step_start,
            on_step_complete=on_step_complete,
            on_step_failed=on_step_failed,
        )

        return executed_plan

    async def reason(
        self,
        problem: str,
        method: str = "zero_shot",
        verify: bool = False,
    ) -> ReasoningChain:
        """
        Apply chain-of-thought reasoning to a problem.

        Encourages step-by-step reasoning for more accurate answers.

        Args:
            problem: The problem to reason about
            method: "zero_shot", "few_shot", "self_consistency", or "tree_of_thought"
            verify: Whether to verify the reasoning chain

        Returns:
            ReasoningChain with steps and conclusion

        Example:
            chain = await team.reason("What is 17 * 23?")
            print(chain.conclusion)
        """
        from .framework import ReasoningType

        # Map method string to enum
        method_map = {
            "zero_shot": ReasoningType.ZERO_SHOT,
            "few_shot": ReasoningType.FEW_SHOT,
            "self_consistency": ReasoningType.SELF_CONSISTENCY,
            "tree_of_thought": ReasoningType.TREE_OF_THOUGHT,
        }
        reasoning_type = method_map.get(method, ReasoningType.ZERO_SHOT)

        # Create LLM call function
        agent = self._get_best_agent()

        if not agent:
            return ReasoningChain(
                problem=problem,
                steps=[],
                conclusion="No agents available for reasoning",
                confidence=0.0,
                reasoning_type=reasoning_type,
            )

        async def llm_call(prompt: str, system: str = None) -> str:
            context = system if system else ""
            response = await agent.generate_response(prompt, context)
            return response.content if response.success else ""

        # Create chain-of-thought reasoner
        cot = ChainOfThought(
            llm_call=llm_call,
            default_type=reasoning_type,
            verify_reasoning=verify,
        )

        return await cot.reason(problem, reasoning_type=reasoning_type)

    def get_context_manager(self, max_tokens: int = 8000) -> ContextManager:
        """
        Get a context manager for managing conversation history.

        Useful for long conversations that need to fit within token limits.

        Args:
            max_tokens: Maximum tokens for the context window

        Returns:
            ContextManager instance
        """
        return ContextManager(max_tokens=max_tokens)

    def get_framework_tools(self) -> List[str]:
        """
        Get list of available framework tools.

        Returns:
            List of tool names registered in the framework
        """
        return get_tool_registry().list_tools()

    def get_framework_tool_schemas(self, format: str = "openai") -> List[Dict[str, Any]]:
        """
        Get tool schemas for API integration.

        Args:
            format: "openai" or "anthropic"

        Returns:
            List of tool schemas in the specified format
        """
        return get_tool_registry().get_schemas(format=format)


# Convenience function for quick setup
def create_team(project_name: str = "default", **kwargs) -> AIDevTeam:
    """Create and configure an AI development team"""
    return AIDevTeam(project_name=project_name, **kwargs)
