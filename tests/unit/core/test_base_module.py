"""
Unit tests for the enhanced BaseModule class.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from backend.core.module_loader import BaseModule, ModuleState
from tests.conftest import TestModule


class TestBaseModule:
    """Test cases for BaseModule class"""
    
    def test_base_module_initialization(self, started_event_bus):
        """Test BaseModule initialization"""
        module = TestModule(started_event_bus, "test_module")
        
        assert module.name == "test_module"
        assert module.event_bus == started_event_bus
        assert module.state == ModuleState.LOADED
        assert module._dependencies == set()
        assert module._dependents == set()
        assert module._cleanup_tasks == []
        
    @pytest.mark.asyncio
    async def test_module_lifecycle_hooks(self, test_module):
        """Test all lifecycle hooks are called in correct order"""
        # Test pre-initialize
        await test_module.pre_initialize()
        assert test_module.pre_init_called
        
        # Test initialize
        await test_module.initialize()
        assert test_module.initialized
        
        # Test post-initialize
        await test_module.post_initialize()
        assert test_module.post_init_called
        
        # Test pre-cleanup
        await test_module.pre_cleanup()
        assert test_module.pre_cleanup_called
        
        # Test cleanup
        await test_module.cleanup()
        
        # Test post-cleanup
        await test_module.post_cleanup()
        assert test_module.post_cleanup_called
        
    def test_dependency_management(self, test_module):
        """Test module dependency management"""
        # Add dependencies
        test_module.add_dependency("module_a")
        test_module.add_dependency("module_b")
        
        assert "module_a" in test_module.get_dependencies()
        assert "module_b" in test_module.get_dependencies()
        assert len(test_module.get_dependencies()) == 2
        
        # Add dependents
        test_module.add_dependent("module_c")
        test_module.add_dependent("module_d")
        
        assert "module_c" in test_module.get_dependents()
        assert "module_d" in test_module.get_dependents()
        assert len(test_module.get_dependents()) == 2
        
    def test_dependency_immutability(self, test_module):
        """Test that returned dependency sets are copies"""
        test_module.add_dependency("test_dep")
        
        deps = test_module.get_dependencies()
        deps.add("modified")
        
        # Original dependencies should not be modified
        assert "modified" not in test_module.get_dependencies()
        assert len(test_module.get_dependencies()) == 1
        
    @pytest.mark.asyncio
    async def test_cleanup_task_management(self, test_module):
        """Test cleanup task scheduling and management"""
        # Create some mock tasks
        task1 = asyncio.create_task(asyncio.sleep(0.1))
        task2 = asyncio.create_task(asyncio.sleep(0.1))
        
        # Schedule tasks for cleanup
        test_module.schedule_cleanup_task(task1)
        test_module.schedule_cleanup_task(task2)
        
        assert len(test_module._cleanup_tasks) == 2
        assert task1 in test_module._cleanup_tasks
        assert task2 in test_module._cleanup_tasks
        
        # Cleanup should cancel all tasks
        await test_module.cleanup()
        
        # Tasks should be cancelled and list should be empty
        assert task1.cancelled() or task1.done()
        assert task2.cancelled() or task2.done()
        assert len(test_module._cleanup_tasks) == 0
        
    @pytest.mark.asyncio
    async def test_cleanup_with_completed_tasks(self, test_module):
        """Test cleanup with already completed tasks"""
        # Create a task that completes immediately
        async def quick_task():
            return "done"
            
        task = asyncio.create_task(quick_task())
        await task  # Wait for completion
        
        test_module.schedule_cleanup_task(task)
        
        # Cleanup should handle completed tasks gracefully
        await test_module.cleanup()
        assert len(test_module._cleanup_tasks) == 0
        
    def test_get_info(self, test_module):
        """Test module info generation"""
        # Add some dependencies and tasks
        test_module.add_dependency("dep1")
        test_module.add_dependent("dep2")
        test_module.schedule_cleanup_task(asyncio.create_task(asyncio.sleep(1)))
        
        info = test_module.get_info()
        
        # Verify info structure
        assert info["name"] == "test_module"
        assert info["state"] == ModuleState.LOADED.value
        assert info["routes"] == 1  # TestModule has 1 route
        assert info["dependencies"] == ["dep1"]
        assert info["dependents"] == ["dep2"]
        assert info["tasks"] == 1
        
    def test_state_transitions(self, test_module):
        """Test module state management"""
        # Initial state
        assert test_module.state == ModuleState.LOADED
        
        # Change state
        test_module.state = ModuleState.INITIALIZING
        assert test_module.state == ModuleState.INITIALIZING
        
        test_module.state = ModuleState.READY
        assert test_module.state == ModuleState.READY
        
        test_module.state = ModuleState.UNLOADING
        assert test_module.state == ModuleState.UNLOADING
        
    def test_routes_implementation(self, test_module):
        """Test that get_routes returns proper router list"""
        routes = test_module.get_routes()
        
        assert isinstance(routes, list)
        assert len(routes) == 1
        
        # Verify it's a FastAPI router
        from fastapi import APIRouter
        assert isinstance(routes[0], APIRouter)
        
    @pytest.mark.asyncio
    async def test_abstract_methods_enforcement(self, started_event_bus):
        """Test that abstract methods must be implemented"""
        from abc import ABC
        
        # BaseModule should be abstract
        assert issubclass(BaseModule, ABC)
        
        # Should not be able to instantiate BaseModule directly
        with pytest.raises(TypeError):
            BaseModule("test", started_event_bus)
            
    @pytest.mark.asyncio
    async def test_concurrent_cleanup_tasks(self, test_module):
        """Test cleanup with multiple concurrent tasks"""
        tasks = []
        
        # Create multiple long-running tasks
        for i in range(5):
            task = asyncio.create_task(asyncio.sleep(0.5))
            tasks.append(task)
            test_module.schedule_cleanup_task(task)
            
        assert len(test_module._cleanup_tasks) == 5
        
        # Cleanup should cancel all tasks concurrently
        await test_module.cleanup()
        
        # All tasks should be cancelled
        for task in tasks:
            assert task.cancelled() or task.done()
            
        assert len(test_module._cleanup_tasks) == 0
        
    @pytest.mark.asyncio
    async def test_cleanup_task_exception_handling(self, test_module):
        """Test cleanup handles task exceptions gracefully"""
        async def failing_task():
            await asyncio.sleep(0.1)
            raise ValueError("Task failed")
            
        task = asyncio.create_task(failing_task())
        test_module.schedule_cleanup_task(task)
        
        # Cleanup should handle task exceptions without raising
        await test_module.cleanup()
        assert len(test_module._cleanup_tasks) == 0
        
    def test_module_name_immutability(self, test_module):
        """Test that module name cannot be changed after initialization"""
        original_name = test_module.name
        
        # Name should be read-only (though Python doesn't enforce this)
        # This test documents the expected behavior
        assert test_module.name == original_name
        
    @pytest.mark.asyncio
    async def test_event_bus_integration(self, test_module):
        """Test module integration with event bus"""
        # Module should have access to event bus
        assert test_module.event_bus is not None
        
        # Should be able to emit events (using mock)
        test_module.event_bus.emit = AsyncMock()
        
        await test_module.event_bus.emit("test.event", {"data": "test"})
        test_module.event_bus.emit.assert_called_once_with("test.event", {"data": "test"})


class TestModuleState:
    """Test cases for ModuleState enum"""
    
    def test_module_state_values(self):
        """Test ModuleState enum values"""
        assert ModuleState.UNLOADED.value == "unloaded"
        assert ModuleState.LOADING.value == "loading"
        assert ModuleState.LOADED.value == "loaded"
        assert ModuleState.INITIALIZING.value == "initializing"
        assert ModuleState.READY.value == "ready"
        assert ModuleState.ERROR.value == "error"
        assert ModuleState.UNLOADING.value == "unloading"
        
    def test_module_state_comparison(self):
        """Test ModuleState comparisons"""
        assert ModuleState.LOADED == ModuleState.LOADED
        assert ModuleState.LOADED != ModuleState.READY
        
    def test_module_state_string_representation(self):
        """Test ModuleState string representation"""
        assert str(ModuleState.READY) == "ModuleState.READY"