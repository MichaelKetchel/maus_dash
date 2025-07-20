<template>
  <div class="bg-white dark:bg-dark-800 rounded-lg border border-gray-200 dark:border-dark-700 p-6">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-semibold text-gray-900 dark:text-white flex items-center space-x-2">
        <BarChart3 class="w-5 h-5" />
        <span>Real-time Metrics</span>
      </h3>

      <div class="flex items-center space-x-2">
        <!-- Auto-refresh toggle -->
        <button
          @click="toggleAutoRefresh"
          class="p-2 rounded-lg transition-colors"
          :class="{
            'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300': autoRefresh,
            'bg-gray-100 dark:bg-dark-700 text-gray-600 dark:text-gray-300': !autoRefresh
          }"
          :title="autoRefresh ? 'Disable auto-refresh' : 'Enable auto-refresh'"
        >
          <Timer class="w-4 h-4" />
        </button>

        <button
          @click="refreshMetrics"
          :disabled="isLoading"
          class="p-2 rounded-lg bg-gray-100 dark:bg-dark-700 hover:bg-gray-200 dark:hover:bg-dark-600 transition-colors disabled:opacity-50"
          title="Refresh metrics"
        >
          <RefreshCw
            class="w-4 h-4 text-gray-600 dark:text-gray-300"
            :class="{ 'animate-spin': isLoading }"
          />
        </button>
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="isLoading && !metrics" class="flex items-center justify-center py-8">
      <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600"></div>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="text-center py-8">
      <AlertTriangle class="w-8 h-8 text-red-500 mx-auto mb-2" />
      <p class="text-sm text-red-600 dark:text-red-400">{{ error }}</p>
      <button
        @click="fetchMetrics"
        class="mt-2 text-xs px-3 py-1 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors"
      >
        Retry
      </button>
    </div>

    <!-- Metrics content -->
    <div v-else-if="metrics" class="space-y-4">
      <!-- CPU and Memory Grid -->
      <div class="grid grid-cols-2 gap-4">
        <MetricCard
          label="CPU Usage"
          :value="`${(metrics.cpu_percent || 0).toFixed(1)}%`"
          :color="getMetricColor(metrics.cpu_percent, [50, 80])"
          icon="Cpu"
        />
        <MetricCard
          label="Memory"
          :value="`${(metrics.memory?.percent || 0).toFixed(1)}%`"
          :color="getMetricColor(metrics.memory?.percent, [70, 90])"
          icon="HardDrive"
        />
      </div>

      <!-- Detailed Memory Info -->
      <div v-if="metrics.memory" class="space-y-2">
        <h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center space-x-2">
          <HardDrive class="w-4 h-4" />
          <span>Memory Details</span>
        </h4>
        
        <div class="grid grid-cols-2 gap-3 text-xs">
          <div class="flex justify-between">
            <span class="text-gray-600 dark:text-gray-400">Used:</span>
            <span class="font-medium">{{ formatBytes(metrics.memory.used) }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-600 dark:text-gray-400">Available:</span>
            <span class="font-medium">{{ formatBytes(metrics.memory.available) }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-600 dark:text-gray-400">Total:</span>
            <span class="font-medium">{{ formatBytes(metrics.memory.total) }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-600 dark:text-gray-400">Free:</span>
            <span class="font-medium">{{ formatBytes(metrics.memory.free) }}</span>
          </div>
        </div>
      </div>

      <!-- Disk Usage -->
      <div v-if="metrics.disk" class="space-y-2">
        <h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center space-x-2">
          <Database class="w-4 h-4" />
          <span>Disk Usage</span>
        </h4>

        <div class="space-y-2">
          <div
            v-for="(disk, path) in metrics.disk"
            :key="path"
            class="flex items-center justify-between p-2 bg-gray-50 dark:bg-dark-700 rounded"
          >
            <div>
              <p class="text-sm font-medium">{{ path === '/' ? 'Root' : path }}</p>
              <p class="text-xs text-gray-500">{{ formatBytes(disk.used) }} / {{ formatBytes(disk.total) }}</p>
            </div>
            <div class="text-right">
              <div 
                class="text-sm font-medium"
                :class="{
                  'text-green-600': disk.percent < 70,
                  'text-yellow-600': disk.percent >= 70 && disk.percent < 90,
                  'text-red-600': disk.percent >= 90
                }"
              >
                {{ disk.percent.toFixed(1) }}%
              </div>
              <div class="text-xs text-gray-500">{{ formatBytes(disk.free) }} free</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Network Info -->
      <div v-if="metrics.network" class="space-y-2">
        <h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center space-x-2">
          <Wifi class="w-4 h-4" />
          <span>Network</span>
        </h4>

        <div class="grid grid-cols-2 gap-3 text-xs">
          <div class="flex justify-between">
            <span class="text-gray-600 dark:text-gray-400">Sent:</span>
            <span class="font-medium">{{ formatBytes(metrics.network.bytes_sent) }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-600 dark:text-gray-400">Received:</span>
            <span class="font-medium">{{ formatBytes(metrics.network.bytes_recv) }}</span>
          </div>
        </div>
      </div>

      <!-- Update info -->
      <div class="pt-3 border-t border-gray-200 dark:border-dark-700">
        <div class="flex justify-between items-center text-xs text-gray-500 dark:text-gray-400">
          <span>Last updated: {{ formatTimestamp(metrics.timestamp || lastUpdate) }}</span>
          <div v-if="autoRefresh" class="flex items-center space-x-1">
            <div class="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            <span>Auto-refresh</span>
          </div>
        </div>
      </div>
    </div>

    <!-- No data state -->
    <div v-else class="text-center py-8">
      <BarChart3 class="w-8 h-8 text-gray-400 mx-auto mb-2" />
      <p class="text-sm text-gray-500 dark:text-gray-400">No metrics available</p>
      <button
        @click="fetchMetrics"
        class="mt-2 text-xs px-3 py-1 bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded hover:bg-primary-200 dark:hover:bg-primary-900/50 transition-colors"
      >
        Load Metrics
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import {
  BarChart3, RefreshCw, AlertTriangle, Timer, Cpu, HardDrive,
  Database, Wifi
} from 'lucide-vue-next'
import { useWebSocketStore } from '@/stores/websocket'
import { useDashboardStore } from '@/stores/dashboard'

// Components
import MetricCard from '@/components/MetricCard.vue'

// Stores
const wsStore = useWebSocketStore()
const dashboardStore = useDashboardStore()

// State
const metrics = ref(null)
const isLoading = ref(false)
const error = ref(null)
const autoRefresh = ref(true)
const lastUpdate = ref(null)
const refreshInterval = ref(null)

// Methods
const fetchMetrics = async () => {
  try {
    isLoading.value = true
    error.value = null

    // Try API first
    const response = await fetch('/api/system_info/metrics')
    if (response.ok) {
      const data = await response.json()
      metrics.value = data
      lastUpdate.value = new Date()
    } else {
      // Fallback to WebSocket request
      wsStore.send({
        type: 'system.metrics_request',
        payload: {}
      })
    }
  } catch (err) {
    console.warn('Error fetching metrics via API, trying WebSocket:', err)
    // Fallback to WebSocket
    wsStore.send({
      type: 'system.metrics_request',
      payload: {}
    })
  } finally {
    isLoading.value = false
  }
}

const refreshMetrics = () => {
  fetchMetrics()
}

const toggleAutoRefresh = () => {
  autoRefresh.value = !autoRefresh.value
  
  if (autoRefresh.value) {
    startAutoRefresh()
  } else {
    stopAutoRefresh()
  }
}

const startAutoRefresh = () => {
  stopAutoRefresh() // Clear any existing interval
  
  refreshInterval.value = setInterval(() => {
    if (autoRefresh.value) {
      fetchMetrics()
    }
  }, 5000) // Refresh every 5 seconds
}

const stopAutoRefresh = () => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
    refreshInterval.value = null
  }
}

const formatBytes = (bytes) => {
  if (!bytes) return '0 B'
  
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let size = bytes
  let unitIndex = 0
  
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex++
  }
  
  return `${size.toFixed(1)} ${units[unitIndex]}`
}

