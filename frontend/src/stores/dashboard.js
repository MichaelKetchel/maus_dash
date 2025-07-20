import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useWebSocketStore } from './websocket'

export const useDashboardStore = defineStore('dashboard', () => {
  // State
  const systemInfo = ref({})
  const systemMetrics = ref({})
  const modules = ref({})
  const workers = ref({})
  const isLoading = ref(false)
  const error = ref(null)
  const lastUpdate = ref(null)
  const isDarkMode = ref(false)

  // Get WebSocket store
  const wsStore = useWebSocketStore()

  // Computed
  const isSystemHealthy = computed(() => {
    return systemMetrics.value.cpu_percent < 80 && 
           systemMetrics.value.memory_percent < 90
  })

  const activeModulesCount = computed(() => {
    return Object.values(modules.value).filter(module => module.loaded).length
  })

  const runningWorkersCount = computed(() => {
    return Object.values(workers.value).filter(worker => worker.running).length
  })

  // Actions
  const initialize = async () => {
    console.log('Initializing dashboard store')
    
    // Set up WebSocket event handlers
    setupEventHandlers()
    
    // Load initial data
    await fetchSystemStatus()
    
    // Set up periodic updates
    startPeriodicUpdates()
  }

  const setupEventHandlers = () => {
    // System metrics updates
    wsStore.on('system_metrics', (data) => {
      systemMetrics.value = data
      lastUpdate.value = new Date()
      console.debug('Updated system metrics:', data)
    })

    // System status updates
    wsStore.on('system.status_response', (data) => {
      updateSystemStatus(data)
    })

    // Module events
    wsStore.on('module.loaded', (data) => {
      if (modules.value[data.module_name]) {
        modules.value[data.module_name] = {
          ...modules.value[data.module_name],
          ...data.module_info,
          loaded: true
        }
      }
    })

    wsStore.on('module.unloaded', (data) => {
      if (modules.value[data.module_name]) {
        modules.value[data.module_name].loaded = false
      }
    })

    // Worker events
    wsStore.on('worker.started', (data) => {
      if (workers.value[data.worker_name]) {
        workers.value[data.worker_name].running = true
      }
    })

    wsStore.on('worker.stopped', (data) => {
      if (workers.value[data.worker_name]) {
        workers.value[data.worker_name].running = false
      }
    })

    wsStore.on('worker.error', (data) => {
      console.error(`Worker ${data.worker_name} error:`, data.error)
      if (workers.value[data.worker_name]) {
        workers.value[data.worker_name].error_count = data.error_count
        workers.value[data.worker_name].last_error = data.error
      }
    })

    // System info updates (from system_info module)
    wsStore.on('system_info.updated', (data) => {
      systemInfo.value = { ...systemInfo.value, ...data }
    })

    // Heartbeat
    wsStore.on('system.heartbeat', (data) => {
      lastUpdate.value = new Date(data.timestamp)
    })
  }

  const fetchSystemStatus = async () => {
    try {
      isLoading.value = true
      error.value = null

      // Fetch via REST API
      const response = await fetch('/api/status')
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data = await response.json()
      updateSystemStatus(data)

    } catch (err) {
      console.error('Failed to fetch system status:', err)
      error.value = err.message
    } finally {
      isLoading.value = false
    }
  }

  const updateSystemStatus = (data) => {
    modules.value = data.modules || {}
    workers.value = data.workers || {}
    lastUpdate.value = new Date()
  }

  const requestSystemStatus = () => {
    wsStore.send('system.status_request')
  }

  const startPeriodicUpdates = () => {
    // Request status updates every 30 seconds
    setInterval(() => {
      if (wsStore.isConnected) {
        requestSystemStatus()
      }
    }, 30000)
  }

  // Module actions
  const reloadModule = (moduleName) => {
    wsStore.send('module.reload', { module_name: moduleName })
  }

  const unloadModule = (moduleName) => {
    wsStore.send('module.unload', { module_name: moduleName })
  }

  // Worker actions
  const startWorker = (workerName) => {
    wsStore.send('worker.start', { worker_name: workerName })
  }

  const stopWorker = (workerName) => {
    wsStore.send('worker.stop', { worker_name: workerName })
  }

  const restartWorker = (workerName) => {
    wsStore.send('worker.restart', { worker_name: workerName })
  }

  // System actions
  const refreshSystemInfo = () => {
    wsStore.send('system_info.refresh_requested')
  }

  // Theme management
  const toggleDarkMode = () => {
    isDarkMode.value = !isDarkMode.value
    updateTheme()
  }

  const setDarkMode = (enabled) => {
    isDarkMode.value = enabled
    updateTheme()
  }

  const updateTheme = () => {
    if (typeof window !== 'undefined') {
      const html = document.documentElement
      if (isDarkMode.value) {
        html.classList.add('dark')
        localStorage.setItem('darkMode', 'true')
      } else {
        html.classList.remove('dark')
        localStorage.setItem('darkMode', 'false')
      }
    }
  }

  const initializeTheme = () => {
    if (typeof window !== 'undefined') {
      const savedTheme = localStorage.getItem('darkMode')
      if (savedTheme !== null) {
        isDarkMode.value = savedTheme === 'true'
      } else {
        // Default to system preference
        isDarkMode.value = window.matchMedia('(prefers-color-scheme: dark)').matches
      }
      updateTheme()
    }
  }

  // Error handling
  const clearError = () => {
    error.value = null
  }

  const handleError = (errorMessage) => {
    error.value = errorMessage
    console.error('Dashboard error:', errorMessage)
  }

  return {
    // State
    systemInfo,
    systemMetrics,
    modules,
    workers,
    isLoading,
    error,
    lastUpdate,
    isDarkMode,

    // Computed
    isSystemHealthy,
    activeModulesCount,
    runningWorkersCount,

    // Actions
    initialize,
    fetchSystemStatus,
    requestSystemStatus,
    reloadModule,
    unloadModule,
    startWorker,
    stopWorker,
    restartWorker,
    refreshSystemInfo,
    toggleDarkMode,
    setDarkMode,
    initializeTheme,
    clearError,
    handleError
  }
})