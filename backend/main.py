import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
import json
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import redis.asyncio as redis
from pydantic import BaseModel, Field

from backend.core.event_bus import EventBus
from backend.core.websocket_manager import WebSocketManager
from backend.core.module_loader import ModuleLoader
from backend.core.worker_manager import WorkerManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Pydantic models for API
class EventMessage(BaseModel):
    type: str = Field(..., description="Event type")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Event payload")
    target: Optional[str] = Field(None, description="Target module (optional)")


class StatusResponse(BaseModel):
    status: str
    modules: Dict[str, Any]
    workers: Dict[str, Any]
    connections: int


# Global instances
event_bus: EventBus = None
websocket_manager: WebSocketManager = None
module_loader: ModuleLoader = None
worker_manager: WorkerManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown"""
    global event_bus, websocket_manager, module_loader, worker_manager

    logger.info("Starting Dashboard Application...")

    try:
        # Initialize Redis connection
        redis_client = redis.Redis(
            host='localhost',
            port=6379,
            decode_responses=True,
            retry_on_timeout=True
        )

        # Test Redis connection
        await redis_client.ping()
        logger.info("Redis connection established")

        # Initialize core components
        event_bus = EventBus(redis_client)
        websocket_manager = WebSocketManager(event_bus)
        module_loader = ModuleLoader(event_bus)
        worker_manager = WorkerManager(event_bus)

        # Start the event bus
        await event_bus.start()

        # Load modules - handle both running from backend/ and project root
        backend_dir = Path(__file__).parent
        modules_dir = backend_dir / "modules"
        await module_loader.load_modules(str(modules_dir))

        # Start background workers
        await worker_manager.start_workers()

        # Register core event handlers
        await register_core_handlers()

        logger.info("Dashboard application started successfully!")
        logger.info(f"Loaded modules: {list(module_loader.modules.keys())}")
        logger.info(f"Started workers: {list(worker_manager.workers.keys())}")
        
        # Debug: List all routes in the app
        logger.info("All registered routes:")
        for route in app.routes:
            if hasattr(route, 'path'):
                logger.info(f"  {getattr(route, 'methods', 'N/A')} {route.path}")

    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise

    yield  # Application runs here

    # Shutdown
    logger.info("Shutting down Dashboard Application...")

    if worker_manager:
        await worker_manager.stop_workers()

    if module_loader:
        logger.info("Unloading all modules...")
        try:
            await module_loader.unload_all_modules(force=True)
            logger.info("All modules unloaded successfully")
        except Exception as e:
            logger.error(f"Error unloading modules: {e}")

    if event_bus:
        await event_bus.stop()

    if redis_client:
        await redis_client.close()

    logger.info("Dashboard application stopped")


async def register_core_handlers():
    """Register core event handlers"""

    @event_bus.on("system.status_request")
    async def handle_status_request(data: Dict[str, Any]):
        """Handle status requests from frontend"""
        status = {
            "status": "running",
            "modules": {
                name: {"loaded": True, "routes": len(module.get_routes())}
                for name, module in module_loader.modules.items()
            },
            "workers": {
                name: {"running": worker.is_running(), "last_run": worker.last_run.isoformat()}
                for name, worker in worker_manager.workers.items()
            },
            "connections": websocket_manager.connection_count
        }

        await event_bus.emit("system.status_response", status)

    @event_bus.on("websocket.broadcast")
    async def handle_websocket_broadcast(data: Dict[str, Any]):
        """Handle broadcast messages to all WebSocket clients"""
        await websocket_manager.broadcast(data)


# Pre-register module routes during import time
def setup_module_routes():
    """Setup module routes at import time"""
    from backend.core.event_bus import EventBus
    from backend.core.module_loader import ModuleLoader
    import redis.asyncio as redis
    import asyncio
    
    # We need to do this synchronously at import time
    backend_dir = Path(__file__).parent
    modules_dir = backend_dir / "modules"
    
    # Simple synchronous module discovery for route registration
    if modules_dir.exists():
        for module_dir in modules_dir.iterdir():
            if module_dir.is_dir() and not module_dir.name.startswith('_'):
                module_file = module_dir / "module.py"
                if module_file.exists():
                    try:
                        # Import and register routes directly
                        import importlib.util
                        import sys
                        
                        spec = importlib.util.spec_from_file_location(
                            f"modules.{module_dir.name}",
                            module_file
                        )
                        if spec and spec.loader:
                            module = importlib.util.module_from_spec(spec)
                            sys.modules[f"modules.{module_dir.name}"] = module
                            spec.loader.exec_module(module)
                            
                            if hasattr(module, 'create_module'):
                                # Create a minimal event bus for route setup
                                class MinimalEventBus:
                                    def on(self, event): return lambda f: f
                                
                                module_instance = module.create_module(MinimalEventBus())
                                routes = module_instance.get_routes()
                                
                                for router in routes:
                                    app.include_router(router, prefix=f"/api/{module_dir.name}")
                                    
                                logger.info(f"Pre-registered {len(routes)} routers for module {module_dir.name}")
                    except Exception as e:
                        logger.error(f"Failed to pre-register module {module_dir.name}: {e}")

# Create FastAPI app
app = FastAPI(
    title="Dashboard API",
    description="Customizable control dashboard with real-time WebSocket communication",
    version="0.1.0",
    lifespan=lifespan
)

# Setup module routes at import time
setup_module_routes()

# Test route to verify routing works
@app.get("/test")
async def test_route():
    return {"message": "Test route works"}

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": asyncio.get_event_loop().time()}


# Status endpoint
@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    """Get application status"""
    if not event_bus:
        raise HTTPException(status_code=503, detail="Application not ready")

    # Request status from event bus
    await event_bus.emit("system.status_request", {})

    # Wait for response (in a real app, you might want to implement a proper request/response pattern)
    await asyncio.sleep(0.1)  # Small delay to allow status to be processed

    return StatusResponse(
        status="running",
        modules={
            name: {"loaded": True, "routes": len(module.get_routes())}
            for name, module in module_loader.modules.items()
        },
        workers={
            name: {"running": worker.is_running(), "last_run": getattr(worker, 'last_run', None)}
            for name, worker in worker_manager.workers.items()
        },
        connections=websocket_manager.connection_count
    )


# Enhanced Module Management API Endpoints
@app.get("/api/modules")
async def get_modules():
    """Get list of all modules with enhanced information"""
    if module_loader:
        return {
            "modules": module_loader.get_module_list(),
            "stats": await module_loader.get_stats()
        }
    return {"modules": [], "stats": {}}

@app.post("/api/modules/{module_name}/reload")
async def reload_module(module_name: str, force: bool = False):
    """Reload a specific module"""
    if not module_loader:
        raise HTTPException(status_code=503, detail="Module loader not available")
    
    try:
        await module_loader.reload_module(module_name, force=force)
        return {"status": "success", "message": f"Module {module_name} reloaded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/modules/{module_name}/unload")
async def unload_module(module_name: str, force: bool = False):
    """Unload a specific module"""
    if not module_loader:
        raise HTTPException(status_code=503, detail="Module loader not available")
    
    try:
        await module_loader.unload_module(module_name, force=force)
        return {"status": "success", "message": f"Module {module_name} unloaded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/modules/reload-all")
async def reload_all_modules(force: bool = False):
    """Reload all modules"""
    if not module_loader:
        raise HTTPException(status_code=503, detail="Module loader not available")
    
    try:
        results = await module_loader.reload_all_modules(force=force)
        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/modules/auto-reload")
async def auto_reload_modules():
    """Auto-reload modules with file changes"""
    if not module_loader:
        raise HTTPException(status_code=503, detail="Module loader not available")
    
    try:
        results = await module_loader.auto_reload_changed_modules()
        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/modules/changes")
async def check_module_changes():
    """Check for module file changes"""
    if not module_loader:
        raise HTTPException(status_code=503, detail="Module loader not available")
    
    changes = module_loader.check_file_changes()
    return {"changes": changes, "changed_count": len([c for c in changes.values() if c])}

@app.get("/api/modules/dependency-graph")
async def get_dependency_graph():
    """Get module dependency graph"""
    if not module_loader:
        raise HTTPException(status_code=503, detail="Module loader not available")
    
    return {"graph": module_loader.get_module_dependency_graph()}

@app.get("/api/modules/routes")
async def get_module_routes():
    """Get all routes provided by modules"""
    if not module_loader:
        raise HTTPException(status_code=503, detail="Module loader not available")
    
    return {"routes": module_loader.list_module_routes()}


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for real-time communication"""
    client_id = await websocket_manager.connect(websocket)
    logger.info(f"Client {client_id} connected")

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                event_type = message.get("type")
                payload = message.get("payload", {})
                target = message.get("target")

                if not event_type:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "payload": {"message": "Missing event type"}
                    }))
                    continue

                # Add client_id to payload for tracking
                payload["_client_id"] = client_id

                # Route message through event bus
                if target:
                    await event_bus.emit(f"{target}.{event_type}", payload)
                else:
                    await event_bus.emit(event_type, payload)

                logger.debug(f"Processed event {event_type} from client {client_id}")

            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "payload": {"message": "Invalid JSON"}
                }))
            except Exception as e:
                logger.error(f"Error processing message from client {client_id}: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "payload": {"message": str(e)}
                }))

    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
    finally:
        await websocket_manager.disconnect(client_id)


