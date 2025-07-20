import asyncio
import importlib
import importlib.util
import logging
import sys
import weakref
from pathlib import Path
from typing import Dict, Any, List, Optional, Type, Set
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from fastapi import APIRouter

from .event_bus import EventBus

logger = logging.getLogger(__name__)


class ModuleState(Enum):
    """Module lifecycle states"""
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    INITIALIZING = "initializing"
    READY = "ready"
    ERROR = "error"
    UNLOADING = "unloading"


class BaseModule(ABC):
    """Base class for dashboard modules with enhanced lifecycle management"""

    def __init__(self, name: str, event_bus: EventBus):
        self.name = name
        self.event_bus = event_bus
        self.state = ModuleState.LOADED
        self._dependencies: Set[str] = set()
        self._dependents: Set[str] = set()
        self._cleanup_tasks: List[asyncio.Task] = []
        
    @abstractmethod
    async def initialize(self):
        """Initialize the module - called after loading"""
        pass

    @abstractmethod
    def get_routes(self) -> List[APIRouter]:
        """Return FastAPI routes for this module"""
        pass

    async def pre_initialize(self):
        """Pre-initialization hook - called before initialize()"""
        pass

    async def post_initialize(self):
        """Post-initialization hook - called after initialize()"""
        pass

    async def pre_cleanup(self):
        """Pre-cleanup hook - called before cleanup()"""
        pass

    async def cleanup(self):
        """Cleanup module resources (optional override)"""
        # Cancel any running tasks
        for task in self._cleanup_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._cleanup_tasks.clear()

    async def post_cleanup(self):
        """Post-cleanup hook - called after cleanup()"""
        pass

    def add_dependency(self, module_name: str):
        """Add a module dependency"""
        self._dependencies.add(module_name)

    def add_dependent(self, module_name: str):
        """Add a module that depends on this one"""
        self._dependents.add(module_name)

    def get_dependencies(self) -> Set[str]:
        """Get module dependencies"""
        return self._dependencies.copy()

    def get_dependents(self) -> Set[str]:
        """Get modules that depend on this one"""
        return self._dependents.copy()

    def schedule_cleanup_task(self, task: asyncio.Task):
        """Schedule a task to be cleaned up when module is unloaded"""
        self._cleanup_tasks.append(task)

    def get_info(self) -> Dict[str, Any]:
        """Get comprehensive module information"""
        return {
            "name": self.name,
            "state": self.state.value,
            "routes": len(self.get_routes()),
            "dependencies": list(self._dependencies),
            "dependents": list(self._dependents),
            "tasks": len(self._cleanup_tasks)
        }


@dataclass
class ModuleInfo:
    """Enhanced information about a module"""
    name: str
    path: Path
    module: Optional[BaseModule]
    state: ModuleState
    loaded_at: datetime
    last_modified: Optional[datetime] = None
    error: Optional[str] = None
    reload_count: int = 0
    module_spec: Optional[importlib.machinery.ModuleSpec] = None
    dependencies: Set[str] = field(default_factory=set)
    file_watchers: List[Any] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "name": self.name,
            "path": str(self.path),
            "state": self.state.value,
            "loaded_at": self.loaded_at.isoformat(),
            "last_modified": self.last_modified.isoformat() if self.last_modified else None,
            "error": self.error,
            "reload_count": self.reload_count,
            "dependencies": list(self.dependencies),
            "module_info": self.module.get_info() if self.module else None
        }


