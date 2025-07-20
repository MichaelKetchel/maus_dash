"""
Test configuration and fixtures for the maus_dash project.
"""
import asyncio
import tempfile
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from typing import AsyncGenerator, Dict, Any

# Add the project root to the Python path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.core.event_bus import EventBus
from backend.core.module_loader import ModuleLoader, BaseModule


class MockRedisClient:
    """Mock Redis client for testing"""
    def __init__(self):
        self.data = {}
        self._subscribers = {}
        
    async def ping(self):
        return True
        
    async def publish(self, channel: str, message: str):
        if channel in self._subscribers:
            for callback in self._subscribers[channel]:
                await callback(message)
                
    async def subscribe(self, channel: str):
        if channel not in self._subscribers:
            self._subscribers[channel] = []
        return MagicMock()
        
    async def close(self):
        pass


class MockEventBus(EventBus):
    """Mock EventBus for testing"""
    def __init__(self):
        # Initialize without Redis
        self.redis = MockRedisClient()
        self.handlers = {}
        self.started = False
        
    async def start(self):
        self.started = True
        
    async def stop(self):
        self.started = False


class TestModule(BaseModule):
    """Test module for testing purposes"""
    
    def __init__(self, event_bus: EventBus, name: str = "test_module"):
        super().__init__(name, event_bus)
        self.initialized = False
        self.pre_init_called = False
        self.post_init_called = False
        self.pre_cleanup_called = False
        self.post_cleanup_called = False
        
    async def pre_initialize(self):
        self.pre_init_called = True
        
    async def initialize(self):
        self.initialized = True
        
    async def post_initialize(self):
        self.post_init_called = True
        
    async def pre_cleanup(self):
        self.pre_cleanup_called = True
        
    async def cleanup(self):
        await super().cleanup()
        
    async def post_cleanup(self):
        self.post_cleanup_called = True
        
    def get_routes(self):
        from fastapi import APIRouter
        router = APIRouter()
        
        @router.get("/test")
        async def test_route():
            return {"message": "test"}
            
        return [router]


@pytest.fixture
def mock_redis():
    """Fixture providing a mock Redis client"""
    return MockRedisClient()


@pytest.fixture  
def event_bus(mock_redis):
    """Fixture providing a mock event bus"""
    return MockEventBus()


@pytest.fixture
async def started_event_bus(event_bus):
    """Fixture providing a started event bus"""
    await event_bus.start()
    yield event_bus
    await event_bus.stop()


@pytest.fixture
def module_loader(started_event_bus):
    """Fixture providing a module loader"""
    return ModuleLoader(started_event_bus)


@pytest.fixture
def test_module(started_event_bus):
    """Fixture providing a test module"""
    return TestModule(started_event_bus)


@pytest.fixture
def temp_module_dir():
    """Fixture providing a temporary directory with a test module"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        module_dir = temp_path / "test_module"
        module_dir.mkdir()
        
        # Create a test module file
        module_file = module_dir / "module.py"
        module_content = '''
from backend.core.module_loader import BaseModule
from backend.core.event_bus import EventBus
from fastapi import APIRouter

class TestModuleImpl(BaseModule):
    def __init__(self, event_bus: EventBus):
        super().__init__("test_module", event_bus)
        
    async def initialize(self):
        pass
        
    def get_routes(self):
        router = APIRouter()
        
        @router.get("/test")
        async def test_endpoint():
            return {"test": "success"}
            
        return [router]

def create_module(event_bus: EventBus):
    return TestModuleImpl(event_bus)
'''
        module_file.write_text(module_content)
        
        yield temp_path


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()