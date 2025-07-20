<template>
  <div class="bg-white dark:bg-dark-800 rounded-lg border border-gray-200 dark:border-dark-700 p-6">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-semibold text-gray-900 dark:text-white flex items-center space-x-2">
        <Activity class="w-5 h-5" />
        <span>Background Workers</span>
      </h3>

      <div class="flex items-center space-x-2">
        <button
          @click="refreshWorkers"
          :disabled="isLoading"
          class="p-2 rounded-lg bg-gray-100 dark:bg-dark-700 hover:bg-gray-200 dark:hover:bg-dark-600 transition-colors disabled:opacity-50"
          title="Refresh workers"
        >
          <RefreshCw
            class="w-4 h-4 text-gray-600 dark:text-gray-300"
            :class="{ 'animate-spin': isLoading }"
          />
        </button>
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="isLoading && !Object.keys(workers).length" class="flex items-center justify-center py-8">
      <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600"></div>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="text-center py-8">
      <AlertTriangle class="w-8 h-8 text-red-500 mx-auto mb-2" />
      <p class="text-sm text-red-600 dark:text-red-400">{{ error }}</p>
      <button
        @click="fetchWorkers"
        class="mt-2 text-xs px-3 py-1 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors"
      >
        Retry
      </button>
    </div>

    <!-- Workers content -->
    <div v-else-if="Object.keys(workers).length" class="space-y-3">
      <div
        v-for="(worker, name) in workers"
        :key="name"
        class="flex items-center justify-between p-3 bg-gray-50 dark:bg-dark-700 rounded-lg"
      >
        <div class="flex items-center space-x-3">
          <div 
            class="w-3 h-3 rounded-full"
            :class="{
              'bg-green-500': worker.running,
              'bg-red-500': !worker.running,
              'bg-yellow-500': worker.status === 'starting'
            }"
            :title="worker.running ? 'Running' : 'Stopped'"
          ></div>
          <div>
            <p class="font-medium text-gray-900 dark:text-white">{{ formatWorkerName(name) }}</p>
            <p class="text-xs text-gray-500 dark:text-gray-400">
              {{ worker.last_run ? `Last run: ${formatTimestamp(worker.last_run)}` : 'Never run' }}
            </p>
          </div>
        </div>

        <div class="flex items-center space-x-2">
          <!-- Worker stats -->
          <div class="text-xs text-gray-500 dark:text-gray-400 text-right">
            <div v-if="worker.run_count !== undefined">Runs: {{ worker.run_count }}</div>
            <div v-if="worker.error_count !== undefined && worker.error_count > 0" class="text-red-500">
              Errors: {{ worker.error_count }}
            </div>
          </div>

          <!-- Control buttons -->
          <button
            v-if="!worker.running"
            @click="startWorker(name)"
            :disabled="isWorkerActionLoading[name]"
            class="px-2 py-1 text-xs bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded hover:bg-green-200 dark:hover:bg-green-900/50 transition-colors disabled:opacity-50"
            title="Start worker"
          >
            <Play class="w-3 h-3" />
          </button>
          
          <button
            v-else
            @click="stopWorker(name)"
            :disabled="isWorkerActionLoading[name]"
            class="px-2 py-1 text-xs bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors disabled:opacity-50"
            title="Stop worker"
          >
            <Square class="w-3 h-3" />
          </button>

          <button
            @click="restartWorker(name)"
            :disabled="isWorkerActionLoading[name]"
            class="px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors disabled:opacity-50"
            title="Restart worker"
          >
            <RotateCcw class="w-3 h-3" />
          </button>
        </div>
      </div>

      <!-- Summary stats -->
      <div class="pt-3 border-t border-gray-200 dark:border-dark-700">
        <div class="flex justify-between text-sm text-gray-600 dark:text-gray-400">
          <span>{{ runningCount }} running</span>
          <span>{{ totalCount }} total workers</span>
        </div>
      </div>
    </div>

    <!-- No data state -->
    <div v-else class="text-center py-8">
      <Activity class="w-8 h-8 text-gray-400 mx-auto mb-2" />
      <p class="text-sm text-gray-500 dark:text-gray-400">No workers available</p>
      <button
        @click="fetchWorkers"
        class="mt-2 text-xs px-3 py-1 bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded hover:bg-primary-200 dark:hover:bg-primary-900/50 transition-colors"
      >
        Load Workers
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import {
  Activity, RefreshCw, AlertTriangle, Play, Square, RotateCcw
} from 'lucide-vue-next'
import { useWebSocketStore } from '@/stores/websocket'
import { useDashboardStore } from '@/stores/dashboard'