# Mount static files (for serving frontend if needed)  
backend_dir = Path(__file__).parent
static_path = backend_dir.parent / "frontend" / "dist"
if static_path.exists():
    app.mount("/", StaticFiles(directory=static_path, html=True), name="static")


# Dynamic route registration from modules
async def register_module_routes():
    """Register routes from loaded modules"""
    if module_loader:
        for module_name, module in module_loader.modules.items():
            routes = module.get_routes()
            logger.info(f"Module {module_name} has {len(routes)} routers")
            for i, router in enumerate(routes):
                logger.info(f"Registering router {i} for {module_name} with {len(router.routes)} routes")
                for route in router.routes:
                    logger.info(f"  Route: {route.methods} {route.path}")
                app.include_router(router, prefix=f"/api/{module_name}")
                logger.info(f"  Included router with prefix /api/{module_name}")
            logger.info(f"Registered {len(routes)} routers for module {module_name}")


@app.get("/url-list")
def get_all_urls():
    url_list = [{"path": route.path, "name": route.name} for route in app.routes]
    return url_list

def main():
    """Main entry point"""
    import uvicorn

    # Configuration
    config = {
        "host": "0.0.0.0",
        "port": 8000,
        "log_level": "info",
        "reload": True,  # Set to False in production
        "reload_dirs": ["."],
    }

    logger.info(f"Starting server on {config['host']}:{config['port']}")
    uvicorn.run("main:app", **config)


if __name__ == "__main__":
    main()