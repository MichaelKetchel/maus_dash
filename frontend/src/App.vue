<template>
  <div id="app" class="min-h-screen bg-gray-50 dark:bg-dark-900 transition-colors duration-200">
    <!-- Header -->
    <header class="bg-white dark:bg-dark-800 shadow-sm border-b border-gray-200 dark:border-dark-700">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center h-16">
          <!-- Logo/Title -->
          <div class="flex items-center space-x-3">
            <div class="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
              <Monitor class="w-5 h-5 text-white" />
            </div>
            <h1 class="text-xl font-semibold text-gray-900 dark:text-white">
              Dashboard
            </h1>
          </div>

          <!-- Connection Status -->
          <div class="flex items-center space-x-4">
            <ConnectionStatus />
            
            <!-- Theme Toggle -->
            <button
              @click="dashboardStore.toggleDarkMode()"
              class="p-2 rounded-lg bg-gray-100 dark:bg-dark-700 hover:bg-gray-200 dark:hover:bg-dark-600 transition-colors"
              title="Toggle theme"
            >
              <Sun v-if="dashboardStore.isDarkMode" class="w-5 h-5 text-gray-600 dark:text-gray-300" />
              <Moon v-else class="w-5 h-5 text-gray-600 dark:text-gray-300" />
            </button>

            <!-- System Status -->
            <div class="flex items-center space-x-2">
              <div 
                class="w-2 h-2 rounded-full"
                :class="{
                  'bg-green-500': dashboardStore.isSystemHealthy,
                  'bg-yellow-500': !dashboardStore.isSystemHealthy,
                  'bg-red-500': dashboardStore.error
                }"
              ></div>
              <span class="text-sm text-gray-600 dark:text-gray-300">
                {{ systemStatusText }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <!-- Error Banner -->
      <div 
        v-if="dashboardStore.error"
        class="mb-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4"
      >
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <AlertTriangle class="w-5 h-5 text-red-500" />
            <div>
              <h3 class="text-sm font-medium text-red-800 dark:text-red-200">
                System Error
              </h3>
              <p class="text-sm text-red-700 dark:text-red-300 mt-1">
                {{ dashboardStore.error }}
              </p>
            </div>
          </div>
          <button
            @click="dashboardStore.clearError()"
            class="text-red-500 hover:text-red-700 dark:hover:text-red-300"
          >
            <X class="w-5 h-5" />
          </button>
        </div>
      </div>

      <!-- Loading State -->
      <div 
        v-if="dashboardStore.isLoading"
        class="flex items-center justify-center py-12"
      >
        <div class="flex items-center space-x-3">
          <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600"></div>
          <span class="text-gray-600 dark:text-gray-300">Loading dashboard...</span>
        </div>
      </div>

      <!-- Dashboard Content -->
      <div v-else class="space-y-6">
        <!-- Stats Overview -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatCard
            title="Modules"
            :value="dashboardStore.activeModulesCount"
            :total="Object.keys(dashboardStore.modules).length"
            icon="Package"
            color="blue"
          />
          <StatCard
            title="Workers"
            :value="dashboardStore.runningWorkersCount"
            :total="Object.keys(dashboardStore.workers).length"
            icon="Activity"
            color="green"
          />
          <StatCard
            title="CPU Usage"
            :value="`${(dashboardStore.systemMetrics.cpu_percent || 0).toFixed(1)}%`"
            icon="Cpu"
            :color="(dashboardStore.systemMetrics.cpu_percent || 0) > 80 ? 'red' : 'yellow'"
          />
          <StatCard
            title="Memory Usage"
            :value="`${(dashboardStore.systemMetrics.memory_percent || 0).toFixed(1)}%`"
            icon="HardDrive"
            :color="(dashboardStore.systemMetrics.memory_percent || 0) > 90 ? 'red' : 'yellow'"
          />
        </div>

        <!-- Module Grid -->
        <div class="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
          <!-- System Info Module -->
          <SystemInfoModule />
          
          <!-- Workers Status -->
          <WorkersModule />
          
          <!-- Modules Status -->
          <ModulesModule />

          <!-- Real-time Metrics -->
          <MetricsModule />
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { 
  Monitor, Sun, Moon, AlertTriangle, X, Package, 
  Activity, Cpu, HardDrive 
} from 'lucide-vue-next'

// Stores
import { useWebSocketStore } from '@/stores/websocket'
import { useDashboardStore } from '@/stores/dashboard'

// Components
import ConnectionStatus from '@/components/ConnectionStatus.vue'
import StatCard from '@/components/StatCard.vue'
import SystemInfoModule from '@/components/modules/SystemInfoModule.vue'
import WorkersModule from '@/components/modules/WorkersModule.vue'
import ModulesModule from '@/components/modules/ModulesModule.vue'
import MetricsModule from '@/components/modules/MetricsModule.vue'

// Initialize stores
const wsStore = useWebSocketStore()
const dashboardStore = useDashboardStore()

// Computed
const systemStatusText = computed(() => {
  if (dashboardStore.error) return 'Error'
  if (dashboardStore.isSystemHealthy) return 'Healthy'
  return 'Warning'
})

// Lifecycle
onMounted(async () => {
  // Initialize theme
  dashboardStore.initializeTheme()
  
  // Initialize WebSocket connection
  wsStore.initialize()
  
  // Initialize dashboard
  await dashboardStore.initialize()
})
</script>

<style>
/* Global styles */
body {
  font-family: 'Inter', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

/* Custom scrollbar */
::-webkit-scrollbar {
  width: 6px;
}

::-webkit-scrollbar-track {
  @apply bg-gray-100 dark:bg-dark-800;
}

::-webkit-scrollbar-thumb {
  @apply bg-gray-300 dark:bg-dark-600 rounded-full;
}

::-webkit-scrollbar-thumb:hover {
  @apply bg-gray-400 dark:bg-dark-500;
}
</style>