import asyncio
import logging
from typing import Dict, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from abc import ABC, abstractmethod
import traceback

from .event_bus import EventBus

logger = logging.getLogger(__name__)


class BaseWorker(ABC):
    """Base class for background workers"""

    def __init__(self, name: str, event_bus: EventBus, interval: float = 5.0):
        self.name = name
        self.event_bus = event_bus
        self.interval = interval
        self.is_active = False
        self.task: Optional[asyncio.Task] = None
        self.last_run: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self.run_count = 0
        self.error_count = 0

    @abstractmethod
    async def work(self):
        """Main work method - implement in subclasses"""
        pass

    async def start(self):
        """Start the worker"""
        if self.is_active:
            logger.warning(f"Worker {self.name} is already running")
            return

        self.is_active = True
        self.task = asyncio.create_task(self._work_loop())
        logger.info(f"Started worker: {self.name}")

        # Emit worker started event
        await self.event_bus.emit("worker.started", {
            "worker_name": self.name,
            "interval": self.interval
        })

    async def stop(self):
        """Stop the worker"""
        if not self.is_active:
            return

        self.is_active = False

        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None

        logger.info(f"Stopped worker: {self.name}")

        # Emit worker stopped event
        await self.event_bus.emit("worker.stopped", {
            "worker_name": self.name,
            "run_count": self.run_count,
            "error_count": self.error_count
        })

    async def _work_loop(self):
        """Main work loop"""
        try:
            while self.is_active:
                try:
                    await self.work()
                    self.last_run = datetime.utcnow()
                    self.run_count += 1
                    self.last_error = None

                except Exception as e:
                    self.error_count += 1
                    self.last_error = str(e)

                    logger.error(f"Error in worker {self.name}: {e}")
                    logger.debug(f"Worker {self.name} traceback: {traceback.format_exc()}")

                    # Emit error event
                    await self.event_bus.emit("worker.error", {
                        "worker_name": self.name,
                        "error": str(e),
                        "error_count": self.error_count
                    })

                # Wait for next iteration
                await asyncio.sleep(self.interval)

        except asyncio.CancelledError:
            logger.info(f"Worker {self.name} loop cancelled")

    def is_running(self) -> bool:
        """Check if worker is running"""
        return self.is_active and self.task is not None and not self.task.done()

    def get_stats(self) -> Dict[str, Any]:
        """Get worker statistics"""
        return {
            "name": self.name,
            "is_active": self.is_active,
            "is_running": self.is_running(),
            "interval": self.interval,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_error": self.last_error,
            "run_count": self.run_count,
            "error_count": self.error_count
        }


class SystemMonitorWorker(BaseWorker):
    """Example worker that monitors system metrics"""

    def __init__(self, event_bus: EventBus):
        super().__init__("system_monitor", event_bus, interval=5.0)

    async def work(self):
        """Monitor system metrics"""
        try:
            import psutil

            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            # Get process count
            process_count = len(psutil.pids())

            metrics = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used": memory.used,
                "memory_total": memory.total,
                "disk_percent": disk.percent,
                "disk_used": disk.used,
                "disk_total": disk.total,
                "process_count": process_count,
                "timestamp": datetime.utcnow().isoformat()
            }

            # Emit metrics event
            await self.event_bus.emit("system.metrics", metrics)

        except ImportError:
            # psutil not available, emit basic metrics
            await self.event_bus.emit("system.metrics", {
                "cpu_percent": 0,
                "memory_percent": 0,
                "disk_percent": 0,
                "process_count": 0,
                "timestamp": datetime.utcnow().isoformat(),
                "note": "psutil not available"
            })


class HeartbeatWorker(BaseWorker):
    """Worker that sends periodic heartbeat events"""

    def __init__(self, event_bus: EventBus):
        super().__init__("heartbeat", event_bus, interval=30.0)

    async def work(self):
        """Send heartbeat"""
        await self.event_bus.emit("system.heartbeat", {
            "timestamp": datetime.utcnow().isoformat(),
            "uptime": self.run_count * self.interval
        })


class WorkerManager:
    """Manages background workers"""

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.workers: Dict[str, BaseWorker] = {}
        self._register_handlers()

    def _register_handlers(self):
        """Register event handlers for worker management"""

        @self.event_bus.on("worker.start")
        async def handle_worker_start(data: Dict[str, Any]):
            """Start a worker"""
            worker_name = data.get("worker_name")
            if worker_name and worker_name in self.workers:
                await self.workers[worker_name].start()

        @self.event_bus.on("worker.stop")
        async def handle_worker_stop(data: Dict[str, Any]):
            """Stop a worker"""
            worker_name = data.get("worker_name")
            if worker_name and worker_name in self.workers:
                await self.workers[worker_name].stop()

        @self.event_bus.on("worker.restart")
        async def handle_worker_restart(data: Dict[str, Any]):
            """Restart a worker"""
            worker_name = data.get("worker_name")
            if worker_name and worker_name in self.workers:
                await self.workers[worker_name].stop()
                await asyncio.sleep(1)  # Brief pause
                await self.workers[worker_name].start()

        @self.event_bus.on("worker.status_request")
        async def handle_worker_status_request(data: Dict[str, Any]):
            """Get worker status"""
            stats = await self.get_stats()
            await self.event_bus.emit("worker.status_response", stats)

    def register_worker(self, worker: BaseWorker):
        """Register a worker"""
        self.workers[worker.name] = worker
        logger.info(f"Registered worker: {worker.name}")

    def unregister_worker(self, worker_name: str):
        """Unregister a worker"""
        if worker_name in self.workers:
            del self.workers[worker_name]
            logger.info(f"Unregistered worker: {worker_name}")

    async def start_workers(self):
        """Start all registered workers"""
        # Register default workers
        self.register_worker(SystemMonitorWorker(self.event_bus))
        self.register_worker(HeartbeatWorker(self.event_bus))

        # Start all workers
        for worker in self.workers.values():
            await worker.start()

        logger.info(f"Started {len(self.workers)} workers")

    async def stop_workers(self):
        """Stop all workers"""
        for worker in self.workers.values():
            await worker.stop()

        logger.info("Stopped all workers")

    async def start_worker(self, worker_name: str) -> bool:
        """Start a specific worker"""
        if worker_name in self.workers:
            await self.workers[worker_name].start()
            return True
        return False

    async def stop_worker(self, worker_name: str) -> bool:
        """Stop a specific worker"""
        if worker_name in self.workers:
            await self.workers[worker_name].stop()
            return True
        return False

    async def restart_worker(self, worker_name: str) -> bool:
        """Restart a specific worker"""
        if worker_name in self.workers:
            await self.workers[worker_name].stop()
            await asyncio.sleep(1)
            await self.workers[worker_name].start()
            return True
        return False

    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics for all workers"""
        return {
            "total_workers": len(self.workers),
            "running_workers": sum(1 for w in self.workers.values() if w.is_running()),
            "workers": {
                name: worker.get_stats()
                for name, worker in self.workers.items()
            }
        }

    def get_worker(self, worker_name: str) -> Optional[BaseWorker]:
        """Get a specific worker"""
        return self.workers.get(worker_name)

    def list_workers(self) -> Dict[str, Dict[str, Any]]:
        """List all workers with their basic info"""
        return {
            name: {
                "name": worker.name,
                "is_running": worker.is_running(),
                "interval": worker.interval,
                "last_run": worker.last_run.isoformat() if worker.last_run else None,
                "run_count": worker.run_count,
                "error_count": worker.error_count
            }
            for name, worker in self.workers.items()
        }