const formatTimestamp = (timestamp) => {
  if (!timestamp) return 'Never'
  return new Date(timestamp).toLocaleTimeString()
}

const getMetricColor = (value, thresholds) => {
  if (!value) return 'gray'
  if (value < thresholds[0]) return 'green'
  if (value < thresholds[1]) return 'yellow'
  return 'red'
}

// WebSocket event handlers
let unsubscribeMetrics
let unsubscribeSystemMetrics

onMounted(() => {
  // Fetch initial data
  fetchMetrics()

  // Start auto-refresh if enabled
  if (autoRefresh.value) {
    startAutoRefresh()
  }

  // Subscribe to real-time metrics updates
  unsubscribeSystemMetrics = wsStore.on('system_metrics', (data) => {
    metrics.value = data
    lastUpdate.value = new Date()
    
    // Also update dashboard store
    dashboardStore.systemMetrics = data
  })

  // Subscribe to metrics response
  unsubscribeMetrics = wsStore.on('system.metrics_response', (data) => {
    metrics.value = data
    lastUpdate.value = new Date()
  })

  // Use dashboard store metrics if available
  if (dashboardStore.systemMetrics && Object.keys(dashboardStore.systemMetrics).length > 0) {
    metrics.value = dashboardStore.systemMetrics
  }
})

onUnmounted(() => {
  stopAutoRefresh()
  
  if (unsubscribeMetrics) unsubscribeMetrics()
  if (unsubscribeSystemMetrics) unsubscribeSystemMetrics()
})
</script>