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
from .routing.cost_tracker import get_cost_tracker
from .preferences import get_preference_store, DevConstraints
from .monitoring import get_health_monitor
from .failover import get_failover_manager, get_circuit_breaker
from .memory import MemorySystem, LearningEngine, MistakePrevention
from .collaboration import WeightedConsensus
from .knowledge import TeachingSystem, get_domain_context, AutoLearner, get_coding_hub, get_rag
from .tools import FileSystemTools, BrowserTools, ShellTools, PermissionManager
from .sessions import get_session_manager
from .personas import get_persona_manager
from .validation import get_validator
from .autonomous import (
    SelfCorrector,
    TaskDecomposer,
    SessionLearner,
    TaskOutcome,
    TeamAdapter,
)
from .tools.tool_manager import ToolManager
from .autonomous.executor import AutonomousExecutor
from .framework.facade import FrameworkFacade

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
    intelligence: Dict[str, Any] = field(default_factory=dict)


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
        local_only: bool = False,
    ):
        self.project_name = project_name
        self.agents: Dict[str, AIAgent] = {}
        self.enable_memory = enable_memory
        self.enable_learning = enable_learning
        self.enable_auto_learning = enable_auto_learning
        self.local_only = local_only  # Use only local Ollama models (no cloud APIs)

        # Initialize task router, cost optimizer, and performance tracker
        self._task_router = TaskRouter()
        self._cost_optimizer = CostOptimizer()
        self._weighted_consensus = WeightedConsensus()
        self._performance_tracker = get_performance_tracker()
        self._cost_tracker = get_cost_tracker()

        # Initialize Apple Silicon smart router for local model optimization
        self._apple_router = None
        try:
            from .apple.smart_router import get_smart_router
            self._apple_router = get_smart_router(prefer_local=not local_only)
            if self._apple_router.hardware:
                logger.info(f"Apple Silicon detected: {self._apple_router.hardware.chip} {self._apple_router.hardware.variant} ({self._apple_router.hardware.memory_gb}GB)")
        except Exception as e:
            logger.debug(f"Apple router not available: {e}")

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

        # Initialize autonomous capabilities
        self._self_corrector = SelfCorrector(max_attempts=3, confidence_threshold=0.7)
        self._task_decomposer = TaskDecomposer(ai_analyzer=self._decompose_analyze)
        # Load persisted learning data or create new
        self._session_learner = SessionLearner.load_or_create(
            failure_threshold=3, learning_rate=0.1
        )
        self._team_adapter = TeamAdapter(self._session_learner)

        # Enable autonomous features by default
        self.enable_self_correction = True
        self.enable_task_decomposition = True
        self.enable_session_learning = True

        # Extracted managers (delegate to reduce orchestrator size)
        self.tool_manager = ToolManager(self)
        self.autonomous_executor = AutonomousExecutor(self)
        self.framework_facade = FrameworkFacade(self)

        # Auto-benchmark flag — run once per session if stale
        self._benchmark_checked = False

        if auto_setup:
            self.setup_agents()

    def setup_agents(self):
        """Setup default AI team based on available API keys"""
        if self.local_only:
            # Local-only mode: skip all cloud APIs, use only Ollama
            logger.info("Local-only mode: using Ollama models only (no cloud APIs)")
            self._setup_local_agents()
            if not self.agents:
                logger.warning(
                    "No local Ollama models available. "
                    "Install Ollama and run: ollama pull llama3.2:3b"
                )
            return

        # Cloud agents (requires API keys)
        # ChatGPT - Lead Developer & Architect
        if os.getenv("OPENAI_API_KEY"):
            self.register_agent(ChatGPTAgent())
            logger.info("Registered ChatGPT agent (Lead Developer & Architect)")

        # Claude - Analyst (optional, requires ANTHROPIC_API_KEY)
        if os.getenv("ANTHROPIC_API_KEY"):
            self.register_agent(ClaudeAgent())
            logger.info("Registered Claude agent (Analyst)")

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

        # Custom personas (user-defined specialist agents)
        try:
            pm = get_persona_manager()
            pm.register_all(self)
        except Exception as e:
            logger.debug(f"Persona registration skipped: {e}")

        if not self.agents:
            logger.warning(
                "No AI agents configured. Set API keys: "
                "ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY, XAI_API_KEY "
                "or use local_only=True with Ollama"
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

        # Build candidate scores using actual router data
        ranked = self._task_router.get_performance_enhanced_agents(
            classification.primary_type, candidates
        )
        ranked_scores = {name: (score, details) for name, score, details in ranked}

        agent_scores = []
        for name in candidates:
            is_local = "local" in name.lower() or "ollama" in name.lower()
            allowed, reason = self._constraints.should_use_agent(name, is_local, 0)
            score, details = ranked_scores.get(name, (0.5, {}))
            agent_scores.append(AgentScore(
                agent_name=name,
                total_score=round(score, 3),
                breakdown=details if details else {"task_match": round(score, 3)},
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
        session_id: Optional[str] = None,
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

        # Session support — inject conversation history
        session = None
        if session_id:
            sm = get_session_manager()
            session = sm.get_or_create(session_id, project=self.project_name)
            session.add_user_turn(prompt)
            session_context = session.get_context_block()
            if session_context:
                context = f"{session_context}\n{context}" if context else session_context
                collaboration_log.append(f"Session {session_id}: injected {session.turn_count} turns of history")

        # Intelligence visibility dict — captures everything happening behind the scenes
        intel = {
            "routing": {},
            "memory": {"patterns_injected": 0, "patterns": [], "prevention_applied": False},
            "agents": [],
            "consensus": {},
            "learning": {},
            "cost": {"total": 0.0, "breakdown": []},
        }

        # Auto-benchmark check (once per session, non-blocking)
        if not self._benchmark_checked:
            self._benchmark_checked = True
            asyncio.ensure_future(self._auto_benchmark_if_stale())

        # Use task router for intelligent agent selection and mode
        classification = self._task_router.classify(prompt, context)
        collaboration_log.append(
            f"Task classified: {classification.primary_type.value} "
            f"(complexity: {classification.complexity}, confidence: {classification.confidence:.2f})"
        )
        intel["routing"]["task_type"] = classification.primary_type.value
        intel["routing"]["complexity"] = classification.complexity
        intel["routing"]["classification_confidence"] = round(classification.confidence, 2)

        # Apple Silicon optimization: use smart router for local vs cloud decision
        prefer_local_models = False
        if self._apple_router and self._apple_router.hardware:
            # Map task types to smart router task types
            apple_task_type = {
                "code_review": "code_review",
                "code_generation": "code_generation",
                "debugging": "debug_error",
                "documentation": "docstring",
                "testing": "write_test",
                "architecture": "architecture",
                "security": "security_audit",
            }.get(classification.primary_type.value, "code_generation")

            routing_decision = self._apple_router.route(
                task_type=apple_task_type,
                prompt_length=len(prompt) + len(context or ""),
            )
            # Only prefer local models for truly simple/fast tasks
            # For medium+ tasks, let cloud agents participate for better quality
            prefer_local_models = (
                routing_decision.tier.value == "local_fast"
                and classification.complexity == "low"
            )
            collaboration_log.append(
                f"Apple router: {routing_decision.tier.value} ({routing_decision.reason}), "
                f"local_only={prefer_local_models}"
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

            # Apple Silicon optimization: only use local agents for simple tasks
            if prefer_local_models and available:
                local_agents = [a for a in available if 'ollama' in a.lower() or 'local' in a.lower()]
                if local_agents:
                    available = local_agents
                    collaboration_log.append(f"Simple task: using local agents only {local_agents}")
            else:
                # For non-trivial tasks, prefer cloud agents for quality
                cloud_agents = [a for a in available if 'local' not in a.lower() and 'ollama' not in a.lower()]
                if cloud_agents:
                    available = cloud_agents
                    collaboration_log.append(f"Using cloud agents for quality: {cloud_agents}")

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
                intel["routing"]["selection_method"] = "performance-enhanced"
                intel["routing"]["scores"] = [
                    {"agent": n, "score": round(s, 3)} for n, s, _ in ranked[:5]
                ]
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

        intel["routing"]["selected_agents"] = agents
        intel["routing"]["mode"] = mode

        # Get prevention context from memory system
        enhanced_prompt = prompt
        task_type = classification.primary_type.value

        # Only inject context for tasks that benefit from it (not simple questions)
        _context_tasks = {"coding", "debugging", "testing", "optimization", "architecture", "security"}
        _needs_context = task_type in _context_tasks and classification.complexity != "low"

        if _needs_context and self._prevention:
            prevention_context = await self._prevention.get_prevention_context(
                task_type, self.project_name
            )
            if prevention_context:
                enhanced_prompt = f"{prevention_context}\n\n{prompt}"
                collaboration_log.append("Applied prevention context from past mistakes")
                intel["memory"]["prevention_applied"] = True
                intel["memory"]["prevention_summary"] = prevention_context[:200]

        # Auto-inject relevant solution patterns from memory
        if _needs_context and self._memory_system:
            try:
                # Two-pass search: (1) prompt-specific, (2) project-wide conventions
                solutions = await self._memory_system.find_solution_patterns(prompt[:200], limit=6)
                project_solutions = await self._memory_system.find_solution_patterns(
                    self.project_name, limit=6
                )
                # Merge and deduplicate by solution_id
                seen_ids = set()
                all_solutions = []
                for s in solutions + project_solutions:
                    if s.solution_id not in seen_ids:
                        seen_ids.add(s.solution_id)
                        all_solutions.append(s)
                # Prefer solutions with explicit best_practices (hand-curated patterns)
                # over auto-captured interaction results (which have empty best_practices)
                curated = [s for s in all_solutions if s.best_practices]
                auto = [s for s in all_solutions if not s.best_practices]
                # Take up to 3 curated, fill remainder with auto
                selected = curated[:3] + auto[:max(0, 3 - len(curated))]
                if selected:
                    solution_lines = ["MANDATORY PROJECT CONVENTIONS — You MUST follow these rules:"]
                    for sol in selected:
                        solution_lines.append(f"\n## {sol.problem_pattern}")
                        for step in sol.solution_steps:
                            # Skip overly long auto-captured steps (full AI responses)
                            if len(step) > 200:
                                continue
                            solution_lines.append(f"  - {step}")
                        if sol.best_practices:
                            solution_lines.append("  REQUIREMENTS (do not ignore):")
                            for bp in sol.best_practices:
                                solution_lines.append(f"    * {bp}")
                    solution_context = "\n".join(solution_lines)
                    # Cap to prevent prompt bloat
                    if len(solution_context) > 3000:
                        solution_context = solution_context[:3000] + "\n..."
                    enhanced_prompt = f"{solution_context}\n\n{enhanced_prompt}"
                    collaboration_log.append(f"Injected {len(selected)} solution patterns from memory ({len(curated)} curated)")
                    # Track which solutions were injected for this task (for feedback loop)
                    self._memory_system.track_injection(
                        task_id, [s.solution_id for s in selected]
                    )
                    # Capture memory intelligence
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

        # Live codebase awareness: auto-index project if path is available
        if _needs_context and self._rag and self.project_name != "default":
            try:
                from .project_context import ProjectContextManager
                pctx = ProjectContextManager()
                profile = pctx.get_profile(self.project_name)
                if profile and profile.project_path:
                    indexed = self._rag.index_project_if_stale(
                        project_name=self.project_name,
                        project_path=profile.project_path,
                    )
                    if indexed:
                        collaboration_log.append(f"Auto-indexed project '{self.project_name}' for RAG")
            except Exception as e:
                logger.debug(f"Auto-index skipped: {e}")

        # Add domain knowledge context (only for complex/relevant tasks)
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

        if _needs_context:
            # Get built-in domain knowledge
            domain_context = get_domain_context(relevant_domains)

            # Get custom teaching knowledge
            teaching_context = self._teaching_system.generate_teaching_context(
                domains=relevant_domains, topics=[task_type]
            )

            if domain_context or teaching_context:
                knowledge_context = "\n".join(filter(None, [domain_context, teaching_context]))
                # Cap context to prevent prompt bloat
                if len(knowledge_context) > 2000:
                    knowledge_context = knowledge_context[:2000] + "\n..."
                enhanced_prompt = f"DOMAIN EXPERTISE:\n{knowledge_context}\n\nTASK:\n{enhanced_prompt}"
                collaboration_log.append(f"Applied domain knowledge: {', '.join(relevant_domains)}")

            # Add coding knowledge hub context (only for code-related tasks)
            if task_type in ["coding", "debugging"]:
                coding_context = self._coding_hub.generate_coding_context(
                    task_description=prompt,
                    language=None,
                    framework=None,
                    max_items=2,
                )
                if coding_context and len(coding_context) <= 1500:
                    enhanced_prompt = f"{coding_context}\n\n{enhanced_prompt}"
                    collaboration_log.append("Applied coding knowledge hub context")

            # Add RAG context (only for complex tasks, capped)
            if classification.complexity in ("medium", "high"):
                try:
                    rag_context = self._rag.get_context_for_task(
                        task_description=prompt,
                        max_results=3,
                        max_tokens=800,
                    )
                    if rag_context.results:
                        enhanced_prompt = f"{rag_context.context_text}\n\n{enhanced_prompt}"
                        collaboration_log.append(f"Applied RAG context ({len(rag_context.results)} sources)")
                except Exception as e:
                    logger.debug(f"RAG context retrieval skipped: {e}")
        else:
            collaboration_log.append(f"Skipped context injection (task_type={task_type}, complexity={classification.complexity})")

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
            # Smart routing: use single agent for low complexity tasks
            if mode == "auto" or mode == "smart":
                if classification.complexity == "low":
                    mode = "single"
                    collaboration_log.append("Auto-routing: simple task → single agent")
                else:
                    mode = "parallel"
                    collaboration_log.append(f"Auto-routing: {classification.complexity} task → parallel")

            if mode == "single":
                # Use only the best agent (first in sorted list)
                best_agent = active_agents[0]
                collaboration_log.append(f"Single-agent mode: using {best_agent.name}")
                response = await best_agent.generate_response(enhanced_prompt, context)
                agent_responses = [response]
            elif mode == "fast":
                # Fast mode: use only first agent, no synthesis
                best_agent = active_agents[0]
                collaboration_log.append(f"Fast mode: using {best_agent.name}")
                response = await best_agent.generate_response(enhanced_prompt, context)
                agent_responses = [response]
            elif mode == "parallel":
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

            # Build agent perspectives for intelligence report
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

            # Detect agreement/disagreement among agents
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
                    # Identify the outlier
                    for r in successful_responses:
                        if abs(r.confidence - avg_confidence) > 0.2:
                            intel["consensus"].setdefault("divergent_agents", []).append(r.agent_name)
            elif len(successful_responses) == 1:
                intel["consensus"]["level"] = "single-agent"
                intel["consensus"]["description"] = "Only one agent responded"

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
                intelligence=intel,
            )

            # Save team response to session
            if session:
                session.add_team_turn(
                    content=final_answer[:2000],
                    agents=result.participating_agents,
                    task_type=task_type,
                    confidence=avg_confidence,
                    task_id=task_id,
                )
                sm = get_session_manager()
                sm.save(session)
                intel["session"] = {
                    "id": session_id,
                    "turns": session.turn_count,
                    "has_summary": bool(session.summary),
                }

            # Store in memory and learn from outcome
            if self.enable_memory and self._memory_system:
                await self._memory_system.capture_interaction(result, self.project_name)

                # Learn from successful outcomes — use cheapest agent to extract patterns
                if self.enable_learning and self._learning_engine and result.success:
                    extractor = None
                    for pref in ["gemini-creative", "ollama-local", "chatgpt-coder"]:
                        if pref in self.agents:
                            extractor = self.agents[pref]
                            break
                    learn_result = await self._learning_engine.learn_from_success(
                        result, prompt, self.project_name,
                        extractor_agent=extractor,
                    )
                    # Capture learning outcomes for intelligence report
                    if learn_result and isinstance(learn_result, dict):
                        intel["learning"]["patterns_extracted"] = len(learn_result.get("solution_steps", []))
                        intel["learning"]["tags"] = learn_result.get("tags", [])
                    elif learn_result:
                        intel["learning"]["stored"] = True
                    mem_stats = self._memory_system.get_statistics() if self._memory_system else {}
                    intel["learning"]["total_patterns"] = mem_stats.get("total_solutions", 0)

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
            # Only store actual code blocks, not conversational responses
            if result.success and task_type in ["coding", "debugging"]:
                import re
                code_blocks = re.findall(r'```(\w+)?\n(.*?)```', final_answer, re.DOTALL)
                for lang, code in code_blocks:
                    code_stripped = code.strip()
                    # Only store substantial code with actual code-like content
                    if (code_stripped
                            and len(code_stripped) > 100
                            and lang  # Must have a language tag
                            and any(kw in code_stripped for kw in ['def ', 'class ', 'import ', 'function ', 'const ', 'return ', 'async '])):
                        self._coding_hub.learn_from_successful_code(
                            code=code_stripped,
                            language=lang,
                            task_description=prompt[:100],
                        )
                        collaboration_log.append(f"Learned code snippet to hub ({lang})")

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

            # Record costs for each agent response
            if self._cost_tracker:
                total_cost = 0.0
                for response in successful_responses:
                    if response.input_tokens or response.output_tokens:
                        model_name = response.metadata.get("model", "") or response.agent_name
                        estimate = self._cost_tracker.record_usage(
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

            # Record session learning outcomes and persist
            if self.enable_session_learning and self._session_learner:
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
                    self._session_learner.record_outcome(outcome)
                # Auto-save learning data
                self._session_learner.save()
                collaboration_log.append(f"Session learning updated and saved")

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

    async def stream_collaborate(
        self,
        prompt: str,
        context: str = "",
        agents: Optional[List[str]] = None,
        session_id: Optional[str] = None,
    ):
        """
        Streaming collaboration — yields agent responses as they arrive.

        Yields dicts with:
            {"type": "agent_start", "agent": name}
            {"type": "agent_chunk", "agent": name, "text": chunk}
            {"type": "agent_done", "agent": name, "time": seconds}
            {"type": "synthesis", "text": final_answer}
            {"type": "intelligence", "report": intel_dict}

        Usage:
            async for event in team.stream_collaborate("Review this code"):
                if event["type"] == "agent_chunk":
                    print(event["text"], end="", flush=True)
        """
        # Use task router to select agents
        classification = self._task_router.classify(prompt, context)
        task_type = classification.primary_type.value

        if not agents:
            available = [n for n in self.agents.keys()
                         if 'local' not in n.lower() and 'ollama' not in n.lower()]
            if not available:
                available = list(self.agents.keys())
            agents = available[:3]

        active_agents = [self.agents[n] for n in agents if n in self.agents]
        if not active_agents:
            yield {"type": "error", "text": "No agents available"}
            return

        # Session support
        if session_id:
            sm = get_session_manager()
            session = sm.get_or_create(session_id, project=self.project_name)
            session.add_user_turn(prompt)
            session_context = session.get_context_block()
            if session_context:
                context = f"{session_context}\n{context}" if context else session_context

        yield {"type": "start", "agents": [a.name for a in active_agents], "task_type": task_type}

        # Stream responses from all agents concurrently
        import time as _time
        agent_contents = {}

        async def stream_agent(agent):
            agent_contents[agent.name] = []
            yield_start = {"type": "agent_start", "agent": agent.name}
            start = _time.time()
            try:
                async for chunk in agent.generate_stream(prompt, context):
                    agent_contents[agent.name].append(chunk)
                    yield {"type": "agent_chunk", "agent": agent.name, "text": chunk}
            except Exception as e:
                yield {"type": "agent_error", "agent": agent.name, "error": str(e)}
            elapsed = _time.time() - start
            yield {"type": "agent_done", "agent": agent.name, "time": round(elapsed, 2)}

        # Run all streams concurrently using asyncio.Queue
        queue = asyncio.Queue()

        async def stream_to_queue(agent):
            await queue.put({"type": "agent_start", "agent": agent.name})
            start = _time.time()
            try:
                async for chunk in agent.generate_stream(prompt, context):
                    agent_contents[agent.name] = agent_contents.get(agent.name, "") + chunk
                    await queue.put({"type": "agent_chunk", "agent": agent.name, "text": chunk})
            except Exception as e:
                await queue.put({"type": "agent_error", "agent": agent.name, "error": str(e)})
            elapsed = _time.time() - start
            await queue.put({"type": "agent_done", "agent": agent.name, "time": round(elapsed, 2)})

        async def run_all():
            tasks = [stream_to_queue(a) for a in active_agents]
            await asyncio.gather(*tasks)
            await queue.put(None)  # Sentinel

        asyncio.ensure_future(run_all())

        while True:
            event = await queue.get()
            if event is None:
                break
            yield event

        # Synthesize
        all_content = "\n\n".join(
            f"[{name}]: {content}" for name, content in agent_contents.items() if content
        )
        if all_content:
            yield {"type": "synthesis_start"}
            # Use first agent to synthesize
            synth_prompt = f"Synthesize these perspectives into one answer:\n{all_content[:6000]}\n\nOriginal task: {prompt}"
            synth_agent = active_agents[0]
            async for chunk in synth_agent.generate_stream(synth_prompt, ""):
                yield {"type": "synthesis_chunk", "text": chunk}
            yield {"type": "synthesis_done"}

        # Save to session if applicable
        if session_id:
            full_content = "".join(str(v) for v in agent_contents.values())
            session.add_team_turn(
                content=full_content[:2000],
                agents=[a.name for a in active_agents],
                task_type=task_type,
            )
            sm.save(session)

        yield {"type": "done"}

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

        # Use the best available agent for synthesis
        synthesis_agent = None
        preferred_patterns = [
            "claude-analyst", "claude", "anthropic",
            "chatgpt", "openai", "gpt",
            "grok-reasoner", "grok",
            "gemini",
        ]
        for pattern in preferred_patterns:
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

        # Gather project conventions for the synthesizer
        conventions_block = ""
        if self._memory_system:
            try:
                curated = await self._memory_system.find_solution_patterns(prompt[:100], limit=3)
                curated = [s for s in curated if s.best_practices]
                if curated:
                    rules = []
                    for s in curated[:2]:
                        rules.extend(s.best_practices)
                    if rules:
                        conventions_block = "\nProject conventions to enforce in the synthesis:\n" + "\n".join(f"- {r}" for r in rules[:8]) + "\n"
            except Exception:
                pass

        synthesis_prompt = f"""Synthesize these AI team responses into one comprehensive answer.
Combine the best insights from each response. Be concise but complete.
{conventions_block}
Original Task: {prompt}

Team Responses:
{responses_text}

Provide a unified, synthesized response that follows all project conventions listed above:"""

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

            # Fallback to best available agent
            if not selected_agent:
                for pattern in ["claude", "chatgpt", "gpt", "grok-reasoner", "grok", "gemini"]:
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

        # Add cost tracking stats (from persistent CostTracker)
        if self._cost_tracker:
            status["costs"] = self._cost_tracker.get_statistics()

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

    async def _auto_benchmark_if_stale(self):
        """Run benchmarks in the background if routing table is stale or missing."""
        try:
            from .routing.benchmark import BenchmarkRunner, STORAGE_DIR
            table_path = STORAGE_DIR / "routing_table.json"

            # Skip if benchmarked within the last 7 days
            if table_path.exists():
                import json
                table = json.loads(table_path.read_text())
                for task_type, data in table.items():
                    updated = data.get("updated", "")
                    if updated:
                        from datetime import datetime, timezone, timedelta
                        try:
                            last_update = datetime.fromisoformat(updated)
                            if datetime.now(timezone.utc) - last_update < timedelta(days=7):
                                logger.debug("Benchmark data is fresh, skipping auto-benchmark")
                                # Reload into router
                                self._task_router._benchmark_data = self._task_router._load_benchmark_data()
                                return
                        except Exception:
                            pass

            # Run a quick benchmark (coding only — most common task type)
            if len(self.agents) < 2:
                return

            logger.info("Running auto-benchmark (coding) in background...")
            runner = BenchmarkRunner(self)
            suite = await runner.run_benchmark("coding")
            logger.info(f"Auto-benchmark complete: {suite.agent_rankings}")

            # Reload benchmark data into router
            self._task_router._benchmark_data = self._task_router._load_benchmark_data()

        except Exception as e:
            logger.debug(f"Auto-benchmark skipped: {e}")

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

    # ==========================
    # Autonomous AI Capabilities (delegated to AutonomousExecutor)
    # ==========================

    async def _decompose_analyze(self, prompt: str) -> str:
        """Helper for task decomposition - uses quick agent for analysis."""
        agent = self.get_agent("local-llama3") or self.get_agent("chatgpt")
        if agent:
            response = await agent.generate_response(prompt)
            return response.content
        return ""

    async def auto_collaborate(self, goal, context=None, enable_correction=True, enable_decomposition=True, on_progress=None):
        """Fully autonomous collaboration. Delegates to AutonomousExecutor."""
        return await self.autonomous_executor.auto_collaborate(goal, context, enable_correction, enable_decomposition, on_progress)

    async def build(self, description, context=None, on_progress=None):
        """High-level autonomous build command. Delegates to AutonomousExecutor."""
        return await self.autonomous_executor.build(description, context, on_progress)

    def get_autonomous_stats(self):
        """Get statistics on autonomous features."""
        return self.autonomous_executor.get_autonomous_stats()

    def get_best_agent_for(self, task_type):
        """Get the best agent for a specific task type based on session learning."""
        return self.autonomous_executor.get_best_agent_for(task_type)

    # =================
    # Tool Access Methods (delegated to ToolManager)
    # =================

    def get_tools(self):
        """Get all available tools."""
        return self.tool_manager.get_tools()

    def get_tool_capabilities(self):
        """Get capabilities of all registered tools."""
        return self.tool_manager.get_tool_capabilities()

    async def execute_tool(self, tool_name, operation, **kwargs):
        """Execute a tool operation."""
        return await self.tool_manager.execute_tool(tool_name, operation, **kwargs)

    def grant_tool_permission(self, tool_name, operation, level="session"):
        """Grant permission for a tool operation."""
        self.tool_manager.grant_tool_permission(tool_name, operation, level)

    def revoke_tool_permission(self, tool_name, operation):
        """Revoke permission for a tool operation."""
        self.tool_manager.revoke_tool_permission(tool_name, operation)

    def list_tool_permissions(self):
        """List all granted tool permissions."""
        return self.tool_manager.list_tool_permissions()

    async def agentic_task(self, task, allowed_tools=None, max_tool_calls=10, agent_name=None):
        """Execute a task where the AI agent can autonomously use tools."""
        return await self.tool_manager.agentic_task(task, allowed_tools, max_tool_calls, agent_name)

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
    # Advanced Agent Framework (delegated to FrameworkFacade)
    # =================

    async def react(self, task, max_steps=10, verbose=False):
        """Execute a task using ReAct (Reasoning + Acting) pattern."""
        return await self.framework_facade.react(task, max_steps, verbose)

    async def plan_and_execute(self, goal, context="", available_tools=None):
        """Create and execute a multi-step plan for achieving a goal."""
        return await self.framework_facade.plan_and_execute(goal, context, available_tools)

    async def reason(self, problem, method="zero_shot", verify=False):
        """Apply chain-of-thought reasoning to a problem."""
        return await self.framework_facade.reason(problem, method, verify)

    def get_context_manager(self, max_tokens=8000):
        """Get a context manager for managing conversation history."""
        return self.framework_facade.get_context_manager(max_tokens)

    def get_framework_tools(self):
        """Get list of available framework tools."""
        return self.framework_facade.get_framework_tools()

    def get_framework_tool_schemas(self, format="openai"):
        """Get tool schemas for API integration."""
        return self.framework_facade.get_framework_tool_schemas(format)


# Convenience function for quick setup
def create_team(project_name: str = "default", **kwargs) -> AIDevTeam:
    """Create and configure an AI development team"""
    return AIDevTeam(project_name=project_name, **kwargs)
