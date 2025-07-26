<template>
  <div class="bg-white dark:bg-dark-800 rounded-lg border border-gray-200 dark:border-dark-700 p-6">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-semibold text-gray-900 dark:text-white flex items-center space-x-2">
        <Package class="w-5 h-5" />
        <span>Enhanced Module Manager</span>
      </h3>

      <div class="flex items-center space-x-2">
        <!-- Auto-reload toggle -->
        <button
          @click="toggleAutoReload"
          :class="{
            'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300': autoReloadEnabled,
            'bg-gray-100 dark:bg-dark-700 text-gray-600 dark:text-gray-300': !autoReloadEnabled
          }"
          class="p-2 rounded-lg hover:bg-opacity-80 transition-colors"
          title="Toggle auto-reload"
        >
          <Zap class="w-4 h-4" />
        </button>
        
        <!-- Check changes -->
        <button
          @click="checkChanges"
          :disabled="isLoading"
          class="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors disabled:opacity-50"
          title="Check for file changes"
        >
          <Search class="w-4 h-4" />
        </button>
        
        <!-- Reload all -->
        <button
          @click="reloadAllModules"
          :disabled="isLoading"
          class="p-2 rounded-lg bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 hover:bg-orange-200 dark:hover:bg-orange-900/50 transition-colors disabled:opacity-50"
          title="Reload all modules"
        >
          <RotateCcw class="w-4 h-4" />
        </button>
        
        <!-- Refresh -->
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

    <!-- Enhanced modules content -->
    <div v-else-if="moduleList.length" class="space-y-3">
      <div
        v-for="module in moduleList"
        :key="module.name"
        class="p-4 bg-gray-50 dark:bg-dark-700 rounded-lg border border-gray-200 dark:border-dark-600 hover:border-gray-300 dark:hover:border-dark-500 transition-colors"
      >
        <!-- Module header -->
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center space-x-3">
            <!-- Enhanced state indicator -->
            <div class="flex items-center space-x-2">
              <div 
                class="w-3 h-3 rounded-full flex-shrink-0"
                :class="getStateClasses(module.state)"
                :title="getStateInfo(module.state).label"
              ></div>
              <span class="text-xs font-medium px-2 py-1 rounded-full" :class="getStateBadgeClasses(module.state)">
                {{ getStateInfo(module.state).label }}
              </span>
            </div>
            
            <!-- File change indicator -->
            <div v-if="fileChanges[module.name]" class="flex items-center space-x-1 text-orange-600 dark:text-orange-400">
              <AlertTriangle class="w-3 h-3" />
              <span class="text-xs">Changed</span>
            </div>
          </div>
          
          <div class="text-xs text-gray-500 dark:text-gray-400">
            Reloads: {{ module.reload_count || 0 }}
          </div>
        </div>
        
        <!-- Module info -->
        <div class="flex items-center justify-between mb-3">
          <div>
            <h4 class="font-medium text-gray-900 dark:text-white">{{ formatModuleName(module.name) }}</h4>
            <div class="text-xs text-gray-500 dark:text-gray-400 space-x-4">
              <span>{{ module.module_info?.routes || 0 }} routes</span>
              <span>{{ module.module_info?.tasks || 0 }} tasks</span>
              <span v-if="module.module_info?.dependencies?.length">{{ module.module_info.dependencies.length }} deps</span>
            </div>
          </div>
        </div>

        <!-- Module actions -->
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <!-- Dependencies info -->
            <div v-if="module.module_info?.dependencies?.length" class="text-xs text-blue-600 dark:text-blue-400">
              Depends: {{ module.module_info.dependencies.join(', ') }}
            </div>
            <div v-if="module.module_info?.dependents?.length" class="text-xs text-purple-600 dark:text-purple-400">
              Used by: {{ module.module_info.dependents.join(', ') }}
            </div>
          </div>
          
          <div class="flex space-x-1">
            <!-- Force reload -->
            <button
              v-if="module.state === 'ready'"
              @click="reloadModule(module.name, true)"
              :disabled="isModuleActionLoading[module.name]"
              class="px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors disabled:opacity-50"
              title="Force reload module"
            >
              <RotateCcw class="w-3 h-3" />
            </button>
            
            <!-- Smart reload (only if changed) -->
            <button
              v-if="module.state === 'ready' && fileChanges[module.name]"
              @click="reloadModule(module.name, false)"
              :disabled="isModuleActionLoading[module.name]"
              class="px-2 py-1 text-xs bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 rounded hover:bg-orange-200 dark:hover:bg-orange-900/50 transition-colors disabled:opacity-50"
              title="Reload (file changed)"
            >
              <RefreshCw class="w-3 h-3" />
            </button>

            <!-- Unload -->
            <button
              v-if="module.state === 'ready'"
              @click="unloadModule(module.name)"
              :disabled="isModuleActionLoading[module.name] || module.module_info?.dependents?.length"
              class="px-2 py-1 text-xs bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors disabled:opacity-50"
              :title="module.module_info?.dependents?.length ? 'Cannot unload: has dependents' : 'Unload module'"
            >
              <Square class="w-3 h-3" />
            </button>
            
            <!-- Force unload -->
            <button
              v-if="module.state === 'ready' && module.module_info?.dependents?.length"
              @click="unloadModule(module.name, true)"
              :disabled="isModuleActionLoading[module.name]"
              class="px-2 py-1 text-xs bg-red-200 dark:bg-red-800/30 text-red-800 dark:text-red-200 rounded hover:bg-red-300 dark:hover:bg-red-800/50 transition-colors disabled:opacity-50"
              title="Force unload (ignore dependents)"
            >
              <X class="w-3 h-3" />
            </button>

            <!-- API docs link -->
            <a
              v-if="module.state === 'ready' && (module.module_info?.routes || 0) > 0"
              :href="getModuleDocsUrl(module.name)"
              target="_blank"
              class="px-2 py-1 text-xs bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded hover:bg-purple-200 dark:hover:bg-purple-900/50 transition-colors"
              title="View API documentation"
            >
              <ExternalLink class="w-3 h-3" />
            </a>
            
            <!-- Module routes link -->
            <a
              v-if="module.state === 'ready' && (module.module_info?.routes || 0) > 0"
              :href="`/api/${module.name}/`"
              target="_blank"
              class="px-2 py-1 text-xs bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 rounded hover:bg-indigo-200 dark:hover:bg-indigo-900/50 transition-colors"
              title="Test API endpoints"
            >
              <Globe class="w-3 h-3" />
            </a>
          </div>
        </div>
      </div>

      <!-- Enhanced summary stats -->
      <div class="pt-4 border-t border-gray-200 dark:border-dark-700">
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div class="text-center">
            <div class="font-semibold text-green-600 dark:text-green-400">{{ stats?.loaded_modules || 0 }}</div>
            <div class="text-xs text-gray-500 dark:text-gray-400">Ready</div>
          </div>
          <div class="text-center">
            <div class="font-semibold text-blue-600 dark:text-blue-400">{{ stats?.total_modules || 0 }}</div>
            <div class="text-xs text-gray-500 dark:text-gray-400">Total</div>
          </div>
          <div class="text-center">
            <div class="font-semibold text-orange-600 dark:text-orange-400">{{ stats?.total_reloads || 0 }}</div>
            <div class="text-xs text-gray-500 dark:text-gray-400">Reloads</div>
          </div>
          <div class="text-center">
            <div class="font-semibold text-red-600 dark:text-red-400">{{ stats?.failed_modules || 0 }}</div>
            <div class="text-xs text-gray-500 dark:text-gray-400">Errors</div>
          </div>
        </div>
        
        <!-- Auto-reload status -->
        <div class="pt-3 text-xs text-center">
          <div class="flex items-center justify-center space-x-2" :class="{
            'text-green-600 dark:text-green-400': autoReloadEnabled,
            'text-gray-500 dark:text-gray-400': !autoReloadEnabled
          }">
            <Zap class="w-3 h-3" />
            <span>Auto-reload: {{ autoReloadEnabled ? 'Enabled' : 'Disabled' }}</span>
            <span v-if="changedModulesCount > 0" class="px-2 py-1 bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 rounded-full">
              {{ changedModulesCount }} changed
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- No data state -->
    <div v-else class="text-center py-8">
      <Package class="w-8 h-8 text-gray-400 mx-auto mb-2" />
      <p class="text-sm text-gray-500 dark:text-gray-400">No modules found</p>
      <p class="text-xs text-gray-400 dark:text-gray-500 mt-1">Check that modules exist in backend/modules/</p>
      <button
        @click="fetchModules"
        class="mt-3 text-xs px-3 py-1 bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded hover:bg-primary-200 dark:hover:bg-primary-900/50 transition-colors"
      >
        Refresh Modules
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import {
  Package, RefreshCw, AlertTriangle, Search, RotateCcw, Square, X,
  ExternalLink, Zap, Globe
} from 'lucide-vue-next'
import { useWebSocketStore } from '@/stores/websocket'
import { useDashboardStore } from '@/stores/dashboard'
import moduleService from '@/services/moduleService'

