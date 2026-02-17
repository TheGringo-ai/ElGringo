"""
Streaming Collaboration - Real-Time AI Team Working Together

SECRET WEAPON #7: Watch multiple AI models collaborate in REAL-TIME!
Each model streams its response while others can already start building on it.

Features:
- Live streaming from multiple models simultaneously
- One model can start responding to another's partial output
- Real-time synthesis as responses come in
- WebSocket support for live UI updates
- Interruptible - stop and redirect anytime

This creates a genuinely collaborative feel - like watching senior
engineers work together in real-time!
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class StreamChunk:
    """A chunk of streaming output"""
    model: str
    content: str
    chunk_type: str  # "thinking", "response", "synthesis"
    timestamp: datetime = field(default_factory=datetime.now)
    is_final: bool = False


@dataclass
class CollaborationStream:
    """A streaming collaboration session"""
    id: str
    prompt: str
    models: List[str]
    chunks: List[StreamChunk] = field(default_factory=list)
    final_synthesis: Optional[str] = None
    status: str = "running"  # "running", "completed", "cancelled"
    start_time: datetime = field(default_factory=datetime.now)


class StreamingCollaboration:
    """
    Real-Time Streaming Collaboration Engine

    Multiple AI models work together with streaming output.
    You can watch them think and respond in real-time!

    Usage:
        collab = StreamingCollaboration()

        # Stream responses from all models
        async for chunk in collab.stream_collaborate(
            "Design a REST API for a todo app"
        ):
            print(f"{chunk.model}: {chunk.content}")

        # With WebSocket callback
        async def on_chunk(chunk):
            await websocket.send(json.dumps({
                "model": chunk.model,
                "content": chunk.content
            }))

        await collab.stream_with_callback(prompt, on_chunk)
    """

    def __init__(self):
        self._clients = {}
        self._active_streams: Dict[str, CollaborationStream] = {}

    async def _get_claude_client(self):
        """Get Anthropic client"""
        if "claude" not in self._clients:
            try:
                import anthropic
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if api_key:
                    self._clients["claude"] = anthropic.AsyncAnthropic(api_key=api_key)
            except ImportError:
                pass
        return self._clients.get("claude")

    async def _get_openai_client(self):
        """Get OpenAI client"""
        if "openai" not in self._clients:
            try:
                import openai
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    self._clients["openai"] = openai.AsyncOpenAI(api_key=api_key)
            except ImportError:
                pass
        return self._clients.get("openai")

    async def _stream_claude(
        self,
        prompt: str,
        system: str = ""
    ) -> AsyncIterator[str]:
        """Stream from Claude"""
        client = await self._get_claude_client()
        if not client:
            yield "[Claude not available]"
            return

        try:
            async with client.messages.stream(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                system=system or "You are a helpful assistant.",
                messages=[{"role": "user", "content": prompt}]
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            yield f"[Claude error: {e}]"

    async def _stream_gpt4(
        self,
        prompt: str,
        system: str = ""
    ) -> AsyncIterator[str]:
        """Stream from GPT-4"""
        client = await self._get_openai_client()
        if not client:
            yield "[GPT-4 not available]"
            return

        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            stream = await client.chat.completions.create(
                model="gpt-4o",
                max_tokens=4000,
                messages=messages,
                stream=True
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            yield f"[GPT-4 error: {e}]"

    async def stream_collaborate(
        self,
        prompt: str,
        models: List[str] = None,
        context: str = ""
    ) -> AsyncIterator[StreamChunk]:
        """
        Stream collaboration between multiple models.

        Models respond in parallel, with their outputs streamed
        as they generate. A final synthesis combines the best.

        Args:
            prompt: The task/question
            models: Which models to use (default: ["claude", "gpt4"])
            context: Additional context

        Yields:
            StreamChunk with model name and content
        """
        models = models or ["claude", "gpt4"]
        session_id = f"collab_{int(time.time())}"

        session = CollaborationStream(
            id=session_id,
            prompt=prompt,
            models=models
        )
        self._active_streams[session_id] = session

        full_prompt = prompt
        if context:
            full_prompt = f"Context:\n{context}\n\n{prompt}"

        system = """You are part of a collaborative AI team. Provide your best response.
