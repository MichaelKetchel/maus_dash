<template>
  <div class="flex items-center space-x-2">
    <!-- Connection indicator -->
    <div 
      class="w-2 h-2 rounded-full transition-colors duration-300"
      :class="statusColor"
    ></div>
    
    <!-- Status text -->
    <span class="text-sm text-gray-600 dark:text-gray-300">
      {{ statusText }}
    </span>

    <!-- Reconnect button (when disconnected) -->
    <button
      v-if="wsStore.connectionStatus === 'disconnected' && wsStore.canReconnect"
      @click="wsStore.connect()"
      class="text-xs px-2 py-1 bg-primary-100 dark:bg-primary-900 text-primary-700 dark:text-primary-300 rounded hover:bg-primary-200 dark:hover:bg-primary-800 transition-colors"
    >
      Reconnect
    </button>

    <!-- Connection info popup -->
    <div class="relative">
      <button
        @click="showDetails = !showDetails"
        class="p-1 rounded hover:bg-gray-100 dark:hover:bg-dark-700 transition-colors"
        title="Connection details"
      >
        <Info class="w-4 h-4 text-gray-500 dark:text-gray-400" />
      </button>

      <!-- Popup -->
      <div
        v-if="showDetails"
        class="absolute right-0 top-8 w-64 bg-white dark:bg-dark-800 border border-gray-200 dark:border-dark-700 rounded-lg shadow-lg p-4 z-50"
      >
        <div class="space-y-3">
          <div class="flex justify-between items-center">
            <h3 class="font-medium text-gray-900 dark:text-white">Connection Info</h3>
            <button @click="showDetails = false">
              <X class="w-4 h-4 text-gray-500" />
            </button>
          </div>

          <div class="space-y-2 text-sm">
            <div class="flex justify-between">
              <span class="text-gray-600 dark:text-gray-400">Status:</span>
              <span class="font-medium" :class="statusTextColor">{{ statusText }}</span>
            </div>

            <div v-if="wsStore.clientId" class="flex justify-between">
              <span class="text-gray-600 dark:text-gray-400">Client ID:</span>
              <span class="font-mono text-xs">{{ wsStore.clientId.slice(0, 8) }}...</span>
            </div>

            <div v-if="wsStore.lastPing" class="flex justify-between">
              <span class="text-gray-600 dark:text-gray-400">Last Ping:</span>
              <span>{{ formatTime(wsStore.lastPing) }}</span>
            </div>

            <div v-if="wsStore.reconnectAttempts > 0" class="flex justify-between">
              <span class="text-gray-600 dark:text-gray-400">Reconnect Attempts:</span>
              <span>{{ wsStore.reconnectAttempts }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Info, X } from 'lucide-vue-next'
import { useWebSocketStore } from '@/stores/websocket'

const wsStore = useWebSocketStore()
const showDetails = ref(false)

const statusColor = computed(() => {
  switch (wsStore.connectionStatus) {
    case 'connected':
      return 'bg-green-500 animate-pulse-slow'
    case 'connecting':
      return 'bg-yellow-500 animate-pulse'
    case 'disconnected':
      return 'bg-red-500'
    default:
      return 'bg-gray-500'
  }
})

const statusTextColor = computed(() => {
  switch (wsStore.connectionStatus) {
    case 'connected':
      return 'text-green-600 dark:text-green-400'
    case 'connecting':
      return 'text-yellow-600 dark:text-yellow-400'
    case 'disconnected':
      return 'text-red-600 dark:text-red-400'
    default:
      return 'text-gray-600 dark:text-gray-400'
  }
})

const statusText = computed(() => {
  switch (wsStore.connectionStatus) {
    case 'connected':
      return 'Connected'
    case 'connecting':
      return 'Connecting...'
    case 'disconnected':
      return 'Disconnected'
    default:
      return 'Unknown'
  }
})

const formatTime = (date) => {
  return new Date(date).toLocaleTimeString()
}
</script>