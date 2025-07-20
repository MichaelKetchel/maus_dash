<template>
  <div class="bg-white dark:bg-dark-800 rounded-lg border border-gray-200 dark:border-dark-700 p-6 hover:shadow-md transition-shadow">
    <div class="flex items-center justify-between">
      <div>
        <p class="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">
          {{ title }}
        </p>
        <div class="flex items-baseline space-x-2">
          <p class="text-2xl font-bold text-gray-900 dark:text-white">
            {{ displayValue }}
          </p>
          <p v-if="total !== undefined" class="text-sm text-gray-500 dark:text-gray-400">
            / {{ total }}
          </p>
        </div>
      </div>

      <div class="flex-shrink-0">
        <div
          class="w-12 h-12 rounded-lg flex items-center justify-center"
          :class="iconBgClass"
        >
          <component
            :is="iconComponent"
            class="w-6 h-6"
            :class="iconClass"
          />
        </div>
      </div>
    </div>

    <!-- Progress bar (if total is provided) -->
    <div v-if="total !== undefined && showProgress" class="mt-4">
      <div class="w-full bg-gray-200 dark:bg-dark-700 rounded-full h-2">
        <div
          class="h-2 rounded-full transition-all duration-300"
          :class="progressBarClass"
          :style="{ width: `${progressPercentage}%` }"
        ></div>
      </div>
    </div>

    <!-- Subtitle/description -->
    <p v-if="subtitle" class="text-xs text-gray-500 dark:text-gray-400 mt-2">
      {{ subtitle }}
    </p>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import {
  Package, Activity, Cpu, HardDrive, Users, Server,
  Zap, AlertTriangle, CheckCircle, Clock
} from 'lucide-vue-next'

const props = defineProps({
  title: {
    type: String,
    required: true
  },
  value: {
    type: [String, Number],
    required: true
  },
  total: {
    type: Number,
    default: undefined
  },
  icon: {
    type: String,
    default: 'Activity'
  },
  color: {
    type: String,
    default: 'blue',
    validator: (value) => ['blue', 'green', 'yellow', 'red', 'purple', 'gray'].includes(value)
  },
  subtitle: {
    type: String,
    default: null
  },
  showProgress: {
    type: Boolean,
    default: true
  }
})

// Icon mapping
const iconMap = {
  Package,
  Activity,
  Cpu,
  HardDrive,
  Users,
  Server,
  Zap,
  AlertTriangle,
  CheckCircle,
  Clock
}

const iconComponent = computed(() => {
  return iconMap[props.icon] || Activity
})

// Color classes
const colorClasses = {
  blue: {
    icon: 'text-blue-600 dark:text-blue-400',
    iconBg: 'bg-blue-100 dark:bg-blue-900/30',
    progress: 'bg-blue-500'
  },
  green: {
    icon: 'text-green-600 dark:text-green-400',
    iconBg: 'bg-green-100 dark:bg-green-900/30',
    progress: 'bg-green-500'
  },
  yellow: {
    icon: 'text-yellow-600 dark:text-yellow-400',
    iconBg: 'bg-yellow-100 dark:bg-yellow-900/30',
    progress: 'bg-yellow-500'
  },
  red: {
    icon: 'text-red-600 dark:text-red-400',
    iconBg: 'bg-red-100 dark:bg-red-900/30',
    progress: 'bg-red-500'
  },
  purple: {
    icon: 'text-purple-600 dark:text-purple-400',
    iconBg: 'bg-purple-100 dark:bg-purple-900/30',
    progress: 'bg-purple-500'
  },
  gray: {
    icon: 'text-gray-600 dark:text-gray-400',
    iconBg: 'bg-gray-100 dark:bg-gray-900/30',
    progress: 'bg-gray-500'
  }
}

const iconClass = computed(() => colorClasses[props.color].icon)
const iconBgClass = computed(() => colorClasses[props.color].iconBg)
const progressBarClass = computed(() => colorClasses[props.color].progress)

const displayValue = computed(() => {
  if (typeof props.value === 'number' && props.total !== undefined) {
    return props.value
  }
  return props.value
})

const progressPercentage = computed(() => {
  if (props.total === undefined || typeof props.value !== 'number') {
    return 0
  }
  return Math.min((props.value / props.total) * 100, 100)
})
</script>