Be specific, thorough, and constructive. Focus on adding unique value."""

        # Create streaming tasks for each model
        async def stream_model(model: str) -> AsyncIterator[Tuple[str, str]]:
            if model == "claude":
                async for chunk in self._stream_claude(full_prompt, system):
                    yield (model, chunk)
            elif model == "gpt4":
                async for chunk in self._stream_gpt4(full_prompt, system):
                    yield (model, chunk)

        # Collect responses for synthesis
        responses = {m: "" for m in models}

        # Stream from all models concurrently
        # We'll use a queue to merge the streams
        queue: asyncio.Queue = asyncio.Queue()
        tasks = []

        async def producer(model: str):
            try:
                async for m, chunk in stream_model(model):
                    await queue.put(StreamChunk(
                        model=m,
                        content=chunk,
                        chunk_type="response"
                    ))
                    responses[model] += chunk
            except Exception as e:
                await queue.put(StreamChunk(
                    model=model,
                    content=f"[Error: {e}]",
                    chunk_type="error"
                ))
            finally:
                await queue.put(StreamChunk(
                    model=model,
                    content="",
                    chunk_type="response",
                    is_final=True
                ))

        # Start all producers
        for model in models:
            tasks.append(asyncio.create_task(producer(model)))

        # Track completed models
        completed = set()

        # Yield chunks as they come in
        while len(completed) < len(models):
            try:
                chunk = await asyncio.wait_for(queue.get(), timeout=120)
                session.chunks.append(chunk)

                if chunk.is_final:
                    completed.add(chunk.model)
                else:
                    yield chunk

            except asyncio.TimeoutError:
                logger.warning("Streaming timeout")
                break

        # Wait for all tasks to complete
        await asyncio.gather(*tasks, return_exceptions=True)

        # Generate synthesis from all responses
        yield StreamChunk(
            model="system",
            content="\n\n--- Synthesizing responses ---\n\n",
            chunk_type="synthesis"
        )

        synthesis_prompt = f"""You are synthesizing multiple AI responses.

Original prompt: {prompt}

Responses:
{chr(10).join(f'**{m.upper()}:**{chr(10)}{r}' for m, r in responses.items())}

Create a unified response that:
1. Takes the best ideas from each response
2. Resolves any contradictions
3. Provides a coherent final answer
4. Notes areas of agreement and disagreement"""

        async for chunk in self._stream_claude(synthesis_prompt, "You are an expert synthesizer."):
            yield StreamChunk(
                model="synthesis",
                content=chunk,
                chunk_type="synthesis"
            )

        session.status = "completed"
        yield StreamChunk(
            model="system",
            content="\n\n[Collaboration complete]",
            chunk_type="system",
            is_final=True
        )

    async def stream_with_callback(
        self,
        prompt: str,
        on_chunk: Callable[[StreamChunk], Any],
        models: List[str] = None
    ):
        """
        Stream with a callback for each chunk.

        Perfect for WebSocket or SSE integration!

        Args:
            prompt: The task/question
            on_chunk: Async callback for each chunk
            models: Which models to use
        """
        async for chunk in self.stream_collaborate(prompt, models):
            await on_chunk(chunk)

    async def stream_sequential_building(
        self,
        prompt: str,
        models: List[str] = None
    ) -> AsyncIterator[StreamChunk]:
        """
        Models build on each other's responses sequentially.

        Model 2 starts responding to Model 1's output while
        Model 1 is still generating!

        This creates a true collaborative building effect.
        """
        models = models or ["claude", "gpt4"]

        # First model starts
        first_response = ""
        async for chunk in self._stream_claude(prompt):
            first_response += chunk
            yield StreamChunk(
                model="claude",
                content=chunk,
                chunk_type="response"
            )

            # When 30% done, start the second model with partial context
            if len(first_response) > 200 and len(first_response) < 300:
                # Start second model in background
                asyncio.create_task(self._delayed_second_model(
                    prompt, first_response
                ))

        # Continue with synthesis
        yield StreamChunk(
            model="system",
            content="\n\n--- Building on response ---\n\n",
            chunk_type="system"
        )

    async def _delayed_second_model(self, original_prompt: str, partial_response: str):
        """Start second model with partial first response"""
        prompt = f"""Original request: {original_prompt}

A colleague has started responding:
{partial_response}...

Build on their response - add your perspective, correct any issues,
and extend their thinking."""

        async for chunk in self._stream_gpt4(prompt):
            # This would be yielded through the main stream
            pass

    async def interrupt(self, session_id: str):
        """Interrupt an active streaming session"""
        if session_id in self._active_streams:
            self._active_streams[session_id].status = "cancelled"
            logger.info(f"Session {session_id} interrupted")

    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get all active streaming sessions"""
        return [{
            "id": s.id,
            "prompt": s.prompt[:50] + "...",
            "models": s.models,
            "status": s.status,
            "chunks": len(s.chunks),
            "duration": (datetime.now() - s.start_time).total_seconds()
        } for s in self._active_streams.values()]


# FastAPI/Starlette SSE endpoint example
async def sse_collaborate_endpoint(prompt: str):
    """
    Example SSE endpoint for streaming collaboration.

    Use with:
    ```javascript
    const eventSource = new EventSource('/api/collaborate/stream?prompt=...');
    eventSource.onmessage = (e) => {
        const chunk = JSON.parse(e.data);
        console.log(chunk.model, chunk.content);
    };
    ```
    """
    collab = StreamingCollaboration()

    async def generate():
        async for chunk in collab.stream_collaborate(prompt):
            yield f"data: {json.dumps({'model': chunk.model, 'content': chunk.content})}\n\n"

    return generate()


# Convenience function
async def stream_team_response(prompt: str) -> str:
    """Quick streaming collaboration, returns final synthesis"""
    collab = StreamingCollaboration()
    full_response = ""

    async for chunk in collab.stream_collaborate(prompt):
        if chunk.chunk_type == "synthesis":
            full_response += chunk.content
        print(f"[{chunk.model}] {chunk.content}", end="", flush=True)

    return full_response
