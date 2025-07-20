import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.module_loader import BaseModule
from core.event_bus import EventBus

logger = logging.getLogger(__name__)


class SystemInfoResponse(BaseModel):
    """Response model for system info"""
    hostname: str
    platform: str
    python_version: str
    uptime: float
    timestamp: str


class SystemInfoModule(BaseModule):
    """Example module that provides system information"""

    def __init__(self, event_bus: EventBus):
        super().__init__("system_info", event_bus)
        self.router = APIRouter()
        self.start_time = datetime.utcnow()
        self._setup_routes()
        self._setup_event_handlers()

    async def initialize(self):
        """Initialize the module"""
        logger.info("Initializing SystemInfo module")

        # Example of module initialization
        await self.event_bus.emit("system_info.initialized", {
            "module": self.name,
            "start_time": self.start_time.isoformat()
        })

    def _setup_routes(self):
        """Setup FastAPI routes for this module"""

        @self.router.get("/info", response_model=SystemInfoResponse)
        async def get_system_info():
            """Get basic system information"""
            try:
                import platform
                import sys
                import socket

                uptime = (datetime.utcnow() - self.start_time).total_seconds()

                return SystemInfoResponse(
                    hostname=socket.gethostname(),
                    platform=platform.platform(),
                    python_version=sys.version,
                    uptime=uptime,
                    timestamp=datetime.utcnow().isoformat()
                )
            except Exception as e:
                logger.error(f"Error getting system info: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.router.get("/metrics")
        async def get_system_metrics():
            """Get system metrics (if psutil is available)"""
            try:
                import psutil

                return {
                    "cpu_percent": psutil.cpu_percent(interval=0.1),
                    "memory": {
                        "total": psutil.virtual_memory().total,
                        "used": psutil.virtual_memory().used,
                        "percent": psutil.virtual_memory().percent
                    },
                    "disk": {
                        "total": psutil.disk_usage('/').total,
                        "used": psutil.disk_usage('/').used,
                        "percent": psutil.disk_usage('/').percent
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
            except ImportError:
                raise HTTPException(
                    status_code=503,
                    detail="psutil not available - install with: pip install psutil"
                )
            except Exception as e:
                logger.error(f"Error getting metrics: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.router.post("/refresh")
        async def refresh_system_info():
            """Trigger a system info refresh"""
            await self.event_bus.emit("system_info.refresh_requested", {
                "requested_at": datetime.utcnow().isoformat()
            })

            return {"status": "refresh_requested"}

    def _setup_event_handlers(self):
        """Setup event handlers for this module"""

        @self.event_bus.on("system_info.refresh_requested")
        async def handle_refresh_request(data: Dict[str, Any]):
            """Handle refresh requests"""
            logger.info("System info refresh requested")

            # Simulate getting fresh data
            await asyncio.sleep(0.1)

            # Emit updated system info
            await self.event_bus.emit("system_info.updated", {
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

        @self.event_bus.on("system_info.get_status")
        async def handle_status_request(data: Dict[str, Any]):
            """Handle status requests"""
            status = {
                "module": self.name,
                "initialized": self.is_initialized,
                "uptime": (datetime.utcnow() - self.start_time).total_seconds(),
                "routes": len(self.get_routes()),
                "timestamp": datetime.utcnow().isoformat()
            }

            await self.event_bus.emit("system_info.status_response", status)

    def get_routes(self) -> List[APIRouter]:
        """Return FastAPI routes for this module"""
        return [self.router]

    async def cleanup(self):
        """Cleanup module resources"""
        logger.info("Cleaning up SystemInfo module")

        # Emit cleanup event
        await self.event_bus.emit("system_info.cleanup", {
            "module": self.name,
            "cleanup_at": datetime.utcnow().isoformat()
        })


def create_module(event_bus: EventBus) -> BaseModule:
    """Factory function to create the module instance"""
    return SystemInfoModule(event_bus)