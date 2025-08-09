import asyncio
import json
import logging
import os
from typing import Dict, Callable, Any, Optional, List
from dataclasses import dataclass, field
from functools import wraps
import uuid
from datetime import datetime

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

logger = logging.getLogger(__name__)


@dataclass
class EventHandler:
    """Represents an event handler"""
    callback: Callable
    pattern: str
    once: bool = False
    priority: int = 0
    handler_id: str = field(default_factory=lambda: str(uuid.uuid4()))


class EventBus:
    """
    Event bus for inter-component communication
    Supports both Redis-backed distributed events and in-memory local events
    Falls back to in-memory mode if Redis is unavailable or disabled
    """

    def __init__(self, redis_client: Optional['redis.Redis'] = None):
        # Check if Redis should be enabled via environment variable
        use_redis = os.getenv('USE_REDIS', '').lower() in ('true', '1', 'yes', 'on')
        
        self.redis = redis_client if redis_client and REDIS_AVAILABLE and use_redis else None
        self.handlers: Dict[str, List[EventHandler]] = {}
        self.local_handlers: Dict[str, List[EventHandler]] = {}
        self.is_running = False
        self.subscriber_task: Optional[asyncio.Task] = None
        self.pubsub = None
        
        # Log the mode we're operating in
        if self.redis:
            logger.info("EventBus initialized with Redis support")
        else:
            mode_reason = []
            if not REDIS_AVAILABLE:
                mode_reason.append("Redis not available")
            if not use_redis:
                mode_reason.append("USE_REDIS not set")
            if not redis_client:
                mode_reason.append("no Redis client provided")
            
            reason = " (" + ", ".join(mode_reason) + ")" if mode_reason else ""
            logger.info(f"EventBus initialized in local-only mode{reason}")

    async def start(self):
        """Start the event bus and Redis subscriber if available"""
        if self.is_running:
            return

        self.is_running = True
        
        # Only start Redis subscriber if Redis is available
        if self.redis:
            try:
                self.pubsub = self.redis.pubsub()
                # Subscribe to all dashboard events
                await self.pubsub.subscribe("dashboard:*")
                # Start the subscriber task
                self.subscriber_task = asyncio.create_task(self._subscriber_loop())
                logger.info("Event bus started with Redis")
            except Exception as e:
                logger.warning(f"Failed to start Redis subscriber, falling back to local-only mode: {e}")
                self.redis = None
                self.pubsub = None
        
        if not self.redis:
            logger.info("Event bus started in local-only mode")

    async def stop(self):
        """Stop the event bus"""
        if not self.is_running:
            return

        self.is_running = False

        if self.subscriber_task:
            self.subscriber_task.cancel()
            try:
                await self.subscriber_task
            except asyncio.CancelledError:
                pass

        if self.pubsub:
            try:
                await self.pubsub.unsubscribe()
                await self.pubsub.close()
            except Exception as e:
                logger.warning(f"Error closing Redis pubsub: {e}")

        logger.info("Event bus stopped")

    async def _subscriber_loop(self):
        """Main subscriber loop for Redis events"""
        try:
            while self.is_running:
                message = await self.pubsub.get_message(timeout=1.0)

                if message and message['type'] == 'message':
                    channel = message['channel']

                    # Extract event type from channel (dashboard:event_type)
                    if channel.startswith('dashboard:'):
                        event_type = channel[10:]  # Remove 'dashboard:' prefix

                        try:
                            data = json.loads(message['data'])
                            await self._handle_event(event_type, data, local_only=False)
                        except json.JSONDecodeError:
                            logger.error(f"Invalid JSON in event {event_type}: {message['data']}")
                        except Exception as e:
                            logger.error(f"Error handling event {event_type}: {e}")

        except asyncio.CancelledError:
            logger.info("Event subscriber loop cancelled")
        except Exception as e:
            logger.error(f"Error in subscriber loop: {e}")

    def on(self, event_type: str, once: bool = False, priority: int = 0):
        """
        Decorator to register event handlers

        Args:
            event_type: Event type to listen for (supports wildcards like 'module.*')
            once: If True, handler is removed after first execution
            priority: Handler priority (higher = executed first)
        """

        def decorator(func: Callable):
            handler = EventHandler(
                callback=func,
                pattern=event_type,
                once=once,
                priority=priority
            )

            # Store in local handlers for both local and distributed events
            if event_type not in self.local_handlers:
                self.local_handlers[event_type] = []
            self.local_handlers[event_type].append(handler)

            # Sort by priority (higher first)
            self.local_handlers[event_type].sort(key=lambda h: h.priority, reverse=True)

            logger.debug(f"Registered handler for event '{event_type}' with priority {priority}")
            return func

        return decorator

    def off(self, event_type: str, handler_id: Optional[str] = None):
        """
        Remove event handlers

        Args:
            event_type: Event type
            handler_id: Specific handler ID to remove, or None to remove all
        """
        if event_type in self.local_handlers:
            if handler_id:
                self.local_handlers[event_type] = [
                    h for h in self.local_handlers[event_type]
                    if h.handler_id != handler_id
                ]
            else:
                del self.local_handlers[event_type]

    async def emit(self, event_type: str, data: Dict[str, Any], local_only: bool = False):
        """
        Emit an event

        Args:
            event_type: Event type
            data: Event data
            local_only: If True, only trigger local handlers (no Redis)
        """
        # Add metadata
        event_data = {
            **data,
            '_event_type': event_type,
            '_timestamp': datetime.utcnow().isoformat(),
            '_local_only': local_only
        }

        # Handle local events first
        await self._handle_event(event_type, event_data, local_only=True)

        # Publish to Redis if not local_only and Redis is available
        if not local_only and self.is_running and self.redis:
            try:
                await self.redis.publish(
                    f"dashboard:{event_type}",
                    json.dumps(event_data)
                )
                logger.debug(f"Published event '{event_type}' to Redis")
            except Exception as e:
                logger.error(f"Failed to publish event '{event_type}': {e}")

    async def _handle_event(self, event_type: str, data: Dict[str, Any], local_only: bool = False):
        """Handle an event by calling registered handlers"""
        handlers_to_call = []
        handlers_to_remove = []

        # Find matching handlers
        for pattern, handler_list in self.local_handlers.items():
            if self._match_pattern(event_type, pattern):
                for handler in handler_list:
                    handlers_to_call.append(handler)
                    if handler.once:
                        handlers_to_remove.append((pattern, handler))

        # Sort by priority
        handlers_to_call.sort(key=lambda h: h.priority, reverse=True)

        # Execute handlers
        for handler in handlers_to_call:
            try:
                if asyncio.iscoroutinefunction(handler.callback):
                    await handler.callback(data)
                else:
                    handler.callback(data)

            except Exception as e:
                logger.error(f"Error in handler for '{event_type}': {e}")

        # Remove 'once' handlers
        for pattern, handler in handlers_to_remove:
            if pattern in self.local_handlers:
                self.local_handlers[pattern] = [
                    h for h in self.local_handlers[pattern]
                    if h.handler_id != handler.handler_id
                ]

        if handlers_to_call:
            logger.debug(f"Handled event '{event_type}' with {len(handlers_to_call)} handlers")

    def _match_pattern(self, event_type: str, pattern: str) -> bool:
        """Check if event_type matches pattern (supports wildcards)"""
        if pattern == event_type:
            return True

        # Support wildcards
        if '*' in pattern:
            import re
            # Convert shell-style wildcards to regex
            regex_pattern = pattern.replace('*', '.*').replace('?', '.')
            return bool(re.match(f'^{regex_pattern}$', event_type))

        return False

    async def request_response(self, event_type: str, data: Dict[str, Any], timeout: float = 5.0) -> Dict[str, Any]:
        """
        Send a request and wait for response (request/response pattern)

        Args:
            event_type: Event type to send
            data: Request data
            timeout: Response timeout in seconds

        Returns:
            Response data
        """
        request_id = str(uuid.uuid4())
        response_event = f"{event_type}.response.{request_id}"
        response_data = None
        response_received = asyncio.Event()

        # Set up response handler
        @self.on(response_event, once=True)
        async def handle_response(resp_data):
            nonlocal response_data
            response_data = resp_data
            response_received.set()

        # Send request
        request_data = {**data, '_request_id': request_id, '_response_event': response_event}
        await self.emit(event_type, request_data)

        # Wait for response
        try:
            await asyncio.wait_for(response_received.wait(), timeout=timeout)
            return response_data
        except asyncio.TimeoutError:
            self.off(response_event)
            raise TimeoutError(f"Request timeout for {event_type}")

    async def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        redis_connected = False
        if self.redis:
            try:
                redis_connected = await self.redis.ping()
            except Exception:
                redis_connected = False
                
        return {
            'running': self.is_running,
            'redis_enabled': self.redis is not None,
            'redis_connected': redis_connected,
            'local_handlers': {
                pattern: len(handlers)
                for pattern, handlers in self.local_handlers.items()
            },
        }