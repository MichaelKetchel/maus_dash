"""
Unit tests for the enhanced ModuleLoader class.
"""
import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from backend.core.module_loader import ModuleLoader, BaseModule, ModuleState, ModuleInfo
from backend.core.event_bus import EventBus


class TestModuleLoader:
    """Test cases for ModuleLoader class"""
    
    @pytest.mark.asyncio
    async def test_module_loader_initialization(self, started_event_bus):
        """Test ModuleLoader initialization"""
        loader = ModuleLoader(started_event_bus)
        
        assert loader.event_bus == started_event_bus
        assert loader.modules == {}
        assert loader.module_info == {}
        assert hasattr(loader, '_loading_lock')
        assert hasattr(loader, '_module_refs')
        
    @pytest.mark.asyncio
    async def test_load_single_module(self, module_loader, temp_module_dir):
        """Test loading a single module"""
        module_name = "test_module"
        module_path = temp_module_dir / module_name
        
        # Load the module
        await module_loader.load_module(module_name, module_path)
        
        # Verify module was loaded
        assert module_name in module_loader.modules
        assert module_name in module_loader.module_info
        
        module = module_loader.modules[module_name]
        assert isinstance(module, BaseModule)
        assert module.name == module_name
        assert module.state == ModuleState.READY
        
        module_info = module_loader.module_info[module_name]
        assert module_info.name == module_name
        assert module_info.state == ModuleState.READY
        assert module_info.module == module
        assert module_info.error is None
        
    @pytest.mark.asyncio
    async def test_load_nonexistent_module(self, module_loader, temp_module_dir):
        """Test loading a module that doesn't exist"""
        module_name = "nonexistent_module"
        module_path = temp_module_dir / module_name
        
        with pytest.raises(FileNotFoundError):
            await module_loader.load_module(module_name, module_path)
            
        # Verify module info contains error
        assert module_name in module_loader.module_info
        module_info = module_loader.module_info[module_name]
        assert module_info.state == ModuleState.ERROR
        assert module_info.error is not None
        assert module_name not in module_loader.modules
        
    @pytest.mark.asyncio
    async def test_unload_module(self, module_loader, temp_module_dir):
        """Test unloading a module"""
        module_name = "test_module"
        module_path = temp_module_dir / module_name
        
        # Load module first
        await module_loader.load_module(module_name, module_path)
        assert module_name in module_loader.modules
        
        # Unload module
        await module_loader.unload_module(module_name)
        
        # Verify module was unloaded
        assert module_name not in module_loader.modules
        assert module_name in module_loader.module_info
        
        module_info = module_loader.module_info[module_name]
        assert module_info.state == ModuleState.UNLOADED
        assert module_info.module is None
        
    @pytest.mark.asyncio
    async def test_unload_nonexistent_module(self, module_loader):
        """Test unloading a module that doesn't exist"""
        # Should not raise an exception, just log a warning
        await module_loader.unload_module("nonexistent_module")
        
    @pytest.mark.asyncio
    async def test_reload_module(self, module_loader, temp_module_dir):
        """Test reloading a module"""
        module_name = "test_module"
        module_path = temp_module_dir / module_name
        
        # Load module first
        await module_loader.load_module(module_name, module_path)
        original_reload_count = module_loader.module_info[module_name].reload_count
        
        # Reload module
        await module_loader.reload_module(module_name, force=True)
        
        # Verify module was reloaded
        assert module_name in module_loader.modules
        module_info = module_loader.module_info[module_name]
        assert module_info.reload_count == original_reload_count + 1
        assert module_info.state == ModuleState.READY
        
    @pytest.mark.asyncio
    async def test_reload_all_modules(self, module_loader, temp_module_dir):
        """Test reloading all modules"""
        module_name = "test_module"
        module_path = temp_module_dir / module_name
        
        # Load module first
        await module_loader.load_module(module_name, module_path)
        
        # Reload all modules
        results = await module_loader.reload_all_modules(force=True)
        
        # Verify results
        assert module_name in results
        assert results[module_name] == "success"
        
    @pytest.mark.asyncio
    async def test_unload_all_modules(self, module_loader, temp_module_dir):
        """Test unloading all modules"""
        module_name = "test_module"
        module_path = temp_module_dir / module_name
        
        # Load module first
        await module_loader.load_module(module_name, module_path)
        assert module_name in module_loader.modules
        
        # Unload all modules
        results = await module_loader.unload_all_modules(force=True)
        
        # Verify results
        assert module_name in results
        assert results[module_name] == "success"
        assert len(module_loader.modules) == 0
        
    @pytest.mark.asyncio
    async def test_check_file_changes(self, module_loader, temp_module_dir):
        """Test file change detection"""
        module_name = "test_module"
        module_path = temp_module_dir / module_name
        
        # Load module first
        await module_loader.load_module(module_name, module_path)
        
        # Check for changes (should be False since no changes)
        changes = module_loader.check_file_changes()
        assert module_name in changes
        assert changes[module_name] is False
        
        # Modify the file
        module_file = module_path / "module.py"
        await asyncio.sleep(0.1)  # Ensure time difference
        module_file.touch()
        
        # Check for changes again (should be True now)
        changes = module_loader.check_file_changes()
        assert changes[module_name] is True
        
    @pytest.mark.asyncio
    async def test_auto_reload_changed_modules(self, module_loader, temp_module_dir):
        """Test auto-reload of changed modules"""
        module_name = "test_module"
        module_path = temp_module_dir / module_name
        
        # Load module first
        await module_loader.load_module(module_name, module_path)
        original_reload_count = module_loader.module_info[module_name].reload_count
        
        # Modify the file to trigger change detection
        module_file = module_path / "module.py"
        await asyncio.sleep(0.1)
        module_file.touch()
        
        # Auto-reload changed modules
        results = await module_loader.auto_reload_changed_modules()
        
        # Verify module was reloaded
        assert module_name in results
        assert results[module_name] == "success"
        assert module_loader.module_info[module_name].reload_count > original_reload_count
        
    @pytest.mark.asyncio 
    async def test_get_module_stats(self, module_loader, temp_module_dir):
        """Test getting module statistics"""
        module_name = "test_module"
        module_path = temp_module_dir / module_name
        
        # Load module first
        await module_loader.load_module(module_name, module_path)
        
        # Get stats
        stats = await module_loader.get_stats()
        
        # Verify stats structure
        assert "loaded_modules" in stats
        assert "total_modules" in stats
        assert "failed_modules" in stats
        assert "state_counts" in stats
        assert "total_reloads" in stats
        assert "modules" in stats
        
        assert stats["loaded_modules"] == 1
        assert stats["total_modules"] == 1
        assert stats["failed_modules"] == 0
        assert stats["state_counts"]["ready"] == 1
        
    @pytest.mark.asyncio
    async def test_get_module_list(self, module_loader, temp_module_dir):
        """Test getting module list"""
        module_name = "test_module"
        module_path = temp_module_dir / module_name
        
        # Load module first
        await module_loader.load_module(module_name, module_path)
        
        # Get module list
        module_list = module_loader.get_module_list()
        
        # Verify module list structure
        assert len(module_list) == 1
        module_data = module_list[0]
        
        assert module_data["name"] == module_name
        assert module_data["state"] == "ready"
        assert module_data["loaded"] is True
        assert module_data["error"] is None
        assert "module_info" in module_data
        
    @pytest.mark.asyncio
    async def test_get_dependency_graph(self, module_loader):
        """Test getting module dependency graph"""
        graph = module_loader.get_module_dependency_graph()
        
        # Verify graph structure
        assert "dependencies" in graph
        assert "dependents" in graph
        
    @pytest.mark.asyncio
    async def test_list_module_routes(self, module_loader, temp_module_dir):
        """Test listing module routes"""
        module_name = "test_module"
        module_path = temp_module_dir / module_name
        
        # Load module first
        await module_loader.load_module(module_name, module_path)
        
        # List routes
        routes = module_loader.list_module_routes()
        
        # Verify routes structure
        assert module_name in routes
        assert len(routes[module_name]) > 0
        
    @pytest.mark.asyncio
    async def test_event_handlers_registration(self, started_event_bus):
        """Test that event handlers are properly registered"""
        loader = ModuleLoader(started_event_bus)
        
        # Verify handlers are registered by checking the event bus
        # This is a basic test since we're using a mock event bus
        assert hasattr(loader, '_register_handlers')
        
    @pytest.mark.asyncio
    async def test_concurrent_module_loading(self, module_loader, temp_module_dir):
        """Test concurrent module loading with locking"""
        module_name = "test_module"
        module_path = temp_module_dir / module_name
        
        # Attempt to load the same module concurrently
        # The second call should wait for the first to complete
        task1 = asyncio.create_task(module_loader.load_module(module_name, module_path))
        task2 = asyncio.create_task(module_loader.load_module(module_name, module_path))
        
        # Wait for both tasks (second should handle already loaded case)
        await task1
        try:
            await task2
        except Exception:
            pass  # Expected since module is already loaded
        
        # Verify only one module instance exists
        assert len(module_loader.modules) == 1
        assert module_name in module_loader.modules


class TestModuleInfo:
    """Test cases for ModuleInfo class"""
    
    def test_module_info_to_dict(self, test_module):
        """Test ModuleInfo to_dict serialization"""
        from datetime import datetime
        
        info = ModuleInfo(
            name="test_module",
            path=Path("/test/path"),
            module=test_module,
            state=ModuleState.READY,
            loaded_at=datetime.now(),
            last_modified=datetime.now()
        )
        
        data = info.to_dict()
        
        # Verify serialization
        assert data["name"] == "test_module"
        assert data["path"] == "/test/path"
        assert data["state"] == "ready"
        assert "loaded_at" in data
        assert "last_modified" in data
        assert data["error"] is None
        assert data["reload_count"] == 0
        assert "module_info" in data