class ModuleLoader:
    """Enhanced module loader with improved lifecycle management"""

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.modules: Dict[str, BaseModule] = {}
        self.module_info: Dict[str, ModuleInfo] = {}
        self._module_registry: Dict[str, Type[BaseModule]] = {}
        self._loading_lock = asyncio.Lock()
        self._module_refs = weakref.WeakValueDictionary()
        self._register_handlers()

    def _register_handlers(self):
        """Register event handlers for module management"""

        @self.event_bus.on("module.reload")
        async def handle_module_reload(data: Dict[str, Any]):
            """Reload a specific module"""
            module_name = data.get("module_name")
            force = data.get("force", False)
            if module_name:
                await self.reload_module(module_name, force=force)

        @self.event_bus.on("module.unload")
        async def handle_module_unload(data: Dict[str, Any]):
            """Unload a module"""
            module_name = data.get("module_name")
            force = data.get("force", False)
            if module_name:
                await self.unload_module(module_name, force=force)

        @self.event_bus.on("module.list_request")
        async def handle_module_list_request(data: Dict[str, Any]):
            """Get list of modules"""
            module_list = self.get_module_list()
            await self.event_bus.emit("module.list_response", {
                "modules": module_list,
                "total": len(module_list)
            })
            
        @self.event_bus.on("module.reload_all")
        async def handle_module_reload_all(data: Dict[str, Any]):
            """Reload all modules"""
            force = data.get("force", False)
            await self.reload_all_modules(force=force)
            
        @self.event_bus.on("module.auto_reload")
        async def handle_module_auto_reload(data: Dict[str, Any]):
            """Auto-reload changed modules"""
            await self.auto_reload_changed_modules()
            
        @self.event_bus.on("module.check_changes")
        async def handle_module_check_changes(data: Dict[str, Any]):
            """Check for file changes"""
            changes = self.check_file_changes()
            await self.event_bus.emit("module.changes_response", {
                "changes": changes,
                "changed_count": len([c for c in changes.values() if c])
            })
            
        @self.event_bus.on("module.dependency_graph_request")
        async def handle_dependency_graph_request(data: Dict[str, Any]):
            """Get dependency graph"""
            graph = self.get_module_dependency_graph()
            await self.event_bus.emit("module.dependency_graph_response", {
                "graph": graph
            })

    async def load_modules(self, modules_dir: str):
        """Load all modules from a directory with dependency resolution"""
        modules_path = Path(modules_dir)

        if not modules_path.exists():
            logger.warning(f"Modules directory {modules_path} does not exist")
            return

        logger.info(f"Loading modules from {modules_path}")

        # Find all module directories
        module_dirs = [d for d in modules_path.iterdir() if d.is_dir() and not d.name.startswith('_')]
        
        # First pass: discover all modules
        module_specs = {}
        for module_dir in module_dirs:
            module_name = module_dir.name
            try:
                spec = await self._discover_module(module_name, module_dir)
                if spec:
                    module_specs[module_name] = spec
            except Exception as e:
                logger.error(f"Failed to discover module {module_name}: {e}")
        
        # Second pass: resolve dependencies and load in order
        load_order = self._resolve_dependencies(module_specs)
        
        loaded_count = 0
        for module_name in load_order:
            try:
                if module_name in module_specs:
                    await self.load_module(module_name, module_specs[module_name]['path'])
                    loaded_count += 1
            except Exception as e:
                logger.error(f"Failed to load module {module_name}: {e}")

        logger.info(f"Loaded {loaded_count}/{len(module_specs)} modules successfully")
        
    async def _discover_module(self, module_name: str, module_path: Path) -> Optional[Dict[str, Any]]:
        """Discover module information without loading it"""
        module_file = module_path / "module.py"
        
        if not module_file.exists():
            return None
            
        # Get file modification time
        last_modified = datetime.fromtimestamp(module_file.stat().st_mtime)
        
        return {
            "name": module_name,
            "path": module_path,
            "file": module_file,
            "last_modified": last_modified
        }
        
    def _resolve_dependencies(self, module_specs: Dict[str, Dict[str, Any]]) -> List[str]:
        """Resolve module dependencies and return load order"""
        # For now, return modules in alphabetical order
        # TODO: Parse module files to extract actual dependencies
        return sorted(module_specs.keys())

    async def load_module(self, module_name: str, module_path: Path):
        """Load a specific module with enhanced lifecycle management"""
        async with self._loading_lock:
            try:
                # Check if already loaded
                if module_name in self.modules:
                    logger.warning(f"Module {module_name} is already loaded")
                    return
                
                # Initialize module info
                module_file = module_path / "module.py"
                if not module_file.exists():
                    raise FileNotFoundError(f"module.py not found in {module_path}")
                
                last_modified = datetime.fromtimestamp(module_file.stat().st_mtime)
                
                module_info = ModuleInfo(
                    name=module_name,
                    path=module_path,
                    module=None,
                    state=ModuleState.LOADING,
                    loaded_at=datetime.now(),
                    last_modified=last_modified
                )
                self.module_info[module_name] = module_info
                
                # Emit loading event
                await self.event_bus.emit("module.loading", {
                    "module_name": module_name,
                    "path": str(module_path)
                })

                # Import the module using enhanced importlib
                sys_module_name = f"backend.modules.{module_name}"
                
                # Remove from sys.modules if it exists (for reloading)
                if sys_module_name in sys.modules:
                    del sys.modules[sys_module_name]
                
                spec = importlib.util.spec_from_file_location(
                    sys_module_name,
                    module_file
                )

                if spec is None or spec.loader is None:
                    raise ImportError(f"Could not load module spec for {module_name}")

                module_info.module_spec = spec
                py_module = importlib.util.module_from_spec(spec)
                
                # Add to sys.modules before execution
                sys.modules[sys_module_name] = py_module
                
                try:
                    spec.loader.exec_module(py_module)
                except Exception:
                    # Remove from sys.modules if execution failed
                    if sys_module_name in sys.modules:
                        del sys.modules[sys_module_name]
                    raise

                # Look for create_module function
                if not hasattr(py_module, 'create_module'):
                    raise AttributeError(f"Module {module_name} must have a create_module function")

                # Create the module instance
                module_instance = py_module.create_module(self.event_bus)

                if not isinstance(module_instance, BaseModule):
                    raise TypeError(f"Module {module_name} must return a BaseModule instance. Got {type(module_instance)}")

                # Update module info
                module_info.module = module_instance
                module_info.state = ModuleState.INITIALIZING
                module_instance.state = ModuleState.INITIALIZING
                
                # Store weak reference
                self._module_refs[module_name] = module_instance

                # Initialize the module with full lifecycle
                await module_instance.pre_initialize()
                await module_instance.initialize()
                await module_instance.post_initialize()
                
                # Mark as ready
                module_instance.state = ModuleState.READY
                module_info.state = ModuleState.READY

                # Store the module
                self.modules[module_name] = module_instance

                logger.info(f"Successfully loaded module: {module_name}")

                # Emit module loaded event
                await self.event_bus.emit("module.loaded", {
                    "module_name": module_name,
                    "module_info": module_instance.get_info()
                })

            except Exception as e:
                logger.error(f"Error loading module {module_name}: {e}")

                # Update module info with error
                if module_name in self.module_info:
                    self.module_info[module_name].state = ModuleState.ERROR
                    self.module_info[module_name].error = str(e)
                else:
                    self.module_info[module_name] = ModuleInfo(
                        name=module_name,
                        path=module_path,
                        module=None,
                        state=ModuleState.ERROR,
                        loaded_at=datetime.now(),
                        error=str(e)
                    )

                # Emit module error event
                await self.event_bus.emit("module.load_error", {
                    "module_name": module_name,
                    "error": str(e)
                })

                raise

    async def unload_module(self, module_name: str, force: bool = False):
        """Unload a module with enhanced cleanup and dependency checking"""
        if module_name not in self.modules:
            logger.warning(f"Module {module_name} is not loaded")
            return

        async with self._loading_lock:
            try:
                module = self.modules[module_name]
                module_info = self.module_info[module_name]
                
                # Check for dependents unless force unload
                if not force and module.get_dependents():
                    dependent_names = ', '.join(module.get_dependents())
                    raise ValueError(f"Cannot unload {module_name}: modules {dependent_names} depend on it. Use force=True to override.")
                
                # Update state
                module.state = ModuleState.UNLOADING
                module_info.state = ModuleState.UNLOADING
                
                # Emit unloading event
                await self.event_bus.emit("module.unloading", {
                    "module_name": module_name
                })

                # Full cleanup lifecycle
                await module.pre_cleanup()
                await module.cleanup()
                await module.post_cleanup()
                
                # Update dependencies
                for dep_name in module.get_dependencies():
                    if dep_name in self.modules:
                        self.modules[dep_name]._dependents.discard(module_name)

                # Remove from modules
                del self.modules[module_name]
                
                # Remove from weak references
                if module_name in self._module_refs:
                    del self._module_refs[module_name]

                # Remove from sys.modules
                sys_module_name = f"backend.modules.{module_name}"
                if sys_module_name in sys.modules:
                    del sys.modules[sys_module_name]
                
                # Update state
                module_info.state = ModuleState.UNLOADED
                module_info.module = None

                logger.info(f"Unloaded module: {module_name}")

                # Emit module unloaded event
                await self.event_bus.emit("module.unloaded", {
                    "module_name": module_name
                })

            except Exception as e:
                # Update error state
                if module_name in self.module_info:
                    self.module_info[module_name].state = ModuleState.ERROR
                    self.module_info[module_name].error = f"Unload error: {str(e)}"
                    
                logger.error(f"Error unloading module {module_name}: {e}")
                raise

    async def reload_module(self, module_name: str, force: bool = False):
        """Reload a module with file change detection"""
        if module_name not in self.module_info:
            logger.warning(f"Module {module_name} info not found")
            return

        module_info = self.module_info[module_name]
        
        try:
            # Check if file has been modified
            module_file = module_info.path / "module.py"
            if module_file.exists():
                current_modified = datetime.fromtimestamp(module_file.stat().st_mtime)
                if (module_info.last_modified and 
                    current_modified <= module_info.last_modified and 
                    not force):
                    logger.info(f"Module {module_name} file not modified, skipping reload")
                    return
            
            logger.info(f"Reloading module: {module_name}")
            
            # Store reload count
            reload_count = module_info.reload_count + 1
            
            # Unload existing module (force if needed)
            if module_name in self.modules:
                await self.unload_module(module_name, force=force)

            # Load the module again
            await self.load_module(module_name, module_info.path)
            
            # Update reload count
            if module_name in self.module_info:
                self.module_info[module_name].reload_count = reload_count

            logger.info(f"Successfully reloaded module: {module_name} (reload #{reload_count})")
            
            # Emit reload event
            await self.event_bus.emit("module.reloaded", {
                "module_name": module_name,
                "reload_count": reload_count
            })

        except Exception as e:
            logger.error(f"Error reloading module {module_name}: {e}")
            
            # Emit reload error event
            await self.event_bus.emit("module.reload_error", {
                "module_name": module_name,
                "error": str(e)
            })
            
            raise

    def get_module(self, module_name: str) -> Optional[BaseModule]:
        """Get a loaded module"""
        return self.modules.get(module_name)

    def get_module_list(self) -> List[Dict[str, Any]]:
        """Get comprehensive list of all modules with enhanced information"""
        result = []

        for name, info in self.module_info.items():
            module_data = info.to_dict()
            module_data["loaded"] = name in self.modules
            result.append(module_data)

        return result

    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive module loader statistics"""
        state_counts = {}
        for state in ModuleState:
            state_counts[state.value] = len([info for info in self.module_info.values() if info.state == state])
            
        total_reloads = sum(info.reload_count for info in self.module_info.values())
        
        return {
            "loaded_modules": len(self.modules),
            "total_modules": len(self.module_info),
            "failed_modules": len([info for info in self.module_info.values() if info.state == ModuleState.ERROR]),
            "state_counts": state_counts,
            "total_reloads": total_reloads,
            "modules": self.get_module_list()
        }

    def list_module_routes(self) -> Dict[str, List[str]]:
        """List all routes provided by modules"""
        routes = {}

        for name, module in self.modules.items():
            module_routes = []
            for router in module.get_routes():
                for route in router.routes:
                    if hasattr(route, 'path'):
                        methods = list(route.methods) if hasattr(route, 'methods') else ['*']
                        module_routes.append(f"{methods} {route.path}")
            routes[name] = module_routes

        return routes
    
    async def reload_all_modules(self, force: bool = False):
        """Reload all modules, optionally forcing reload even if files haven't changed"""
        logger.info("Reloading all modules...")
        
        reload_results = {}
        for module_name in list(self.module_info.keys()):
            try:
                await self.reload_module(module_name, force=force)
                reload_results[module_name] = "success"
            except Exception as e:
                reload_results[module_name] = f"error: {str(e)}"
                
        # Emit reload all event
        await self.event_bus.emit("module.reload_all_complete", {
            "results": reload_results,
            "success_count": len([r for r in reload_results.values() if r == "success"]),
            "error_count": len([r for r in reload_results.values() if r.startswith("error")])
        })
        
        return reload_results
    
    async def unload_all_modules(self, force: bool = False):
        """Unload all modules"""
        logger.info("Unloading all modules...")
        
        unload_results = {}
        # Unload in reverse order to handle dependencies
        for module_name in reversed(list(self.modules.keys())):
            try:
                await self.unload_module(module_name, force=force)
                unload_results[module_name] = "success"
            except Exception as e:
                unload_results[module_name] = f"error: {str(e)}"
                
        return unload_results
    
    def check_file_changes(self) -> Dict[str, bool]:
        """Check which modules have file changes since last load"""
        changes = {}
        
        for name, info in self.module_info.items():
            module_file = info.path / "module.py"
            if module_file.exists() and info.last_modified:
                current_modified = datetime.fromtimestamp(module_file.stat().st_mtime)
                changes[name] = current_modified > info.last_modified
            else:
                changes[name] = False
                
        return changes
    
    async def auto_reload_changed_modules(self):
        """Automatically reload modules that have file changes"""
        changes = self.check_file_changes()
        changed_modules = [name for name, changed in changes.items() if changed]
        
        if not changed_modules:
            logger.debug("No module file changes detected")
            return {}
            
        logger.info(f"Auto-reloading changed modules: {', '.join(changed_modules)}")
        
        reload_results = {}
        for module_name in changed_modules:
            try:
                await self.reload_module(module_name)
                reload_results[module_name] = "success"
            except Exception as e:
                reload_results[module_name] = f"error: {str(e)}"
                
        return reload_results
    
    def get_module_dependency_graph(self) -> Dict[str, Dict[str, List[str]]]:
        """Get the module dependency graph"""
        graph = {
            "dependencies": {},  # module -> [dependencies]
            "dependents": {}      # module -> [dependents]
        }
        
        for name, module in self.modules.items():
            graph["dependencies"][name] = list(module.get_dependencies())
            graph["dependents"][name] = list(module.get_dependents())
            
        return graph