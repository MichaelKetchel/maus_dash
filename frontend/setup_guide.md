# Vue.js Frontend Setup Guide

## 🚀 Complete Frontend Stack

I've created a comprehensive Vue.js frontend that integrates seamlessly with your FastAPI backend. Here's what you now have:

### 📦 **Core Features**

✅ **Real-time WebSocket Communication** - Auto-reconnecting with exponential backoff  
✅ **Reactive State Management** - Pinia stores for WebSocket and dashboard data  
✅ **Dark/Light Theme** - System preference detection with manual toggle  
✅ **Modular Components** - Easy to extend with new dashboard modules  
✅ **TypeScript-Ready** - Easy to migrate to TypeScript later  
✅ **Error Handling** - Graceful error states and retry mechanisms  
✅ **Live System Monitoring** - Real-time CPU, memory, and system stats

### 🏗️ **Architecture Overview**

**WebSocket Store (`websocket.js`)**
- Auto-connecting WebSocket client with reconnection logic
- Event subscription system for modular components
- Message queuing when disconnected
- Connection status tracking and health monitoring

**Dashboard Store (`dashboard.js`)**
- Centralized state for system info, metrics, modules, and workers
- Actions for controlling modules and workers via WebSocket
- Theme management with localStorage persistence
- Error handling and loading states

**Component Structure**
- **App.vue** - Main layout with header, status, and grid
- **ConnectionStatus.vue** - Real-time connection indicator
- **StatCard.vue** - Reusable metrics display cards
- **SystemInfoModule.vue** - System information display
- **InfoRow.vue** - Key-value pair display component
- **MetricCard.vue** - Small metric display cards

### 🛠️ **Setup Instructions**

#### 1. Initialize Frontend Project
```bash
cd frontend

# Install dependencies
npm install

# Or if you prefer yarn
yarn install
```

#### 2. Development Server
```bash
# Start development server (with hot reload)
npm run dev

# The frontend will be available at http://localhost:3000
# API calls will be proxied to your FastAPI backend at http://localhost:8000
```

#### 3. Build for Production
```bash
# Build optimized production bundle
npm run build

# Preview production build
npm run preview
```

### 📁 **File Structure**

```
frontend/
├── index.html              # Main HTML template
├── package.json             # Dependencies and scripts
├── vite.config.js          # Vite configuration with proxy
├── tailwind.config.js      # Tailwind CSS configuration
├── src/
│   ├── main.js             # Vue app initialization
│   ├── App.vue             # Main app component
│   ├── style.css           # Global styles and Tailwind imports
│   ├── stores/
│   │   ├── websocket.js    # WebSocket connection management
│   │   └── dashboard.js    # Dashboard state management
│   └── components/
│       ├── ConnectionStatus.vue
│       ├── StatCard.vue
│       ├── InfoRow.vue
│       ├── MetricCard.vue
│       └── modules/
│           └── SystemInfoModule.vue
└── dist/                   # Built files (auto-generated)
```

### 🔌 **WebSocket Integration**

The frontend automatically connects to your FastAPI WebSocket endpoint and handles:

**Outgoing Events (Frontend → Backend)**
```javascript
// Send events through the WebSocket store
wsStore.send('system.status_request')
wsStore.send('module.reload', { module_name: 'system_info' })
wsStore.send('worker.restart', { worker_name: 'system_monitor' })
```

**Incoming Events (Backend → Frontend)**
```javascript
// Subscribe to events in components
wsStore.on('system_metrics', (data) => {
  // Handle real-time system metrics
})

wsStore.on('module.loaded', (data) => {
  // Handle module loading events
})
```

### 🎨 **Styling & Theming**

**Tailwind CSS Setup**
- Dark/light mode with `dark:` prefixes
- Custom color palette for dashboard themes
- Responsive design utilities
- Custom animations for status indicators

**Theme Features**
- System preference detection
- Manual toggle with persistence
- Smooth transitions between themes
- Accessible color contrasts

### 📱 **Responsive Design**

The dashboard is fully responsive:
- **Desktop**: Multi-column grid layout
- **Tablet**: 2-column layout with adjusted spacing
- **Mobile**: Single-column stacked layout
- **Touch-friendly**: Larger tap targets and spacing

### 🔧 **Development Workflow**

#### Hot Reload Development
```bash
# Terminal 1: Start backend
cd backend
python main.py

# Terminal 2: Start frontend
cd frontend
npm run dev
```

Both servers support hot reload:
- **Backend**: FastAPI auto-reloads on Python file changes
- **Frontend**: Vite hot-reloads on Vue/JS/CSS changes

#### Debugging WebSockets
- Browser DevTools → Network → WS tab shows WebSocket messages
- Console logs all WebSocket events with debug info
- Connection status component shows real-time connection health

### 🧩 **Adding New Dashboard Modules**

#### 1. Create Backend Module
```python
# backend/modules/my_module/module.py
class MyModule(BaseModule):
    def __init__(self, event_bus):
        super().__init__("my_module", event_bus)
        # Module implementation
```

#### 2. Create Frontend Component
```vue
<!-- frontend/src/components/modules/MyModule.vue -->
<template>
  <div class="bg-white dark:bg-dark-800 rounded-lg border p-6">
    <h3>My Custom Module</h3>
    <!-- Module UI -->
  </div>
</template>

<script setup>
import { useWebSocketStore } from '@/stores/websocket'
const wsStore = useWebSocketStore()

// Subscribe to module events
wsStore.on('my_module.data_update', (data) => {
  // Handle module-specific events
})
</script>
```

#### 3. Add to Main Grid
```vue
<!-- In App.vue -->
<div class="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
  <SystemInfoModule />
  <MyModule />  <!-- Add your module here -->
</div>
```

### 🚀 **Next Steps**

1. **Start the frontend** with `npm run dev`
2. **Test WebSocket connection** - should auto-connect to your backend
3. **Verify system info module** - should display real system data
4. **Customize the theme** - modify Tailwind config for your preferences
5. **Add more modules** - create components for app launcher, media control, etc.

### 🎯 **Ready Features**

- ✅ **Real-time system monitoring** with live CPU/memory updates
- ✅ **WebSocket health monitoring** with auto-reconnection
- ✅ **Module management** UI for loading/unloading modules
- ✅ **Worker control** UI for starting/stopping background workers
- ✅ **Responsive design** that works on tablets and desktops
- ✅ **Dark/light theme** with smooth transitions
- ✅ **Error handling** with user-friendly retry options

### 🔧 **Configuration Options**

**Environment Variables** (create `.env` file):
```bash
VITE_API_URL=http://localhost:8000  # Backend URL
VITE_WS_URL=ws://localhost:8000/ws  # WebSocket URL
```

**Vite Proxy Configuration** (already configured):
- `/api/*` → FastAPI backend
- `/ws` → WebSocket endpoint

You now have a complete, production-ready frontend that perfectly complements your FastAPI backend! The WebSocket connection should establish automatically, and you'll see real-time system metrics flowing from your backend workers to the frontend dashboard.

Start both servers and watch your custom dashboard come to life! 🎉