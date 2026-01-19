"""
Stream Manager
==============

Manages real-time streaming of AI responses and task progress using
Server-Sent Events (SSE).

Features:
- Token-by-token AI response streaming
- Task progress updates
- Collaboration event broadcasting
- Stream lifecycle management
"""

import asyncio
import json
import logging
import queue
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Generator, List, Optional, Set

logger = logging.getLogger(__name__)


class StreamType(Enum):
    """Types of streams"""
    AI_RESPONSE = "ai_response"  # Token-by-token AI output
    TASK_PROGRESS = "task_progress"  # Task completion progress
    COLLABORATION = "collaboration"  # Multi-agent collaboration events
    SYSTEM = "system"  # System notifications


@dataclass
class StreamEvent:
    """A single event in a stream"""
    event_type: str
    data: Dict[str, Any]
    stream_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    sequence: int = 0

    def to_sse(self) -> str:
        """Format as Server-Sent Event"""
        event_data = {
            'type': self.event_type,
            'data': self.data,
            'stream_id': self.stream_id,
            'timestamp': self.timestamp.isoformat(),
            'sequence': self.sequence,
        }
        return f"data: {json.dumps(event_data)}\n\n"

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result


class Stream:
    """Represents an active stream"""

    def __init__(self, stream_id: str, stream_type: StreamType, metadata: Optional[Dict] = None):
        self.stream_id = stream_id
        self.stream_type = stream_type
        self.metadata = metadata or {}
        self.created_at = datetime.now(timezone.utc)
        self.events: List[StreamEvent] = []
        self.event_queue: queue.Queue = queue.Queue()
        self.is_active = True
        self.sequence = 0
        self._subscribers: Set[str] = set()

    def add_event(self, event_type: str, data: Dict[str, Any]) -> StreamEvent:
        """Add an event to the stream"""
        self.sequence += 1
        event = StreamEvent(
            event_type=event_type,
            data=data,
            stream_id=self.stream_id,
            sequence=self.sequence,
        )
        self.events.append(event)
        self.event_queue.put(event)
        return event

    def complete(self, final_data: Optional[Dict] = None):
        """Mark the stream as complete"""
        if final_data:
            self.add_event('complete', final_data)
        else:
            self.add_event('complete', {'message': 'Stream completed'})
        self.is_active = False

    def error(self, error_message: str):
        """Mark the stream as errored"""
        self.add_event('error', {'error': error_message})
        self.is_active = False

    def get_events_generator(self, timeout: float = 60.0) -> Generator[StreamEvent, None, None]:
        """Generator that yields events as they arrive"""
        while self.is_active or not self.event_queue.empty():
            try:
                event = self.event_queue.get(timeout=1.0)
                yield event
            except queue.Empty:
                # Send heartbeat to keep connection alive
                yield StreamEvent(
                    event_type='heartbeat',
                    data={'timestamp': datetime.now(timezone.utc).isoformat()},
                    stream_id=self.stream_id,
                )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'stream_id': self.stream_id,
            'stream_type': self.stream_type.value,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'is_active': self.is_active,
            'event_count': len(self.events),
            'sequence': self.sequence,
        }


class StreamManager:
    """
    Manages all active streams and provides SSE endpoints
    """

    def __init__(self):
        self._streams: Dict[str, Stream] = {}
        self._lock = threading.Lock()

    def create_stream(
        self,
        stream_type: StreamType,
        metadata: Optional[Dict] = None,
    ) -> Stream:
        """Create a new stream"""
        stream_id = str(uuid.uuid4())[:12]
        stream = Stream(stream_id, stream_type, metadata)

        with self._lock:
            self._streams[stream_id] = stream

        logger.info(f"Created stream {stream_id} of type {stream_type.value}")
        return stream

    def get_stream(self, stream_id: str) -> Optional[Stream]:
        """Get a stream by ID"""
        return self._streams.get(stream_id)

    def close_stream(self, stream_id: str):
        """Close a stream"""
        stream = self._streams.get(stream_id)
        if stream:
            stream.is_active = False

    def emit_to_stream(
        self,
        stream_id: str,
        event_type: str,
        data: Dict[str, Any],
    ) -> bool:
        """Emit an event to a specific stream"""
        stream = self._streams.get(stream_id)
        if stream and stream.is_active:
            stream.add_event(event_type, data)
            return True
        return False

    def complete_stream(self, stream_id: str, final_data: Optional[Dict] = None):
        """Mark a stream as complete"""
        stream = self._streams.get(stream_id)
        if stream:
            stream.complete(final_data)

    def error_stream(self, stream_id: str, error_message: str):
        """Mark a stream as errored"""
        stream = self._streams.get(stream_id)
        if stream:
            stream.error(error_message)

    def get_active_streams(self) -> List[Dict[str, Any]]:
        """Get all active streams"""
        return [s.to_dict() for s in self._streams.values() if s.is_active]

    def get_stream_events_sse(
        self,
        stream_id: str,
        timeout: float = 60.0,
    ) -> Generator[str, None, None]:
        """
        Generator that yields SSE-formatted events for a stream

        Usage in Flask:
            @app.route('/stream/<stream_id>')
            def stream_events(stream_id):
                return Response(
                    stream_manager.get_stream_events_sse(stream_id),
                    mimetype='text/event-stream'
                )
        """
        stream = self._streams.get(stream_id)
        if not stream:
            yield f"data: {json.dumps({'error': 'Stream not found'})}\n\n"
            return

        for event in stream.get_events_generator(timeout):
            yield event.to_sse()

    def cleanup_old_streams(self, max_age_seconds: int = 3600):
        """Remove old inactive streams"""
        now = datetime.now(timezone.utc)
        to_remove = []

        with self._lock:
            for stream_id, stream in self._streams.items():
                if not stream.is_active:
                    age = (now - stream.created_at).total_seconds()
                    if age > max_age_seconds:
                        to_remove.append(stream_id)

            for stream_id in to_remove:
                del self._streams[stream_id]

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old streams")

    def get_statistics(self) -> Dict[str, Any]:
        """Get stream statistics"""
        active = sum(1 for s in self._streams.values() if s.is_active)
        completed = sum(1 for s in self._streams.values() if not s.is_active)

        by_type = {}
        for stream in self._streams.values():
            stype = stream.stream_type.value
            if stype not in by_type:
                by_type[stype] = {'active': 0, 'completed': 0}
            if stream.is_active:
                by_type[stype]['active'] += 1
            else:
                by_type[stype]['completed'] += 1

        total_events = sum(len(s.events) for s in self._streams.values())

        return {
            'total_streams': len(self._streams),
            'active_streams': active,
            'completed_streams': completed,
            'by_type': by_type,
            'total_events': total_events,
        }


