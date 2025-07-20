<template>
  <div class="bg-white dark:bg-dark-800 rounded-lg border border-gray-200 dark:border-dark-700 p-6">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-semibold text-gray-900 dark:text-white flex items-center space-x-2">
        <Server class="w-5 h-5" />
        <span>System Information</span>
      </h3>

      <div class="flex items-center space-x-2">
        <button
          @click="refreshSystemInfo"
          :disabled="isLoading"
          class="p-2 rounded-lg bg-gray-100 dark:bg-dark-700 hover:bg-gray-200 dark:hover:bg-dark-600 transition-colors disabled:opacity-50"
          title="Refresh system info"
        >
          <RefreshCw
            class="w-4 h-4 text-gray-600 dark:text-gray-300"
            :class="{ 'animate-spin': isLoading }"
          />
        </button>
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="isLoading && !systemInfo" class="flex items-center justify-center py-8">
      <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600"></div>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="text-center py-8">
      <AlertTriangle class="w-8 h-8 text-red-500 mx-auto mb-2" />
      <p class="text-sm text-red-600 dark:text-red-400">{{ error }}</p>
      <button
        @click="fetchSystemInfo"
        class="mt-2 text-xs px-3 py-1 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors"
      >
        Retry
      </button>
    </div>

    <!-- System info content -->
    <div v-else-if="systemInfo" class="space-y-4">
      <!-- Basic info -->
      <div class="grid grid-cols-1 gap-3">
        <InfoRow
          label="Hostname"
          :value="systemInfo.hostname"
          icon="Server"
        />
        <InfoRow
          label="Platform"
          :value="systemInfo.platform"
          icon="Monitor"
        />
        <InfoRow
          label="Python Version"
          :value="formatPythonVersion(systemInfo.python_version)"
          icon="Code"
        />
        <InfoRow
          label="Uptime"
          :value="formatUptime(systemInfo.uptime)"
          icon="Clock"
        />
      </div>

      <!-- Metrics (if available) -->
      <div v-if="metrics" class="pt-4 border-t border-gray-200 dark:border-dark-700">
        <h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3 flex items-center space-x-2">
          <Activity class="w-4 h-4" />
          <span>Live Metrics</span>
        </h4>

        <div class="grid grid-cols-2 gap-4">
          <MetricCard
            label="CPU"
            :value="`${metrics.cpu_percent?.toFixed(1)}%`"
            :color="getMetricColor(metrics.cpu_percent, [50, 80])"
          />
          <MetricCard
            label="Memory"
            :value="`${metrics.memory?.percent?.toFixed(1)}%`"
            :color="getMetricColor(metrics.memory?.percent, [70, 90])"
          />
        </div>
      </div>

      <!-- Last updated -->
      <div class="text-xs text-gray-500 dark:text-gray-400 text-center pt-3 border-t border-gray-200 dark:border-dark-700">
        Last updated: {{ formatTimestamp(systemInfo.timestamp) }}
      </div>
    </div>

    <!-- No data state -->
    <div v-else class="text-center py-8">
      <Server class="w-8 h-8 text-gray-400 mx-auto mb-2" />
      <p class="text-sm text-gray-500 dark:text-gray-400">No system information available</p>
      <button
        @click="fetchSystemInfo"
        class="mt-2 text-xs px-3 py-1 bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded hover:bg-primary-200 dark:hover:bg-primary-900/50 transition-colors"
      >
        Load Info
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import {
  Server, RefreshCw, AlertTriangle, Activity,
  Monitor, Code, Clock
} from 'lucide-vue-next'
import { useWebSocketStore } from '@/stores/websocket'
import { useDashboardStore } from '@/stores/dashboard'

// Components
import InfoRow from '@/components/InfoRow.vue'
import MetricCard from '@/components/MetricCard.vue'

// Stores
const wsStore = useWebSocketStore()
const dashboardStore = useDashboardStore()

// State
const systemInfo = ref(null)
const metrics = ref(null)
const isLoading = ref(false)
const error = ref(null)

// Computed
const formattedSystemInfo = computed(() => {
  if (!systemInfo.value) return null
  return {
    ...systemInfo.value,
    uptime: formatUptime(systemInfo.value.uptime),
    python_version: formatPythonVersion(systemInfo.value.python_version)
  }
})

// Methods
const fetchSystemInfo = async () => {
  try {
    isLoading.value = true
    error.value = null

    const response = await fetch('/api/system_info/info')
    if (!response.ok) {
      throw new Error(`Failed to fetch system info: ${response.statusText}`)
    }

    systemInfo.value = await response.json()
  } catch (err) {
    console.error('Error fetching system info:', err)
    error.value = err.message
  } finally {
    isLoading.value = false
  }
}

const fetchMetrics = async () => {
  try {
    const response = await fetch('/api/system_info/metrics')
    if (response.ok) {
      metrics.value = await response.json()
    }
  } catch (err) {
    console.warn('Could not fetch metrics:', err)
  }
}

const refreshSystemInfo = () => {
  dashboardStore.refreshSystemInfo()
  fetchSystemInfo()
  fetchMetrics()
}

const formatUptime = (seconds) => {
  if (!seconds) return 'Unknown'

  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)

  if (days > 0) {
    return `${days}d ${hours}h ${minutes}m`
  } else if (hours > 0) {
    return `${hours}h ${minutes}m`
  } else {
    return `${minutes}m`
  }
}

const formatPythonVersion = (version) => {
  if (!version) return 'Unknown'
  // Extract just the version number from full version string
  const match = version.match(/(\d+\.\d+\.\d+)/)
  return match ? match[1] : version.split(' ')[0]
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
let unsubscribeSystemInfo
let unsubscribeMetrics

onMounted(() => {
  // Fetch initial data
  fetchSystemInfo()
  fetchMetrics()

  // Subscribe to real-time updates
  unsubscribeSystemInfo = wsStore.on('system_info.updated', (data) => {
    if (systemInfo.value) {
      systemInfo.value = { ...systemInfo.value, ...data }
    }
  })

  unsubscribeMetrics = wsStore.on('system_metrics', (data) => {
    metrics.value = data
  })
})

onUnmounted(() => {
  if (unsubscribeSystemInfo) unsubscribeSystemInfo()
  if (unsubscribeMetrics) unsubscribeMetrics()
})
</script>