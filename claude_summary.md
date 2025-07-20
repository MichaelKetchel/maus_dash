# Custom Dashboard System - Project Overview

## 📋 Project Description

A customizable Python-based dashboard system similar to TouchPortal or Stream Deck, designed to run as a web application accessed via Android tablet or Surface computer. Features real-time bidirectional communication, modular architecture, and responsive design.

## 🏗️ Architecture Overview

### Backend (FastAPI + Python)
- **FastAPI** main application with WebSocket support
- **Redis-backed event bus** for distributed messaging
- **WebSocket manager** for real-time client communication
- **Module loader** for hot-pluggable functionality
- **Worker manager** for background async tasks
- **uv** for dependency management and virtual environments

### Frontend (Vue.js 3)
- **Vue 3 with Composition API** for reactive components
- **Pinia** for state management (WebSocket + Dashboard stores)
- **Tailwind CSS** for responsive design and dark/light themes
- **Vite** for development server with HMR and production builds
- **Auto-reconnecting WebSocket client** with health monitoring

## 🔧 Core Components

### Backend Core (`backend/core/`)
1. **event_bus.py** - Redis-backed message bus with pattern matching
2. **websocket_manager.py** - Connection lifecycle and broadcasting
3. **module_loader.py** - Dynamic module loading and hot reload
4. **worker_manager.py** - Background worker orchestration
5. **main.py** - FastAPI application with lifespan management

### Frontend Core (`frontend/src/`)
1. **stores/websocket.js** - WebSocket connection and event handling
2. **stores/dashboard.js** - Application state and system monitoring
3. **App.vue** - Main application layout and orchestration
4. **components/** - Reusable UI components (StatCard, ConnectionStatus, etc.)
5. **components/modules/** - Dashboard module components

## 📦 Key Features Implemented

### ✅ Event-Driven Communication
- **Pattern-based event routing** (`module.*`, `worker.*`, `system.*`)
- **Request/response pattern** for synchronous-like operations
- **WebSocket event subscriptions** from frontend components
- **Local + distributed events** via Redis pub/sub

### ✅ Modular Architecture
- **Self-contained modules** with routes, events, and cleanup
- **Hot reload capability** without application restart
- **Factory pattern** for clean dependency injection
- **Example system_info module** as template

### ✅ Background Workers
- **Independent async workers** (system monitor, heartbeat)
- **Configurable intervals** and error handling
- **Start/stop/restart** control via events
- **Statistics tracking** and health monitoring

### ✅ Real-Time Dashboard
- **Live system metrics** (CPU, memory, disk usage)
- **Connection status monitoring** with auto-reconnection
- **Dark/light theme** with system preference detection
- **Responsive grid layout** for multiple screen sizes

## 🚀 Development Environment

### Backend Setup
```bash
cd backend
uv venv && source .venv/bin/activate
uv pip install -e .
docker run -d -p 6379:6379 redis:latest  # Event bus
python main.py  # Starts on localhost:8000
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev  # Starts on localhost:3000 with proxy to backend
```

## 📁 Project Structure
```
dashboard/
├── backend/
│   ├── main.py                 # FastAPI application entry point
│   ├── core/                   # Core framework components
│   ├── modules/                # Pluggable dashboard modules
│   └── pyproject.toml         # Python dependencies
├── frontend/
│   ├── src/                   # Vue.js application source
│   ├── package.json           # Node.js dependencies
│   └── vite.config.js         # Development server config
└── pyproject.toml             # Root project config
```

## 🎯 Established Patterns

### Module Creation Pattern
1. **Backend**: Create `modules/module_name/module.py` with `BaseModule` subclass
2. **Frontend**: Create `components/modules/ModuleName.vue` component
3. **Integration**: Module auto-loads and registers routes + events
4. **Communication**: Use event bus for module ↔ frontend communication

### Event Naming Convention
- `system.*` - Core system events (status, metrics, heartbeat)
- `module.*` - Module lifecycle events (loaded, unloaded, errors)
- `worker.*` - Worker control events (start, stop, restart, error)
- `websocket.*` - Client connection events (subscribe, broadcast)

### WebSocket Message Format
```json
{
  "type": "event_type",
  "payload": { "data": "object" },
  "target": "module_name"  // Optional
}
```

## 🔄 Current Status

### ✅ Completed
- Full-stack foundation with real-time communication
- System monitoring module with live metrics
- WebSocket health monitoring and auto-reconnection
- Dark/light theme with responsive design
- Module and worker management infrastructure

### 🎯 Ready for Extension
- App launcher module for system control
- Media control module for audio/video
- Custom automation modules
- Hardware integration modules
- Advanced dashboard widgets

## 🛠️ Development Tools

- **PyCharm/IntelliJ** - Backend development with uv integration
- **WebStorm** - Frontend development (optional)
- **Redis** - Message bus (Docker or local installation)
- **Browser DevTools** - WebSocket debugging and performance monitoring

## 📝 Notes

- **Redis required** for event bus functionality
- **WebSocket proxy** configured in Vite for development
- **CORS enabled** for frontend integration
- **Error isolation** - module failures don't crash system
- **Production ready** - includes proper error handling and logging