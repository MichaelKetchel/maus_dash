<template>
  <div class="flex items-center justify-between py-2">
    <div class="flex items-center space-x-2">
      <component
        v-if="icon"
        :is="iconComponent"
        class="w-4 h-4 text-gray-500 dark:text-gray-400"
      />
      <span class="text-sm text-gray-600 dark:text-gray-400">{{ label }}:</span>
    </div>
    <span class="text-sm font-medium text-gray-900 dark:text-white text-right max-w-xs truncate" :title="value">
      {{ value || 'N/A' }}
    </span>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import {
  Server, Monitor, Code, Clock, User, Globe,
  HardDrive, Cpu, Activity, Package
} from 'lucide-vue-next'

const props = defineProps({
  label: {
    type: String,
    required: true
  },
  value: {
    type: [String, Number],
    default: null
  },
  icon: {
    type: String,
    default: null
  }
})

// Icon mapping
const iconMap = {
  Server,
  Monitor,
  Code,
  Clock,
  User,
  Globe,
  HardDrive,
  Cpu,
  Activity,
  Package
}

const iconComponent = computed(() => {
  return props.icon ? iconMap[props.icon] || Server : null
})
</script>