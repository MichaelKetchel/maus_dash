import asyncio
import json
import logging
import os
import re
from typing import Dict, Any, List
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.module_loader import BaseModule
from backend.core.event_bus import EventBus

logger = logging.getLogger(__name__)


def is_url_safe(text: str) -> bool:
    """Check if a string contains only URL-safe characters"""
    return re.match(r'^[A-Za-z0-9\-_.~]*$', text) is not None


#
# class SystemInfoResponse(BaseModel):
#     """Response model for system info"""
#     hostname: str
#     platform: str
#     python_version: str
#     uptime: float
#     timestamp: str

class CLICommand(BaseModel):
    """Represents a CLI command"""
    name: str
    cmds: List[str]

class CLICommandResponse(CLICommand):
    """Represents a CLI command response"""
    name: str
    cmd: str
    code: int
    stdout: str
    stderr: str


class CLIExecutorModule(BaseModule):
    """Enhanced system information module with full lifecycle support"""

    def __init__(self, event_bus: EventBus):
        super().__init__("cli_executor", event_bus)
        self.router = APIRouter()
        self.start_time = datetime.utcnow()
        self._setup_routes()
        self._setup_event_handlers()

        self.available_commands: dict[str, CLICommand] = {}

    async def pre_initialize(self):
        """Pre-initialization setup"""
        logger.info(f"Pre-initializing {self.__name__}")
        
    async def initialize(self):
        """Initialize the module"""
        logger.info(f"Initializing {self.__name__}")
        
        # Load commands from commands.json
        commands_file = os.path.join(os.path.dirname(__file__), "commands.json")
        try:
            with open(commands_file, 'r') as f:
                commands_data = json.load(f)
            
            for cmd_data in commands_data:
                cli_command = CLICommand(**cmd_data)
                self.available_commands[cli_command.name] = cli_command
            
            logger.info(f"Loaded {len(self.available_commands)} commands from {commands_file}")
        except FileNotFoundError:
            logger.warning(f"Commands file not found: {commands_file}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in commands file: {e}")
        except Exception as e:
            logger.error(f"Error loading commands: {e}")

        # Example of module initialization
        await self.event_bus.emit(f"{self.name}.initialized", {
            "module": self.name,
            "start_time": self.start_time.isoformat()
        })
        
    async def post_initialize(self):
        """Post-initialization setup"""
        logger.info(f"Post-initializing {self.__name__}")
        # Module is now fully ready

    def _setup_routes(self):
        """Setup FastAPI routes for this module"""

        for command in self.available_commands.values():

            if " " in command.name:
                logger.error("Command name contains spaces, which are not URL safe.")




    def _setup_event_handlers(self):
        """Setup event handlers for this module"""

        @self.event_bus.on(f"{self.name}.refresh_requested")
        async def handle_refresh_request(data: Dict[str, Any]):
            """Handle refresh requests"""
            logger.info("System info refresh requested")

            # Simulate getting fresh data
            await asyncio.sleep(0.1)

            # Emit updated system info
            await self.event_bus.emit(f"{self.name}.updated", {
                "module": self.name,
                "updated_at": datetime.utcnow().isoformat(),
                "uptime": (datetime.utcnow() - self.start_time).total_seconds()
            })

        @self.event_bus.on("system.metrics")
        async def handle_system_metrics(data: Dict[str, Any]):
            """Handle system metrics from worker"""
            # Forward metrics to WebSocket clients
            await self.event_bus.emit("websocket.broadcast", {
                "message": {
                    "type": "system_metrics",
                    "payload": data
                }
            })

        @self.event_bus.on(f"{self.name}.get_status")
        async def handle_status_request(data: Dict[str, Any]):
            """Handle status requests"""
            status = {
                "module": self.name,
                "state": self.state.value,
                "uptime": (datetime.utcnow() - self.start_time).total_seconds(),
                "routes": len(self.get_routes()),
                "timestamp": datetime.utcnow().isoformat()
            }

            await self.event_bus.emit(f"{self.name}.status_response", status)

    def get_routes(self) -> List[APIRouter]:
        """Return FastAPI routes for this module"""
        return [self.router]

    async def pre_cleanup(self):
        """Pre-cleanup hook"""
        logger.info(f"Pre-cleanup {self.__name__}")
        
    async def cleanup(self):
        """Cleanup module resources"""
        logger.info(f"Cleaning up {self.__name__}")
        
        # Cancel metrics task
        if self._metrics_task and not self._metrics_task.done():
            self._metrics_task.cancel()
            try:
                await self._metrics_task
            except asyncio.CancelledError:
                pass

        # Call parent cleanup for standard cleanup tasks
        await super().cleanup()

        # Emit cleanup event
        await self.event_bus.emit(f"{self.name}.cleanup", {
            "module": self.name,
            "cleanup_at": datetime.utcnow().isoformat()
        })
        
    async def post_cleanup(self):
        """Post-cleanup hook"""
        logger.info(f"Post-cleanup {self.__name__}")


    async def _metrics_loop(self):
        """Background metrics collection loop"""
        try:
            import psutil
            while True:
                try:
                    metrics = {
                        "cpu_percent": psutil.cpu_percent(interval=1),
                        "memory": {
                            "total": psutil.virtual_memory().total,
                            "used": psutil.virtual_memory().used,
                            "percent": psutil.virtual_memory().percent
                        },
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    # Add disk info (cross-platform)
                    try:
                        disk = psutil.disk_usage('/' if hasattr(psutil, 'disk_usage') else 'C:\\')
                        metrics["disk"] = {
                            "total": disk.total,
                            "used": disk.used,
                            "percent": (disk.used / disk.total) * 100
                        }
                    except Exception:
                        pass  # Skip disk metrics if unavailable
                    
                    await self.event_bus.emit("system.metrics", metrics)
                    await asyncio.sleep(5)  # Update every 5 seconds
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in metrics loop: {e}")
                    await asyncio.sleep(10)  # Wait longer on error
                    
        except ImportError:
            pass  # psutil not available


def create_module(event_bus: EventBus) -> BaseModule:
    """Factory function to create the module instance"""
    return CLIExecutorModule(event_bus)