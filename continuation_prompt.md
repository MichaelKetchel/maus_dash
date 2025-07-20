# Continuation Prompt for Claude Project

## 🎯 Context for New Conversations

Use this prompt when starting new conversations in your Claude Project to maintain context and development momentum:

---

**Prompt:**

I'm continuing development on my custom dashboard system - a Python FastAPI backend with Vue.js frontend that provides real-time control and monitoring capabilities similar to TouchPortal or Stream Deck.

**Current Architecture:**
- **Backend**: FastAPI with Redis event bus, WebSocket manager, modular plugin system, and background workers
- **Frontend**: Vue 3 + Pinia + Tailwind CSS with auto-reconnecting WebSocket client
- **Communication**: Event-driven architecture with real-time bidirectional WebSocket communication
- **Deployment**: Development setup with uv (Python) and Vite (frontend)

**What's Already Built:**
- ✅ Complete FastAPI foundation with lifespan management
- ✅ Redis-backed event bus with pattern matching (`system.*`, `module.*`, `worker.*`)
- ✅ WebSocket manager with connection health and broadcasting
- ✅ Module loader for hot-pluggable functionality
- ✅ Background worker system (system monitor, heartbeat workers)
- ✅ Vue.js frontend with real-time dashboard
- ✅ System info module showing live CPU/memory metrics
- ✅ Dark/light theme with responsive design
- ✅ WebSocket client with auto-reconnection and event subscriptions

**Project Structure:**
```
dashboard/
├── backend/
│   ├── main.py                # FastAPI app with WebSocket endpoint
│   ├── core/                  # Event bus, WebSocket, module loader, workers
│   └── modules/               # Pluggable dashboard modules
└── frontend/
    ├── src/stores/            # WebSocket & dashboard Pinia stores  
    ├── src/components/        # Reusable UI components
    └── src/components/modules/ # Dashboard module components
```

**Development Environment:**
- Backend runs on `localhost:8000` (FastAPI + WebSocket)
- Frontend runs on `localhost:3000` (Vite dev server with proxy)
- Redis required for event bus functionality
- Real-time communication working between frontend and backend

**Next Development Goals:**
[Add your specific goals here, such as:]
- Create an app launcher module for controlling system applications
- Build media control module for audio/video control
- Add custom automation workflows
- Implement additional dashboard widgets
- Integrate with specific hardware or APIs

**Please help me:**
[State your specific request here]

---

## 🔧 Additional Context Prompts

### For Module Development:
> I want to create a new dashboard module called "[MODULE_NAME]" that [DESCRIPTION]. Please help me build both the backend module (following the BaseModule pattern) and the frontend Vue component. It should integrate with the existing event bus system and dashboard layout.

### For Frontend Features:
> I want to add [FEATURE] to the Vue.js frontend dashboard. This should integrate with the existing Pinia stores and follow the established WebSocket event patterns. Please ensure it works with the dark/light theme and responsive design.

### For Backend Extensions:
> I need to extend the FastAPI backend with [FUNCTIONALITY]. This should integrate with the existing event bus system and follow the established patterns for [modules/workers/routes]. Please ensure proper error handling and logging.

### For Architecture Questions:
> I have a question about the dashboard architecture: [SPECIFIC QUESTION]. Please explain how this works with the current event-driven system and suggest the best approach following established patterns.

### For Debugging Help:
> I'm experiencing [ISSUE] with [COMPONENT]. The current behavior is [DESCRIPTION]. Based on the established architecture, what could be causing this and how can I debug/fix it?

## 💡 Pro Tips for Project Conversations

1. **Reference existing patterns** - "following the BaseModule pattern" or "using the established event naming convention"

2. **Specify integration points** - mention which stores, components, or backend systems should be involved

3. **Include context about your setup** - OS (Windows/Linux), development environment, any specific requirements

4. **Be specific about scope** - whether you want just the code, explanation of how it fits into the architecture, or full implementation with testing

5. **Mention deployment context** - development vs production considerations, if relevant

This will help Claude understand exactly where you are in the project and maintain consistency with the patterns and architecture already established!