class AIResponseStreamer:
    """
    Helper class for streaming AI responses token by token
    """

    def __init__(self, stream_manager: StreamManager):
        self.stream_manager = stream_manager

    def create_response_stream(
        self,
        model_name: str,
        task_id: Optional[str] = None,
    ) -> Stream:
        """Create a new AI response stream"""
        return self.stream_manager.create_stream(
            StreamType.AI_RESPONSE,
            metadata={
                'model': model_name,
                'task_id': task_id,
            }
        )

    def stream_token(self, stream_id: str, token: str):
        """Emit a single token to the stream"""
        self.stream_manager.emit_to_stream(
            stream_id,
            'token',
            {'token': token}
        )

    def stream_tokens(self, stream_id: str, tokens: List[str], delay: float = 0.0):
        """Emit multiple tokens with optional delay"""
        for token in tokens:
            self.stream_manager.emit_to_stream(
                stream_id,
                'token',
                {'token': token}
            )
            if delay > 0:
                time.sleep(delay)

    def complete_response(
        self,
        stream_id: str,
        full_response: str,
        metadata: Optional[Dict] = None,
    ):
        """Complete the response stream"""
        self.stream_manager.complete_stream(
            stream_id,
            {
                'full_response': full_response,
                'metadata': metadata or {},
            }
        )


class TaskProgressStreamer:
    """
    Helper class for streaming task progress updates
    """

    def __init__(self, stream_manager: StreamManager):
        self.stream_manager = stream_manager

    def create_progress_stream(
        self,
        task_name: str,
        total_steps: int,
    ) -> Stream:
        """Create a new task progress stream"""
        return self.stream_manager.create_stream(
            StreamType.TASK_PROGRESS,
            metadata={
                'task_name': task_name,
                'total_steps': total_steps,
            }
        )

    def update_progress(
        self,
        stream_id: str,
        current_step: int,
        step_name: str,
        details: Optional[str] = None,
    ):
        """Update task progress"""
        self.stream_manager.emit_to_stream(
            stream_id,
            'progress',
            {
                'current_step': current_step,
                'step_name': step_name,
                'details': details,
            }
        )

    def complete_task(
        self,
        stream_id: str,
        result: Dict[str, Any],
    ):
        """Complete the task stream"""
        self.stream_manager.complete_stream(
            stream_id,
            {'result': result}
        )


class CollaborationStreamer:
    """
    Helper class for streaming collaboration events
    """

    def __init__(self, stream_manager: StreamManager):
        self.stream_manager = stream_manager

    def create_collaboration_stream(
        self,
        task_id: str,
        agents: List[str],
    ) -> Stream:
        """Create a new collaboration stream"""
        return self.stream_manager.create_stream(
            StreamType.COLLABORATION,
            metadata={
                'task_id': task_id,
                'agents': agents,
            }
        )

    def agent_started(self, stream_id: str, agent_name: str):
        """Notify that an agent has started working"""
        self.stream_manager.emit_to_stream(
            stream_id,
            'agent_started',
            {'agent': agent_name}
        )

    def agent_response(
        self,
        stream_id: str,
        agent_name: str,
        response: str,
        confidence: Optional[float] = None,
    ):
        """Emit an agent's response"""
        self.stream_manager.emit_to_stream(
            stream_id,
            'agent_response',
            {
                'agent': agent_name,
                'response': response,
                'confidence': confidence,
            }
        )

    def synthesis_started(self, stream_id: str):
        """Notify that response synthesis has started"""
        self.stream_manager.emit_to_stream(
            stream_id,
            'synthesis_started',
            {}
        )

    def complete_collaboration(
        self,
        stream_id: str,
        final_response: str,
        agent_contributions: Dict[str, str],
    ):
        """Complete the collaboration stream"""
        self.stream_manager.complete_stream(
            stream_id,
            {
                'final_response': final_response,
                'agent_contributions': agent_contributions,
            }
        )


# Singleton instance
_stream_manager: Optional[StreamManager] = None


def get_stream_manager() -> StreamManager:
    """Get the global stream manager instance"""
    global _stream_manager
    if _stream_manager is None:
        _stream_manager = StreamManager()
    return _stream_manager
