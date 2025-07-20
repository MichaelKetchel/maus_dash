<template>
  <div class="bg-white dark:bg-dark-800 rounded-lg border border-gray-200 dark:border-dark-700 p-6">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-semibold text-gray-900 dark:text-white flex items-center space-x-2">
        <Package class="w-5 h-5" />
        <span>Dashboard Modules</span>
      </h3>

      <div class="flex items-center space-x-2">
        <button
          @click="refreshModules"
          :disabled="isLoading"
          class="p-2 rounded-lg bg-gray-100 dark:bg-dark-700 hover:bg-gray-200 dark:hover:bg-dark-600 transition-colors disabled:opacity-50"
          title="Refresh modules"
        >
          <RefreshCw
            class="w-4 h-4 text-gray-600 dark:text-gray-300"
            :class="{ 'animate-spin': isLoading }"
          />
        </button>
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="isLoading && !Object.keys(modules).length" class="flex items-center justify-center py-8">
      <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600"></div>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="text-center py-8">
      <AlertTriangle class="w-8 h-8 text-red-500 mx-auto mb-2" />
      <p class="text-sm text-red-600 dark:text-red-400">{{ error }}</p>
      <button
        @click="fetchModules"
        class="mt-2 text-xs px-3 py-1 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors"
      >
        Retry
      </button>
    </div>

    <!-- Modules content -->
    <div v-else-if="Object.keys(modules).length" class="space-y-3">
      <div
        v-for="(module, name) in modules"
        :key="name"
        class="flex items-center justify-between p-3 bg-gray-50 dark:bg-dark-700 rounded-lg"
      >
        <div class="flex items-center space-x-3">
          <div 
            class="w-3 h-3 rounded-full"
            :class="{
              'bg-green-500': module.loaded,
              'bg-red-500': !module.loaded,
              'bg-yellow-500': module.status === 'loading'
            }"
            :title="module.loaded ? 'Loaded' : 'Not loaded'"
          ></div>
          <div>
            <p class="font-medium text-gray-900 dark:text-white">{{ formatModuleName(name) }}</p>
            <p class="text-xs text-gray-500 dark:text-gray-400">
              {{ module.routes !== undefined ? `${module.routes} routes` : 'No route info' }}
            </p>
          </div>
        </div>

        <div class="flex items-center space-x-2">
          <!-- Module info -->
          <div class="text-xs text-gray-500 dark:text-gray-400 text-right">
            <div v-if="module.version">v{{ module.version }}</div>
            <div v-if="module.description" class="max-w-32 truncate" :title="module.description">
              {{ module.description }}
            </div>
          </div>

          <!-- Module actions -->
          <div class="flex space-x-1">
            <button
              v-if="!module.loaded"
              @click="loadModule(name)"
              :disabled="isModuleActionLoading[name]"
              class="px-2 py-1 text-xs bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded hover:bg-green-200 dark:hover:bg-green-900/50 transition-colors disabled:opacity-50"
              title="Load module"
            >
              <Play class="w-3 h-3" />
            </button>
            
            <button
              v-if="module.loaded"
              @click="reloadModule(name)"
              :disabled="isModuleActionLoading[name]"
              class="px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors disabled:opacity-50"
              title="Reload module"
            >
              <RotateCcw class="w-3 h-3" />
            </button>

            <button
              v-if="module.loaded"
              @click="unloadModule(name)"
              :disabled="isModuleActionLoading[name]"
              class="px-2 py-1 text-xs bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors disabled:opacity-50"
              title="Unload module"
            >
              <Square class="w-3 h-3" />
            </button>

            <!-- API status indicator -->
            <a
              v-if="module.loaded && module.routes > 0"
              :href="`/api/${name}/`"
              target="_blank"
              class="px-2 py-1 text-xs bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded hover:bg-purple-200 dark:hover:bg-purple-900/50 transition-colors"
              title="View API endpoints"
            >
              <ExternalLink class="w-3 h-3" />
            </a>
          </div>
        </div>
      </div>

      <!-- Summary stats -->
      <div class="pt-3 border-t border-gray-200 dark:border-dark-700">
        <div class="flex justify-between text-sm text-gray-600 dark:text-gray-400">
          <span>{{ loadedCount }} loaded</span>
          <span>{{ totalCount }} total modules</span>
        </div>
      </div>

      <!-- Hot reload info -->
      <div class="pt-2 text-xs text-gray-500 dark:text-gray-400 text-center">
        <div class="flex items-center justify-center space-x-1">
          <Zap class="w-3 h-3" />
          <span>Hot reload enabled - modules update automatically</span>
        </div>
      </div>
    </div>

    <!-- No data state -->
    <div v-else class="text-center py-8">
      <Package class="w-8 h-8 text-gray-400 mx-auto mb-2" />
      <p class="text-sm text-gray-500 dark:text-gray-400">No modules available</p>
      <button
        @click="fetchModules"
        class="mt-2 text-xs px-3 py-1 bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded hover:bg-primary-200 dark:hover:bg-primary-900/50 transition-colors"
      >
        Load Modules
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import {
  Package, RefreshCw, AlertTriangle, Play, Square, RotateCcw,
  ExternalLink, Zap
} from 'lucide-vue-next'
import { useWebSocketStore } from '@/stores/websocket'
import { useDashboardStore } from '@/stores/dashboard'

