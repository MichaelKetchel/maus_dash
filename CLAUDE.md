# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a customizable dashboard system similar to TouchPortal or Stream Deck, designed to run as a web application accessible via Android tablet or Surface computer. It features a FastAPI backend with Vue.js frontend, real-time WebSocket communication through a Redis-backed event bus system, and modular plugin architecture for extensibility.

**Purpose**: Custom control dashboard with real-time bidirectional communication, modular architecture, and responsive design for various control and monitoring tasks.

## Development Commands

### Backend (Python/FastAPI)
- **Start development server**: `python backend/main.py` (from project root)
- **Install dependencies**: `uv pip install -e .` (uses pyproject.toml)
- **Format code**: `black backend/` (line-length: 100, if black is installed)
- **Lint code**: `ruff check backend/` (if ruff is installed)
- **Run tests**: `pytest` (if tests exist)

### Frontend (Vue.js)
- **Install dependencies**: `npm install` (from frontend/ directory)
- **Start dev server**: `npm run dev` (from frontend/ directory)
- **Build for production**: `npm run build` (from frontend/ directory)
- **Lint**: `npm run lint` (from frontend/ directory)
- **Format**: `npm run format` (from frontend/ directory)

### Infrastructure
- **Start Redis**: `docker run -d -p 6379:6379 redis:latest` (required for event bus)
- **Package for distribution**: `uv run pyinstaller --onefile --windowed backend/main.py`

## Core Architecture

### Event Bus System (`backend/core/event_bus.py`)
- Redis-backed distributed event system for inter-component communication
- Supports both local and Redis-distributed events
- Pattern matching with wildcards (`module.*`)
- Priority-based event handlers

### Module System (`backend/core/module_loader.py`)
- Dynamic module loading from `backend/modules/` directory
- Each module inherits from `BaseModule` class
- Modules automatically register FastAPI routes under `/api/{module_name}/`
- Hot reloading capability without restart

### WebSocket Manager (`backend/core/websocket_manager.py`)
- Real-time bidirectional communication
- Auto-reconnection with exponential backoff
- Client subscription filtering
- Heartbeat/ping for connection health

### Worker Manager (`backend/core/worker_manager.py`)
- Background task execution system
- Configurable intervals and error handling
- Statistics tracking and lifecycle management

## File Structure

```
backend/
├── main.py                    # FastAPI application entry point
├── core/                      # Core framework components
│   ├── event_bus.py          # Redis-backed event system
│   ├── websocket_manager.py  # WebSocket connection handling
│   ├── module_loader.py      # Dynamic module loading
│   └── worker_manager.py     # Background worker system
└── modules/                   # Application modules
    └── system_info/          # Example module
        └── module.py

frontend/
├── src/
│   ├── App.vue              # Main application component
│   ├── stores/              # Pinia state management
│   │   ├── websocket.js     # WebSocket connection store
│   │   └── dashboard.js     # Dashboard state
│   └── components/          # Vue components
└── package.json
```

## Development Patterns

### Event Naming Convention
- `system.*` - Core system events (status, metrics, heartbeat)
- `module.*` - Module lifecycle events (loaded, unloaded, errors)  
- `worker.*` - Worker control events (start, stop, restart, error)
- `websocket.*` - Client connection events (subscribe, broadcast)

### Creating New Modules

**Backend Module Pattern:**
1. Create directory in `backend/modules/{module_name}/`
2. Create `module.py` that inherits from `BaseModule`
3. Implement required methods: `initialize()`, `get_routes()`
4. Use factory pattern: `def create_module(event_bus: EventBus): return ModuleName(event_bus)`
5. Module will auto-load and register routes at `/api/{module_name}/`

**Frontend Integration:**
1. Create `frontend/src/components/modules/ModuleName.vue` component
2. Integrate with existing Pinia stores (websocket.js, dashboard.js)
3. Follow established WebSocket event patterns
4. Ensure dark/light theme and responsive design compatibility

### Worker Creation Pattern
- Background workers run independently with configurable intervals
- Register via WorkerManager with start/stop/restart control via events
- Built-in workers: system monitor, heartbeat
- Statistics tracking and error handling included

## WebSocket Communication

- **Endpoint**: `/ws`
- **Message format**: `{"type": "event_type", "payload": {...}, "target": "module_name"}`
- **Built-in events**: `system.status_request`, `worker.start/stop/restart`, `websocket.subscribe/unsubscribe`
- **Auto-reconnection**: Exponential backoff with health monitoring
- **Pattern matching**: Support for wildcards in event subscriptions

## Dependencies

- **Backend**: FastAPI, uvicorn, websockets, redis, pydantic
- **Frontend**: Vue 3, Pinia, Vite, TailwindCSS
- **Dev tools**: pytest, black, ruff (Python), eslint, prettier (JavaScript)

## Current System Status

### ✅ Implemented Features
- Complete FastAPI foundation with lifespan management
- Redis-backed event bus with pattern matching
- WebSocket manager with connection health and broadcasting  
- Module loader for hot-pluggable functionality
- Background worker system (system monitor, heartbeat workers)
- Vue.js frontend with real-time dashboard
- System info module showing live CPU/memory metrics
- Dark/light theme with responsive design
- WebSocket client with auto-reconnection and event subscriptions

### 🎯 Ready for Extension
- App launcher module for system control
- Media control module for audio/video
- Custom automation modules  
- Hardware integration modules
- Advanced dashboard widgets

## Development Environment

- **Backend**: localhost:8000 (FastAPI + WebSocket)
- **Frontend**: localhost:3000 (Vite dev server with proxy to backend)
- **Redis**: Required for event bus functionality
- **Real-time communication**: Working between frontend and backend

## Notes

- Redis connection required on localhost:6379 for event bus
- WebSocket proxy configured in Vite for development
- CORS enabled for frontend integration
- Error isolation - module failures don't crash system
- Production ready with proper error handling and logging
- Module routes automatically prefixed with `/api/{module_name}`