// Stores
const wsStore = useWebSocketStore()
const dashboardStore = useDashboardStore()

// State
const workers = ref({})
const isLoading = ref(false)
const error = ref(null)
const isWorkerActionLoading = ref({})

// Computed
const runningCount = computed(() => {
  return Object.values(workers.value).filter(worker => worker.running).length
})

const totalCount = computed(() => {
  return Object.keys(workers.value).length
})

// Methods
const fetchWorkers = async () => {
  try {
    isLoading.value = true
    error.value = null

    // Request workers status via WebSocket
    wsStore.send({
      type: 'system.status_request',
      payload: {}
    })
  } catch (err) {
    console.error('Error fetching workers:', err)
    error.value = err.message
  } finally {
    isLoading.value = false
  }
}

const refreshWorkers = () => {
  fetchWorkers()
}

const startWorker = async (workerName) => {
  try {
    isWorkerActionLoading.value[workerName] = true
    
    wsStore.send({
      type: 'worker.start',
      payload: { worker_name: workerName }
    })

    // Update local state optimistically
    if (workers.value[workerName]) {
      workers.value[workerName].running = true
    }
  } catch (err) {
    console.error('Error starting worker:', err)
    error.value = `Failed to start worker: ${err.message}`
  } finally {
    setTimeout(() => {
      isWorkerActionLoading.value[workerName] = false
    }, 1000)
  }
}

const stopWorker = async (workerName) => {
  try {
    isWorkerActionLoading.value[workerName] = true
    
    wsStore.send({
      type: 'worker.stop',
      payload: { worker_name: workerName }
    })

    // Update local state optimistically
    if (workers.value[workerName]) {
      workers.value[workerName].running = false
    }
  } catch (err) {
    console.error('Error stopping worker:', err)
    error.value = `Failed to stop worker: ${err.message}`
  } finally {
    setTimeout(() => {
      isWorkerActionLoading.value[workerName] = false
    }, 1000)
  }
}

const restartWorker = async (workerName) => {
  try {
    isWorkerActionLoading.value[workerName] = true
    
    wsStore.send({
      type: 'worker.restart',
      payload: { worker_name: workerName }
    })
  } catch (err) {
    console.error('Error restarting worker:', err)
    error.value = `Failed to restart worker: ${err.message}`
  } finally {
    setTimeout(() => {
      isWorkerActionLoading.value[workerName] = false
    }, 2000) // Longer timeout for restart
  }
}

const formatWorkerName = (name) => {
  return name.split('_').map(word => 
    word.charAt(0).toUpperCase() + word.slice(1)
  ).join(' ')
}

const formatTimestamp = (timestamp) => {
  if (!timestamp) return 'Never'
  return new Date(timestamp).toLocaleTimeString()
}

// WebSocket event handlers
let unsubscribeStatusResponse
let unsubscribeWorkerEvents

onMounted(() => {
  // Fetch initial data
  fetchWorkers()

  // Subscribe to status updates
  unsubscribeStatusResponse = wsStore.on('system.status_response', (data) => {
    if (data.workers) {
      workers.value = data.workers
      // Update dashboard store as well
      dashboardStore.workers = data.workers
    }
  })

  // Subscribe to worker events
  unsubscribeWorkerEvents = wsStore.on('worker.*', (data, eventType) => {
    console.log('Worker event:', eventType, data)
    
    // Refresh workers on any worker event
    setTimeout(fetchWorkers, 500)
  })

  // Use dashboard store workers if available
  if (dashboardStore.workers && Object.keys(dashboardStore.workers).length > 0) {
    workers.value = dashboardStore.workers
  }
})

onUnmounted(() => {
  if (unsubscribeStatusResponse) unsubscribeStatusResponse()
  if (unsubscribeWorkerEvents) unsubscribeWorkerEvents()
})
</script>