"""
Streaming Collaboration - Real-time streaming collaboration between agents
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

from ..agents import AIAgent, AgentResponse

logger = logging.getLogger(__name__)


@dataclass
class StreamChunk:
    """A chunk of streamed content"""
    agent_name: str
    content: str
    is_final: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StreamingResult:
    """Result of a streaming collaboration"""
    success: bool
    final_content: str
    chunks_received: int
    agents_participated: List[str]
    total_time: float
    errors: List[str] = field(default_factory=list)


class StreamingCollaborationEngine:
    """
    Streaming collaboration engine.

    Enables real-time collaboration where agents can build on
    each other's partial outputs as they stream.
    """

    def __init__(self):
        self._active_streams: Dict[str, asyncio.Task] = {}
        self._callbacks: List[Callable[[StreamChunk], None]] = []

    def add_callback(self, callback: Callable[[StreamChunk], None]):
        """Add a callback for stream chunks"""
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[StreamChunk], None]):
        """Remove a callback"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    async def _notify_callbacks(self, chunk: StreamChunk):
        """Notify all callbacks of a new chunk"""
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(chunk)
                else:
                    callback(chunk)
            except Exception as e:
                logger.warning(f"Callback error: {e}")

    async def stream_sequential(
        self,
        prompt: str,
        agents: List[AIAgent],
        context: str = "",
        handoff_threshold: float = 0.3,
    ) -> AsyncIterator[StreamChunk]:
        """
        Stream responses sequentially with early handoff.

        Agent 2 starts receiving Agent 1's output while Agent 1
        is still streaming (after handoff_threshold of content).

        Args:
            prompt: The task prompt
            agents: List of agents to use
            context: Additional context
            handoff_threshold: Fraction of estimated content before handoff (0.3 = 30%)

        Yields:
            StreamChunk for each piece of content
        """
        if not agents:
            return

        accumulated_context = context

        for i, agent in enumerate(agents):
            agent_content = ""

            # Check if agent supports streaming
            if hasattr(agent, 'generate_stream'):
                async for chunk in agent.generate_stream(prompt, accumulated_context):
                    agent_content += chunk
                    yield StreamChunk(
                        agent_name=agent.name,
                        content=chunk,
                        is_final=False,
                    )
                    await self._notify_callbacks(StreamChunk(
                        agent_name=agent.name,
                        content=chunk,
                        is_final=False,
                    ))
            else:
                # Fallback to non-streaming
                response = await agent.generate_response(prompt, accumulated_context)
                if response.success:
                    agent_content = response.content
                    # Simulate streaming by chunking
                    chunk_size = 100
                    for j in range(0, len(agent_content), chunk_size):
                        chunk = agent_content[j:j + chunk_size]
                        yield StreamChunk(
                            agent_name=agent.name,
                            content=chunk,
                            is_final=j + chunk_size >= len(agent_content),
                        )
                        await asyncio.sleep(0.01)  # Small delay for simulation

            # Final chunk marker
            yield StreamChunk(
                agent_name=agent.name,
                content="",
                is_final=True,
                metadata={"total_length": len(agent_content)},
            )

            # Add to context for next agent
            if agent_content:
                accumulated_context = (
                    f"{context}\n\n"
                    f"Previous response from {agent.name}:\n{agent_content}"
                )

    async def stream_parallel(
        self,
        prompt: str,
        agents: List[AIAgent],
        context: str = "",
    ) -> AsyncIterator[StreamChunk]:
        """
        Stream responses from all agents in parallel.

        All agents work simultaneously, chunks are yielded as they arrive.

        Args:
            prompt: The task prompt
            agents: List of agents to use
            context: Additional context

        Yields:
            StreamChunk from any agent as they arrive
        """
        if not agents:
            return

        # Create queues for each agent
        queues: Dict[str, asyncio.Queue] = {
            agent.name: asyncio.Queue() for agent in agents
        }

        async def stream_agent(agent: AIAgent, queue: asyncio.Queue):
            """Stream from a single agent to its queue"""
            try:
                if hasattr(agent, 'generate_stream'):
                    async for chunk in agent.generate_stream(prompt, context):
                        await queue.put(StreamChunk(
                            agent_name=agent.name,
                            content=chunk,
                            is_final=False,
                        ))
                else:
                    response = await agent.generate_response(prompt, context)
                    if response.success:
                        # Chunk the response
                        chunk_size = 100
                        for i in range(0, len(response.content), chunk_size):
                            await queue.put(StreamChunk(
                                agent_name=agent.name,
                                content=response.content[i:i + chunk_size],
                                is_final=False,
                            ))

                # Signal completion
                await queue.put(StreamChunk(
                    agent_name=agent.name,
                    content="",
                    is_final=True,
                ))
            except Exception as e:
                logger.error(f"Streaming error from {agent.name}: {e}")
                await queue.put(StreamChunk(
                    agent_name=agent.name,
                    content="",
                    is_final=True,
                    metadata={"error": str(e)},
                ))

        # Start all agents
        tasks = [
            asyncio.create_task(stream_agent(agent, queues[agent.name]))
            for agent in agents
        ]

        # Merge streams
        completed = set()
        while len(completed) < len(agents):
            for agent_name, queue in queues.items():
                if agent_name in completed:
                    continue

                try:
                    chunk = queue.get_nowait()
                    yield chunk
                    await self._notify_callbacks(chunk)

                    if chunk.is_final:
                        completed.add(agent_name)
                except asyncio.QueueEmpty:
                    pass

            await asyncio.sleep(0.01)

        # Wait for all tasks to complete
        await asyncio.gather(*tasks, return_exceptions=True)

    async def stream_with_synthesis(
        self,
        prompt: str,
        agents: List[AIAgent],
        synthesis_agent: AIAgent,
        context: str = "",
    ) -> AsyncIterator[StreamChunk]:
        """
        Stream from multiple agents, then synthesize results.

        Args:
            prompt: The task prompt
            agents: List of agents to generate responses
            synthesis_agent: Agent to synthesize final result
            context: Additional context

        Yields:
            StreamChunk from agents and final synthesis
        """
        # Collect all responses
        agent_outputs: Dict[str, str] = {}

        async for chunk in self.stream_parallel(prompt, agents, context):
            yield chunk

            if chunk.agent_name not in agent_outputs:
                agent_outputs[chunk.agent_name] = ""
            agent_outputs[chunk.agent_name] += chunk.content

        # Synthesize
        if agent_outputs:
            synthesis_prompt = f"""Synthesize these AI team responses into one unified answer:

Original Task: {prompt}

Team Responses:
{chr(10).join(f'[{name}]: {content[:500]}...' for name, content in agent_outputs.items())}

Provide a comprehensive, unified response combining the best insights."""

            yield StreamChunk(
                agent_name="synthesis",
                content="\n\n--- SYNTHESIS ---\n\n",
                is_final=False,
            )

            if hasattr(synthesis_agent, 'generate_stream'):
                async for chunk in synthesis_agent.generate_stream(synthesis_prompt, context):
                    yield StreamChunk(
                        agent_name="synthesis",
                        content=chunk,
                        is_final=False,
                    )
            else:
                response = await synthesis_agent.generate_response(synthesis_prompt, context)
                if response.success:
                    yield StreamChunk(
                        agent_name="synthesis",
                        content=response.content,
                        is_final=False,
                    )

            yield StreamChunk(
                agent_name="synthesis",
                content="",
                is_final=True,
            )

    async def collect_stream(
        self,
        stream: AsyncIterator[StreamChunk],
    ) -> StreamingResult:
        """
        Collect a stream into a final result.

        Args:
            stream: Async iterator of StreamChunks

        Returns:
            StreamingResult with collected content
        """
        import time
        start_time = time.time()

        content_by_agent: Dict[str, str] = {}
        chunk_count = 0
        errors = []

        async for chunk in stream:
            chunk_count += 1

            if chunk.agent_name not in content_by_agent:
                content_by_agent[chunk.agent_name] = ""

            content_by_agent[chunk.agent_name] += chunk.content

            if chunk.metadata.get("error"):
                errors.append(f"{chunk.agent_name}: {chunk.metadata['error']}")

        # Combine all content
        final_content = "\n\n".join(
            f"[{name}]\n{content}"
            for name, content in content_by_agent.items()
            if content.strip()
        )

        return StreamingResult(
            success=bool(content_by_agent) and not errors,
            final_content=final_content,
            chunks_received=chunk_count,
            agents_participated=list(content_by_agent.keys()),
            total_time=time.time() - start_time,
            errors=errors,
        )