// Stores
const wsStore = useWebSocketStore()
const dashboardStore = useDashboardStore()

// State
const modules = ref({})
const isLoading = ref(false)
const error = ref(null)
const isModuleActionLoading = ref({})

// Computed
const loadedCount = computed(() => {
  return Object.values(modules.value).filter(module => module.loaded).length
})

const totalCount = computed(() => {
  return Object.keys(modules.value).length
})

// Methods
const fetchModules = async () => {
  try {
    isLoading.value = true
    error.value = null

    // Request modules status via WebSocket
    wsStore.send({
      type: 'system.status_request',
      payload: {}
    })
  } catch (err) {
    console.error('Error fetching modules:', err)
    error.value = err.message
  } finally {
    isLoading.value = false
  }
}

const refreshModules = () => {
  fetchModules()
}

const loadModule = async (moduleName) => {
  try {
    isModuleActionLoading.value[moduleName] = true
    
    wsStore.send({
      type: 'module.load',
      payload: { module_name: moduleName }
    })

    // Update local state optimistically
    if (modules.value[moduleName]) {
      modules.value[moduleName].loaded = true
      modules.value[moduleName].status = 'loading'
    }
  } catch (err) {
    console.error('Error loading module:', err)
    error.value = `Failed to load module: ${err.message}`
  } finally {
    setTimeout(() => {
      isModuleActionLoading.value[moduleName] = false
    }, 1000)
  }
}

const unloadModule = async (moduleName) => {
  try {
    isModuleActionLoading.value[moduleName] = true
    
    wsStore.send({
      type: 'module.unload',
      payload: { module_name: moduleName }
    })

    // Update local state optimistically
    if (modules.value[moduleName]) {
      modules.value[moduleName].loaded = false
    }
  } catch (err) {
    console.error('Error unloading module:', err)
    error.value = `Failed to unload module: ${err.message}`
  } finally {
    setTimeout(() => {
      isModuleActionLoading.value[moduleName] = false
    }, 1000)
  }
}

const reloadModule = async (moduleName) => {
  try {
    isModuleActionLoading.value[moduleName] = true
    
    wsStore.send({
      type: 'module.reload',
      payload: { module_name: moduleName }
    })
  } catch (err) {
    console.error('Error reloading module:', err)
    error.value = `Failed to reload module: ${err.message}`
  } finally {
    setTimeout(() => {
      isModuleActionLoading.value[moduleName] = false
    }, 2000) // Longer timeout for reload
  }
}

const formatModuleName = (name) => {
  return name.split('_').map(word => 
    word.charAt(0).toUpperCase() + word.slice(1)
  ).join(' ')
}

// WebSocket event handlers
let unsubscribeStatusResponse
let unsubscribeModuleEvents

onMounted(() => {
  // Fetch initial data
  fetchModules()

  // Subscribe to status updates
  unsubscribeStatusResponse = wsStore.on('system.status_response', (data) => {
    if (data.modules) {
      modules.value = data.modules
      // Update dashboard store as well
      dashboardStore.modules = data.modules
    }
  })

  // Subscribe to module events
  unsubscribeModuleEvents = wsStore.on('module.*', (data, eventType) => {
    console.log('Module event:', eventType, data)
    
    // Handle specific module events
    if (eventType === 'module.loaded' && data.module_name) {
      if (modules.value[data.module_name]) {
        modules.value[data.module_name].loaded = true
        modules.value[data.module_name].status = 'loaded'
      }
    } else if (eventType === 'module.unloaded' && data.module_name) {
      if (modules.value[data.module_name]) {
        modules.value[data.module_name].loaded = false
      }
    } else if (eventType === 'module.error' && data.module_name) {
      if (modules.value[data.module_name]) {
        modules.value[data.module_name].status = 'error'
      }
      error.value = `Module ${data.module_name}: ${data.error || 'Unknown error'}`
    }
    
    // Refresh modules on any module event
    setTimeout(fetchModules, 500)
  })

  // Use dashboard store modules if available
  if (dashboardStore.modules && Object.keys(dashboardStore.modules).length > 0) {
    modules.value = dashboardStore.modules
  }
})

onUnmounted(() => {
  if (unsubscribeStatusResponse) unsubscribeStatusResponse()
  if (unsubscribeModuleEvents) unsubscribeModuleEvents()
})
</script>