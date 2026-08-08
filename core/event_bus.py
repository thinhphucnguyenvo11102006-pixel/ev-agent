"""
E.V. Event Bus — Async pub/sub event system.
Allows components to communicate in a loosely-coupled manner.
"""

import asyncio
import logging
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger("ev.event_bus")


class EventType(Enum):
    """All event types in the E.V. system."""
    # Perception events
    SPEECH_START = auto()       # VAD detected speech beginning
    SPEECH_END = auto()         # VAD detected speech ending
    TRANSCRIPTION_READY = auto()  # STT finished transcribing

    # Input events
    TEXT_INPUT = auto()         # User typed text input
    KEYBOARD_SHORTCUT = auto()  # Hotkey pressed

    # Brain events
    THINKING_START = auto()     # LLM started processing
    THINKING_DONE = auto()      # LLM finished (direct response)
    TOOL_CALL_REQUEST = auto()  # LLM wants to call a tool
    TOOL_CALL_RESULT = auto()   # Tool execution finished

    # Synthesis events
    RESPONSE_TEXT = auto()      # Final text response ready
    RESPONSE_CHUNK = auto()     # Streaming text chunk
    TTS_START = auto()          # TTS started generating audio
    TTS_DONE = auto()           # TTS finished
    AUDIO_PLAY_START = auto()   # Audio playback started
    AUDIO_PLAY_DONE = auto()    # Audio playback finished

    # Control events
    INTERRUPT = auto()          # Barge-in: user interrupted
    STATE_CHANGE = auto()       # Agent state changed
    ERROR = auto()              # Error occurred
    SHUTDOWN = auto()           # System shutting down

    # Memory events
    MEMORY_SAVE = auto()        # Save to long-term memory
    MEMORY_RECALL = auto()      # Retrieved from memory


@dataclass
class Event:
    """An event in the E.V. system."""
    type: EventType
    data: Any = None
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = ""

    def __repr__(self):
        return f"Event({self.type.name}, source={self.source}, data_type={type(self.data).__name__})"


# Type alias for event handlers
EventHandler = Callable[[Event], Coroutine[Any, Any, None]]


class EventBus:
    """
    Async event bus for inter-component communication.
    
    Usage:
        bus = EventBus()
        bus.subscribe(EventType.TEXT_INPUT, my_handler)
        await bus.emit(Event(EventType.TEXT_INPUT, data="hello"))
    """

    def __init__(self):
        self._handlers: Dict[EventType, List[EventHandler]] = {}
        self._queue: asyncio.Queue[Event] = asyncio.Queue()
        self._running = False
        self._history: List[Event] = []
        self._max_history = 100

    def subscribe(self, event_type: EventType, handler: EventHandler):
        """Subscribe a handler to an event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug(f"Subscribed {handler.__name__} to {event_type.name}")

    def unsubscribe(self, event_type: EventType, handler: EventHandler):
        """Unsubscribe a handler from an event type."""
        if event_type in self._handlers:
            self._handlers[event_type] = [
                h for h in self._handlers[event_type] if h != handler
            ]

    async def emit(self, event: Event):
        """Emit an event to all subscribed handlers."""
        logger.debug(f"Emitting {event}")
        
        # Store in history
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        # Call all handlers for this event type
        handlers = self._handlers.get(event.type, [])
        if not handlers:
            logger.debug(f"No handlers for {event.type.name}")
            return

        # Run handlers concurrently
        tasks = []
        for handler in handlers:
            try:
                tasks.append(asyncio.create_task(handler(event)))
            except Exception as e:
                logger.error(f"Error creating task for handler {handler.__name__}: {e}")

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(
                        f"Handler {handlers[i].__name__} raised: {result}"
                    )

    async def emit_nowait(self, event: Event):
        """Put event in queue for async processing (non-blocking)."""
        await self._queue.put(event)

    async def process_queue(self):
        """Process events from the queue. Run this in background."""
        self._running = True
        logger.info("Event bus queue processor started")
        
        while self._running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=0.1)
                await self.emit(event)
                self._queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Queue processing error: {e}")

    def stop(self):
        """Stop the queue processor."""
        self._running = False
        logger.info("Event bus stopped")

    def get_history(self, event_type: Optional[EventType] = None, limit: int = 10) -> List[Event]:
        """Get recent event history, optionally filtered by type."""
        if event_type:
            filtered = [e for e in self._history if e.type == event_type]
        else:
            filtered = self._history
        return filtered[-limit:]


# Global singleton
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get or create the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus
