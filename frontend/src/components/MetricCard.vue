<template>
  <div class="text-center p-3 rounded-lg border border-gray-200 dark:border-dark-700 bg-gray-50 dark:bg-dark-900/50">
    <div class="text-xs text-gray-600 dark:text-gray-400 mb-1">{{ label }}</div>
    <div
      class="text-lg font-bold"
      :class="valueColorClass"
    >
      {{ value }}
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  label: {
    type: String,
    required: true
  },
  value: {
    type: [String, Number],
    required: true
  },
  color: {
    type: String,
    default: 'gray',
    validator: (value) => ['green', 'yellow', 'red', 'blue', 'gray'].includes(value)
  }
})

const valueColorClass = computed(() => {
  const colorMap = {
    green: 'text-green-600 dark:text-green-400',
    yellow: 'text-yellow-600 dark:text-yellow-400',
    red: 'text-red-600 dark:text-red-400',
    blue: 'text-blue-600 dark:text-blue-400',
    gray: 'text-gray-600 dark:text-gray-400'
  }
  return colorMap[props.color]
})
</script>