<template>
  <div
    class="flex min-h-64 flex-col items-center justify-center rounded-6 border border-dashed border-outline-gray-2 px-6 py-12 text-center"
  >
    <div class="flex size-10 items-center justify-center rounded-4 bg-surface-gray-2">
      <span :class="[icon, 'size-5 text-ink-gray-5']" />
    </div>
    <h3 class="mt-4 text-lg-medium text-ink-gray-8">{{ title }}</h3>
    <p v-if="description" class="mt-1 max-w-sm text-p-base text-ink-gray-5">
      {{ description }}
    </p>
    <div v-if="$slots.actions" class="mt-4">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  icon: string
  title: string
  description?: string
}>()
</script>
