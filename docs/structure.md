# Dashboard Project Structure

```
dashboard/
├── backend/
│   ├── main.py                 # Main FastAPI application
│   ├── core/
│   │   ├── __init__.py
│   │   ├── event_bus.py        # Redis-backed event bus
│   │   ├── websocket_manager.py # WebSocket connection management
│   │   ├── module_loader.py    # Dynamic module loading
│   │   └── worker_manager.py   # Background worker management
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── system_info/
│   │   │   ├── __init__.py
│   │   │   └── module.py       # Example system info module
│   │   ├── app_launcher/
│   │   │   ├── __init__.py
│   │   │   └── module.py       # App launcher module (to be created)
│   │   └── media_control/
│   │       ├── __init__.py
│   │       └── module.py       # Media control module (to be created)
│   └── requirements.txt
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── src/
│   │   ├── main.js
│   │   ├── App.vue
│   │   ├── components/
│   │   │   ├── Dashboard.vue
│   │   │   └── ModuleContainer.vue
│   │   ├── modules/
│   │   │   ├── SystemInfo.vue
│   │   │   ├── AppLauncher.vue
│   │   │   └── MediaControl.vue
│   │   └── stores/
│   │       ├── websocket.js
│   │       └── dashboard.js
│   └── dist/                   # Built frontend files
├── pyproject.toml
├── README.md
└── docker-compose.yml          # Optional Redis container
```

## pyproject.toml

```toml
[project]
name = "dashboard"
version = "0.1.0"
description = "Custom control dashboard with WebSocket communication"
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "websockets>=12.0",
    "redis>=5.0.0",
    "pydantic>=2.5.0",
    "python-multipart>=0.0.6",
    "psutil>=5.9.0",  # For system monitoring
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
    "mypy>=1.7.0",
]

[project.scripts]
dashboard = "main:main"

[tool.black]
line-length = 100
target-version = ['py311']

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
```

## requirements.txt (Alternative to pyproject.toml)

```txt
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
websockets>=12.0
redis>=5.0.0
pydantic>=2.5.0
python-multipart>=0.0.6
psutil>=5.9.0
```

## Development Setup

### 1. Backend Setup
```bash
# Create and activate virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -e .
# Or with requirements.txt: uv pip install -r requirements.txt

# Start Redis (needed for event bus)
# Option 1: Docker
docker run -d -p 6379:6379 redis:latest

# Option 2: Local Redis installation
# sudo apt-get install redis-server  # Ubuntu/Debian
# brew install redis                 # macOS

# Start the backend
cd backend
python main.py
# Or: uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend Setup (Vue.js)
```bash
cd frontend

# Initialize Vue project (if not already done)
npm create vue@latest .

# Install dependencies
npm install

# Additional dependencies for dashboard
npm install @vueuse/core pinia vue-router

# Start development server
npm run dev
```

## Core Architecture Features

### Event Bus System
- **Redis-backed** for distributed events across processes
- **Local handlers** for same-process communication
- **Pattern matching** with wildcards (`module.*`)
- **Request/response pattern** for sync-like operations
- **Priority-based handlers** for ordered execution

### WebSocket Manager
- **Auto-reconnection** with exponential backoff
- **Client subscriptions** to specific event types
- **Heartbeat/ping** to keep connections alive
- **Broadcast filtering** for targeted messages
- **Connection metadata** tracking

### Module System
- **Dynamic loading** from filesystem
- **Hot reloading** without restart
- **Self-contained** routes and event handlers
- **Dependency injection** of event bus
- **Error isolation** - one module failure doesn't crash others

### Worker System
- **Background tasks** running independently
- **Configurable intervals** and error handling
- **Statistics tracking** (run count, errors, timing)
- **Start/stop/restart** via events
- **Built-in workers** for system monitoring and heartbeat

## Creating Your First Custom Module

### 1. Create Module Directory
```bash
mkdir -p backend/modules/my_module
touch backend/modules/my_module/__init__.py
```

### 2. Create module.py
```python
from fastapi import APIRouter
from core.module_loader import BaseModule
from core.event_bus import EventBus

class MyCustomModule(BaseModule):
    def __init__(self, event_bus: EventBus):
        super().__init__("my_module", event_bus)
        self.router = APIRouter()
        self._setup_routes()
        self._setup_events()
    
    async def initialize(self):
        # Module initialization logic
        await self.event_bus.emit("my_module.initialized", {})
    
    def _setup_routes(self):
        @self.router.get("/hello")
        async def hello():
            return {"message": "Hello from my module!"}
    
    def _setup_events(self):
        @self.event_bus.on("my_module.do_something")
        async def handle_event(data):
            # Handle custom events
            pass
    
    def get_routes(self):
        return [self.router]

def create_module(event_bus: EventBus):
    return MyCustomModule(event_bus)
```

### 3. Module Auto-Discovery
The module will be automatically loaded when the application starts. Access it at:
- REST API: `http://localhost:8000/api/my_module/hello`
- Events: Send `my_module.do_something` via WebSocket

## WebSocket Communication Protocol

### Client → Server
```json
{
  "type": "event_type",
  "payload": { "key": "value" },
  "target": "module_name"  // Optional
}
```

### Server → Client
```json
{
  "type": "event_type",
  "payload": { "data": "response" }
}
```

### Built-in Events
- `system.status_request` - Get system status
- `worker.start/stop/restart` - Control workers
- `module.reload/unload` - Module management
- `websocket.subscribe/unsubscribe` - Event subscriptions

## Next Steps

1. **Start with the system_info module** to test the architecture
2. **Create an app_launcher module** for controlling applications
3. **Build Vue.js frontend** with WebSocket client
4. **Add more workers** for specific monitoring tasks
5. **Implement module-specific frontend components**

## PyCharm Configuration

### Run Configuration
- **Script path**: `backend/main.py`
- **Working directory**: `/path/to/dashboard`
- **Environment variables**: `PYTHONPATH=backend`
- **Python interpreter**: Project venv

### Debugging WebSockets
- Set breakpoints in WebSocket handlers
- Use PyCharm's HTTP client for testing REST endpoints
- Monitor Redis with built-in Redis plugin