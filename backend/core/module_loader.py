import asyncio
import importlib.util
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass
from fastapi import APIRouter

from .event_bus import EventBus

logger = logging.getLogger(__name__)


class BaseModule(ABC):
    """Base class for dashboard modules"""

    def __init__(self, name: str, event_bus: EventBus):
        self.name = name
        self.event_bus = event_bus
        self.is_initialized = False

    @abstractmethod
    async def initialize(self):
        """Initialize the module"""
        pass

    @abstractmethod
    def get_routes(self) -> List[APIRouter]:
        """Return FastAPI routes for this module"""
        pass

    async def cleanup(self):
        """Cleanup module resources (optional override)"""
        pass

    def get_info(self) -> Dict[str, Any]:
        """Get module information"""
        return {
            "name": self.name,
            "initialized": self.is_initialized,
            "routes": len(self.get_routes())
        }


@dataclass
class ModuleInfo:
    """Information about a loaded module"""
    name: str
    path: Path
    module: BaseModule
    loaded_at: str
    error: Optional[str] = None


class ModuleLoader:
    """Loads and manages dashboard modules"""

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.modules: Dict[str, BaseModule] = {}
        self.module_info: Dict[str, ModuleInfo] = {}
        self._register_handlers()

    def _register_handlers(self):
        """Register event handlers for module management"""

        @self.event_bus.on("module.reload")
        async def handle_module_reload(data: Dict[str, Any]):
            """Reload a specific module"""
            module_name = data.get("module_name")
            if module_name:
                await self.reload_module(module_name)

        @self.event_bus.on("module.unload")
        async def handle_module_unload(data: Dict[str, Any]):
            """Unload a module"""
            module_name = data.get("module_name")
            if module_name:
                await self.unload_module(module_name)

        @self.event_bus.on("module.list_request")
        async def handle_module_list_request(data: Dict[str, Any]):
            """Get list of modules"""
            module_list = self.get_module_list()
            await self.event_bus.emit("module.list_response", {
                "modules": module_list,
                "total": len(module_list)
            })

    async def load_modules(self, modules_dir: str):
        """Load all modules from a directory"""
        modules_path = Path(modules_dir)

        if not modules_path.exists():
            logger.warning(f"Modules directory {modules_path} does not exist")
            return

        logger.info(f"Loading modules from {modules_path}")

        # Find all module directories
        module_dirs = [d for d in modules_path.iterdir() if d.is_dir() and not d.name.startswith('_')]

        for module_dir in module_dirs:
            module_name = module_dir.name

            try:
                await self.load_module(module_name, module_dir)
            except Exception as e:
                logger.error(f"Failed to load module {module_name}: {e}")

        logger.info(f"Loaded {len(self.modules)} modules successfully")

    async def load_module(self, module_name: str, module_path: Path):
        """Load a specific module"""
        try:
            # Look for module.py in the module directory
            module_file = module_path / "module.py"

            if not module_file.exists():
                raise FileNotFoundError(f"module.py not found in {module_path}")

            # Import the module
            spec = importlib.util.spec_from_file_location(
                f"modules.{module_name}",
                module_file
            )

            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load module spec for {module_name}")

            module = importlib.util.module_from_spec(spec)
            sys.modules[f"modules.{module_name}"] = module
            spec.loader.exec_module(module)

            # Look for create_module function
            if not hasattr(module, 'create_module'):
                raise AttributeError(f"Module {module_name} must have a create_module function")

            # Create the module instance
            module_instance = module.create_module(self.event_bus)

            if not isinstance(module_instance, BaseModule):
                raise TypeError(f"Module {module_name} must return a BaseModule instance. Got {type(module_instance)}")

            # Initialize the module
            await module_instance.initialize()
            module_instance.is_initialized = True

            # Store the module
            self.modules[module_name] = module_instance
            self.module_info[module_name] = ModuleInfo(
                name=module_name,
                path=module_path,
                module=module_instance,
                loaded_at=asyncio.get_event_loop().time()
            )

            logger.info(f"Successfully loaded module: {module_name}")

            # Emit module loaded event
            await self.event_bus.emit("module.loaded", {
                "module_name": module_name,
                "module_info": module_instance.get_info()
            })

        except Exception as e:
            logger.error(f"Error loading module {module_name}: {e}")

            # Store error info
            self.module_info[module_name] = ModuleInfo(
                name=module_name,
                path=module_path,
                module=None,
                loaded_at=asyncio.get_event_loop().time(),
                error=str(e)
            )

            # Emit module error event
            await self.event_bus.emit("module.load_error", {
                "module_name": module_name,
                "error": str(e)
            })

            raise

    async def unload_module(self, module_name: str):
        """Unload a module"""
        if module_name not in self.modules:
            logger.warning(f"Module {module_name} is not loaded")
            return

        try:
            module = self.modules[module_name]

            # Cleanup the module
            await module.cleanup()

            # Remove from modules
            del self.modules[module_name]

            # Remove from sys.modules if it exists
            sys_module_name = f"modules.{module_name}"
            if sys_module_name in sys.modules:
                del sys.modules[sys_module_name]

            logger.info(f"Unloaded module: {module_name}")

            # Emit module unloaded event
            await self.event_bus.emit("module.unloaded", {
                "module_name": module_name
            })

        except Exception as e:
            logger.error(f"Error unloading module {module_name}: {e}")
            raise

    async def reload_module(self, module_name: str):
        """Reload a module"""
        if module_name not in self.module_info:
            logger.warning(f"Module {module_name} info not found")
            return

        module_info = self.module_info[module_name]

        try:
            # Unload existing module
            if module_name in self.modules:
                await self.unload_module(module_name)

            # Load the module again
            await self.load_module(module_name, module_info.path)

            logger.info(f"Reloaded module: {module_name}")

        except Exception as e:
            logger.error(f"Error reloading module {module_name}: {e}")
            raise

    def get_module(self, module_name: str) -> Optional[BaseModule]:
        """Get a loaded module"""
        return self.modules.get(module_name)

    def get_module_list(self) -> List[Dict[str, Any]]:
        """Get list of all modules (loaded and failed)"""
        result = []

        for name, info in self.module_info.items():
            module_data = {
                "name": name,
                "loaded_at": info.loaded_at,
                "path": str(info.path),
                "loaded": name in self.modules,
                "error": info.error
            }

            if info.module:
                module_data.update(info.module.get_info())

            result.append(module_data)

        return result

    async def get_stats(self) -> Dict[str, Any]:
        """Get module loader statistics"""
        return {
            "loaded_modules": len(self.modules),
            "total_modules": len(self.module_info),
            "failed_modules": len([info for info in self.module_info.values() if info.error]),
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
                        module_routes.append(f"{route.methods} {route.path}")
            routes[name] = module_routes

        return routes