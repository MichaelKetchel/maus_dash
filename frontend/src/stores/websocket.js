import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useWebSocketStore = defineStore('websocket', () => {
  // State
  const ws = ref(null)
  const isConnected = ref(false)
  const isConnecting = ref(false)
  const clientId = ref(null)
  const lastPing = ref(null)
  const reconnectAttempts = ref(0)
  const maxReconnectAttempts = ref(10)
  const reconnectDelay = ref(1000)
  const eventHandlers = ref(new Map())
  const messageQueue = ref([])

  // Computed
  const connectionStatus = computed(() => {
    if (isConnected.value) return 'connected'
    if (isConnecting.value) return 'connecting'
    return 'disconnected'
  })

  const canReconnect = computed(() => {
    return reconnectAttempts.value < maxReconnectAttempts.value
  })

  // Actions
  const connect = async (url = null) => {
    if (ws.value && isConnected.value) {
      console.warn('WebSocket already connected')
      return
    }

    const wsUrl = url || `ws://${window.location.hostname}:8000/ws`
    
    try {
      isConnecting.value = true
      ws.value = new WebSocket(wsUrl)

      ws.value.onopen = handleOpen
      ws.value.onmessage = handleMessage
      ws.value.onclose = handleClose
      ws.value.onerror = handleError

      console.log(`Connecting to WebSocket: ${wsUrl}`)
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
      isConnecting.value = false
    }
  }

  const disconnect = () => {
    if (ws.value) {
      ws.value.close(1000, 'Client disconnecting')
    }
  }

  const send = (type, payload = {}, target = null) => {
    const message = {
      type,
      payload,
      ...(target && { target })
    }

    if (isConnected.value && ws.value.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify(message))
      console.debug('Sent message:', message)
    } else {
      // Queue message for when connection is restored
      messageQueue.value.push(message)
      console.warn('WebSocket not connected, message queued:', message)
    }
  }

  const subscribe = (eventType, handler) => {
    if (!eventHandlers.value.has(eventType)) {
      eventHandlers.value.set(eventType, new Set())
    }
    eventHandlers.value.get(eventType).add(handler)

    // Send subscription request to server
    send('websocket.subscribe', {
      event_types: [eventType]
    })

    // Return unsubscribe function
    return () => {
      unsubscribe(eventType, handler)
    }
  }

  const unsubscribe = (eventType, handler = null) => {
    if (handler) {
      const handlers = eventHandlers.value.get(eventType)
      if (handlers) {
        handlers.delete(handler)
        if (handlers.size === 0) {
          eventHandlers.value.delete(eventType)
        }
      }
    } else {
      eventHandlers.value.delete(eventType)
    }

    // Send unsubscription request to server
    send('websocket.unsubscribe', {
      event_types: handler ? [] : [eventType]
    })
  }

  const on = (eventType, handler) => {
    return subscribe(eventType, handler)
  }

  const off = (eventType, handler = null) => {
    unsubscribe(eventType, handler)
  }

  // Event Handlers
  const handleOpen = (event) => {
    console.log('WebSocket connected')
    isConnected.value = true
    isConnecting.value = false
    reconnectAttempts.value = 0

    // Send queued messages
    while (messageQueue.value.length > 0) {
      const message = messageQueue.value.shift()
      ws.value.send(JSON.stringify(message))
    }
  }

  const handleMessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      console.debug('Received message:', data)

      // Handle different message types
      switch (data.type) {
        case 'connection.welcome':
          clientId.value = data.payload.client_id
          console.log('Received client ID:', clientId.value)
          break

        case 'ping':
          lastPing.value = new Date(data.payload.timestamp)
          // Send pong response
          send('pong', { timestamp: new Date().toISOString() })
          break

        case 'event':
          // Handle subscribed events
          const eventType = data.payload.event_type
          const eventData = data.payload.data
          handleEvent(eventType, eventData)
          break

        case 'error':
          console.error('Server error:', data.payload.message)
          break

        default:
          // Handle direct events
          handleEvent(data.type, data.payload)
      }
    } catch (error) {
      console.error('Error parsing WebSocket message:', error, event.data)
    }
  }

  const handleEvent = (eventType, data) => {
    const handlers = eventHandlers.value.get(eventType)
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(data)
        } catch (error) {
          console.error(`Error in event handler for ${eventType}:`, error)
        }
      })
    }
  }

  const handleClose = (event) => {
    console.log('WebSocket disconnected:', event.code, event.reason)
    isConnected.value = false
    isConnecting.value = false
    ws.value = null
    clientId.value = null

    // Attempt reconnection if not a clean close
    if (event.code !== 1000 && canReconnect.value) {
      scheduleReconnect()
    }
  }

  const handleError = (error) => {
    console.error('WebSocket error:', error)
    isConnecting.value = false
  }

  const scheduleReconnect = () => {
    if (!canReconnect.value) {
      console.warn('Max reconnection attempts reached')
      return
    }

    const delay = Math.min(reconnectDelay.value * Math.pow(2, reconnectAttempts.value), 30000)
    console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttempts.value + 1})`)

    setTimeout(() => {
      reconnectAttempts.value++
      connect()
    }, delay)
  }

  // Initialize connection on store creation
  const initialize = () => {
    if (typeof window !== 'undefined') {
      connect()
      
      // Handle page visibility changes
      document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible' && !isConnected.value) {
          connect()
        }
      })

      // Handle online/offline events
      window.addEventListener('online', () => {
        if (!isConnected.value) {
          connect()
        }
      })
    }
  }

  return {
    // State
    isConnected,
    isConnecting,
    clientId,
    lastPing,
    reconnectAttempts,
    connectionStatus,
    canReconnect,

    // Actions
    connect,
    disconnect,
    send,
    subscribe,
    unsubscribe,
    on,
    off,
    initialize
  }
})