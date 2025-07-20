"""
Integration tests for the complete module lifecycle.
"""
import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

from backend.core.module_loader import ModuleLoader, ModuleState
from backend.core.event_bus import EventBus


@pytest.mark.asyncio
class TestModuleLifecycleIntegration:
    """Integration tests for complete module lifecycle scenarios"""
    
    async def test_complete_module_lifecycle(self, started_event_bus, temp_module_dir):
        """Test complete module lifecycle from loading to unloading"""
        loader = ModuleLoader(started_event_bus)
        module_name = "test_module"
        module_path = temp_module_dir / module_name
        
        # 1. Load module
        await loader.load_module(module_name, module_path)
        
        # Verify loaded state
        assert module_name in loader.modules
        module = loader.modules[module_name]
        assert module.state == ModuleState.READY
        
        # Verify module info
        module_info = loader.module_info[module_name]
        assert module_info.state == ModuleState.READY
        assert module_info.error is None
        assert module_info.reload_count == 0
        
        # 2. Reload module
        await loader.reload_module(module_name, force=True)
        
        # Verify reload
        assert module_name in loader.modules
        updated_info = loader.module_info[module_name]
        assert updated_info.reload_count == 1
        assert updated_info.state == ModuleState.READY
        
        # 3. Unload module
        await loader.unload_module(module_name)
        
        # Verify unloaded state
        assert module_name not in loader.modules
        final_info = loader.module_info[module_name]
        assert final_info.state == ModuleState.UNLOADED
        assert final_info.module is None
        
    async def test_module_error_handling_lifecycle(self, started_event_bus, temp_module_dir):
        """Test module lifecycle with error scenarios"""
        loader = ModuleLoader(started_event_bus)
        
        # 1. Try to load invalid module
        invalid_module_dir = temp_module_dir / "invalid_module"
        invalid_module_dir.mkdir()
        
        # Create invalid module file (missing create_module function)
        invalid_file = invalid_module_dir / "module.py"
        invalid_file.write_text("# Invalid module - no create_module function")
        
        with pytest.raises(AttributeError):
            await loader.load_module("invalid_module", invalid_module_dir)
            
        # Verify error state
        assert "invalid_module" in loader.module_info
        error_info = loader.module_info["invalid_module"]
        assert error_info.state == ModuleState.ERROR
        assert error_info.error is not None
        assert "invalid_module" not in loader.modules
        
    async def test_module_dependency_lifecycle(self, started_event_bus, temp_module_dir):
        """Test module lifecycle with dependencies"""
        loader = ModuleLoader(started_event_bus)
        
        # Create modules with dependencies
        module_a_dir = temp_module_dir / "module_a"
        module_b_dir = temp_module_dir / "module_b"
        
        for module_dir in [module_a_dir, module_b_dir]:
            module_dir.mkdir()
            
        # Module A (no dependencies)
        module_a_file = module_a_dir / "module.py"
        module_a_content = '''
from backend.core.module_loader import BaseModule
from backend.core.event_bus import EventBus
from fastapi import APIRouter

class ModuleA(BaseModule):
    def __init__(self, event_bus: EventBus):
        super().__init__("module_a", event_bus)
        
    async def initialize(self):
        pass
        
    def get_routes(self):
        return [APIRouter()]

def create_module(event_bus: EventBus):
    return ModuleA(event_bus)
'''
        module_a_file.write_text(module_a_content)
        
        # Module B (depends on Module A)
        module_b_file = module_b_dir / "module.py"
        module_b_content = '''
from backend.core.module_loader import BaseModule
from backend.core.event_bus import EventBus
from fastapi import APIRouter

class ModuleB(BaseModule):
    def __init__(self, event_bus: EventBus):
        super().__init__("module_b", event_bus)
        self.add_dependency("module_a")
        
    async def initialize(self):
        pass
        
    def get_routes(self):
        return [APIRouter()]

def create_module(event_bus: EventBus):
    return ModuleB(event_bus)
'''
        module_b_file.write_text(module_b_content)
        
        # Load modules
        await loader.load_module("module_a", module_a_dir)
        await loader.load_module("module_b", module_b_dir)
        
        # Verify dependencies
        module_a = loader.modules["module_a"]
        module_b = loader.modules["module_b"]
        
        assert "module_a" in module_b.get_dependencies()
        
        # Try to unload module_a (should fail due to dependency)
        with pytest.raises(ValueError):
            await loader.unload_module("module_a")
            
        # Unload module_b first, then module_a should work
        await loader.unload_module("module_b")
        await loader.unload_module("module_a")
        
        assert len(loader.modules) == 0
        
    async def test_concurrent_module_operations(self, started_event_bus, temp_module_dir):
        """Test concurrent module operations"""
        loader = ModuleLoader(started_event_bus)
        module_name = "test_module"
        module_path = temp_module_dir / module_name
        
        # Load module first
        await loader.load_module(module_name, module_path)
        
        # Try concurrent reload operations
        async def reload_operation():
            await loader.reload_module(module_name, force=True)
            
        # Run multiple concurrent reloads
        tasks = [asyncio.create_task(reload_operation()) for _ in range(3)]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Module should still be in valid state
        assert module_name in loader.modules
        assert loader.modules[module_name].state == ModuleState.READY
        
    async def test_module_auto_reload_integration(self, started_event_bus, temp_module_dir):
        """Test auto-reload integration with file changes"""
        loader = ModuleLoader(started_event_bus)
        module_name = "test_module"
        module_path = temp_module_dir / module_name
        
        # Load module
        await loader.load_module(module_name, module_path)
        original_reload_count = loader.module_info[module_name].reload_count
        
        # Simulate file change
        module_file = module_path / "module.py"
        await asyncio.sleep(0.1)  # Ensure timestamp difference
        module_file.touch()
        
        # Auto-reload should detect changes and reload
        results = await loader.auto_reload_changed_modules()
        
        assert module_name in results
        assert results[module_name] == "success"
        assert loader.module_info[module_name].reload_count > original_reload_count
        
    async def test_module_cleanup_integration(self, started_event_bus, temp_module_dir):
        """Test module cleanup integration"""
        loader = ModuleLoader(started_event_bus)
        
        # Create module with cleanup tasks
        module_dir = temp_module_dir / "cleanup_module"
        module_dir.mkdir()
        
        module_file = module_dir / "module.py"
        module_content = '''
import asyncio
from backend.core.module_loader import BaseModule
from backend.core.event_bus import EventBus
from fastapi import APIRouter

class CleanupModule(BaseModule):
    def __init__(self, event_bus: EventBus):
        super().__init__("cleanup_module", event_bus)
        self.background_task = None
        
    async def initialize(self):
        # Start a background task
        self.background_task = asyncio.create_task(self._background_work())
        self.schedule_cleanup_task(self.background_task)
        
    async def _background_work(self):
        try:
            while True:
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            # Clean cancellation
            raise
            
    def get_routes(self):
        return [APIRouter()]

def create_module(event_bus: EventBus):
    return CleanupModule(event_bus)
'''
        module_file.write_text(module_content)
        
        # Load module
        await loader.load_module("cleanup_module", module_dir)
        
        module = loader.modules["cleanup_module"]
        assert len(module._cleanup_tasks) == 1
        background_task = module._cleanup_tasks[0]
        assert not background_task.done()
        
        # Unload module should clean up tasks
        await loader.unload_module("cleanup_module")
        
        # Background task should be cancelled
        assert background_task.cancelled() or background_task.done()
        
    async def test_module_event_integration(self, started_event_bus, temp_module_dir):
        """Test module integration with event system"""
        loader = ModuleLoader(started_event_bus)
        module_name = "test_module"
        module_path = temp_module_dir / module_name
        
        # Mock event emission
        events_emitted = []
        
        original_emit = started_event_bus.emit
        
        async def mock_emit(event, data):
            events_emitted.append((event, data))
            return await original_emit(event, data)
            
        started_event_bus.emit = mock_emit
        
        # Load module
        await loader.load_module(module_name, module_path)
        
        # Check that lifecycle events were emitted
        event_names = [event[0] for event in events_emitted]
        assert "module.loading" in event_names
        assert "module.loaded" in event_names
        
        # Unload module
        await loader.unload_module(module_name)
        
        # Check unload events
        event_names = [event[0] for event in events_emitted]
        assert "module.unloading" in event_names
        assert "module.unloaded" in event_names
        
    async def test_module_stats_integration(self, started_event_bus, temp_module_dir):
        """Test module statistics integration"""
        loader = ModuleLoader(started_event_bus)
        
        # Initially no modules
        stats = await loader.get_stats()
        assert stats["loaded_modules"] == 0
        assert stats["total_modules"] == 0
        
        # Load a module
        module_name = "test_module"
        module_path = temp_module_dir / module_name
        await loader.load_module(module_name, module_path)
        
        # Check stats after loading
        stats = await loader.get_stats()
        assert stats["loaded_modules"] == 1
        assert stats["total_modules"] == 1
        assert stats["failed_modules"] == 0
        assert stats["state_counts"]["ready"] == 1
        
        # Reload module
        await loader.reload_module(module_name, force=True)
        
        # Check stats after reload
        stats = await loader.get_stats()
        assert stats["total_reloads"] == 1
        
        # Unload module
        await loader.unload_module(module_name)
        
        # Check stats after unload
        stats = await loader.get_stats()
        assert stats["loaded_modules"] == 0
        assert stats["total_modules"] == 1  # Still tracked in module_info
        assert stats["state_counts"]["unloaded"] == 1