// Stores
const wsStore = useWebSocketStore()
const dashboardStore = useDashboardStore()

// Enhanced state
const moduleList = ref([])
const stats = ref(null)
const fileChanges = ref({})
const isLoading = ref(false)
const error = ref(null)
const isModuleActionLoading = ref({})
const autoReloadEnabled = ref(false)
const autoReloadInterval = ref(null)

// Enhanced computed
const changedModulesCount = computed(() => {
  return Object.values(fileChanges.value).filter(changed => changed).length
})

// Enhanced methods
const fetchModules = async () => {
  try {
    isLoading.value = true
    error.value = null

    // Use the enhanced module API
    const response = await moduleService.getModules()
    moduleList.value = response.modules || []
    stats.value = response.stats || {}
    
    // Also fetch file changes
    await checkChanges()
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

const reloadModule = async (moduleName, force = false) => {
  try {
    isModuleActionLoading.value[moduleName] = true
    
    const response = await moduleService.reloadModule(moduleName, force)
    
    // Clear file change status on successful reload
    if (fileChanges.value[moduleName]) {
      fileChanges.value[moduleName] = false
    }
    
    // Refresh module list
    await fetchModules()
    
    console.log(`Module ${moduleName} reloaded successfully`)
  } catch (err) {
    console.error('Error reloading module:', err)
    error.value = `Failed to reload module: ${err.message}`
  } finally {
    isModuleActionLoading.value[moduleName] = false
  }
}

const unloadModule = async (moduleName, force = false) => {
  try {
    isModuleActionLoading.value[moduleName] = true
    
    await moduleService.unloadModule(moduleName, force)
    
    // Refresh module list
    await fetchModules()
    
    console.log(`Module ${moduleName} unloaded successfully`)
  } catch (err) {
    console.error('Error unloading module:', err)
    error.value = `Failed to unload module: ${err.message}`
  } finally {
    isModuleActionLoading.value[moduleName] = false
  }
}

const reloadAllModules = async () => {
  try {
    isLoading.value = true
    
    await moduleService.reloadAllModules(true) // Force reload all
    
    // Clear all file changes
    fileChanges.value = {}
    
    // Refresh module list
    await fetchModules()
    
    console.log('All modules reloaded successfully')
  } catch (err) {
    console.error('Error reloading all modules:', err)
    error.value = `Failed to reload all modules: ${err.message}`
  } finally {
    isLoading.value = false
  }
}

const checkChanges = async () => {
  try {
    const response = await moduleService.checkModuleChanges()
    fileChanges.value = response.changes || {}
    
    // Auto-reload changed modules if enabled
    if (autoReloadEnabled.value && response.changed_count > 0) {
      await autoReloadChangedModules()
    }
  } catch (err) {
    console.error('Error checking file changes:', err)
  }
}

const autoReloadChangedModules = async () => {
  try {
    const response = await moduleService.autoReloadModules()
    
    if (response.results && Object.keys(response.results).length > 0) {
      console.log('Auto-reloaded changed modules:', response.results)
      await fetchModules()
    }
  } catch (err) {
    console.error('Error auto-reloading modules:', err)
  }
}

const toggleAutoReload = () => {
  autoReloadEnabled.value = !autoReloadEnabled.value
  
  if (autoReloadEnabled.value) {
    // Start checking for changes every 5 seconds
    autoReloadInterval.value = setInterval(checkChanges, 5000)
    console.log('Auto-reload enabled')
  } else {
    // Stop checking
    if (autoReloadInterval.value) {
      clearInterval(autoReloadInterval.value)
      autoReloadInterval.value = null
    }
    console.log('Auto-reload disabled')
  }
}

// Utility methods
const formatModuleName = (name) => {
  return moduleService.formatModuleName(name)
}

const getStateInfo = (state) => {
  return moduleService.getStateInfo(state)
}

const getStateClasses = (state) => {
  const info = getStateInfo(state)
  const colorMap = {
    'gray': 'bg-gray-400',
    'yellow': 'bg-yellow-400 animate-pulse',
    'blue': 'bg-blue-400',
    'orange': 'bg-orange-400 animate-pulse',
    'green': 'bg-green-400',
    'red': 'bg-red-400'
  }
  return colorMap[info.color] || 'bg-gray-400'
}

const getStateBadgeClasses = (state) => {
  const info = getStateInfo(state)
  const colorMap = {
    'gray': 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300',
    'yellow': 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300',
    'blue': 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300',
    'orange': 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300',
    'green': 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300',
    'red': 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300'
  }
  return colorMap[info.color] || 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300'
}

const getModuleDocsUrl = (moduleName) => {
  return moduleService.getModuleDocsUrl(moduleName)
}

// Enhanced WebSocket event handlers
let unsubscribeModuleEvents

onMounted(async () => {
  // Fetch initial data
  await fetchModules()

  // Subscribe to enhanced module events
  unsubscribeModuleEvents = wsStore.on('module.*', async (data, eventType) => {
    console.log('Enhanced module event:', eventType, data)
    
    // Handle all module lifecycle events
    if (data.module_name) {
      // Update loading states
      if (eventType.includes('loading') || eventType.includes('initializing')) {
        isModuleActionLoading.value[data.module_name] = true
      } else {
        isModuleActionLoading.value[data.module_name] = false
      }
      
      // Show errors
      if (eventType.includes('error')) {
        error.value = `Module ${data.module_name}: ${data.error || 'Unknown error'}`
      }
      
      // Refresh modules on significant events
      if (['loaded', 'unloaded', 'reloaded', 'error'].some(event => eventType.includes(event))) {
        setTimeout(fetchModules, 500)
      }
    }
  })
  
  // Start auto-reload if it was previously enabled
  const savedAutoReload = localStorage.getItem('module-auto-reload')
  if (savedAutoReload === 'true') {
    toggleAutoReload()
  }
})

onUnmounted(() => {
  if (unsubscribeModuleEvents) unsubscribeModuleEvents()
  
  // Clean up auto-reload interval
  if (autoReloadInterval.value) {
    clearInterval(autoReloadInterval.value)
  }
  
  // Save auto-reload preference
  localStorage.setItem('module-auto-reload', autoReloadEnabled.value.toString())
})
</script>