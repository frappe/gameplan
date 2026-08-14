<template>
  <div
    class="relative block h-[68px] select-none sm:h-15 sm:rounded-[10px]"
    role="status"
    :aria-label="label"
  >
    <div class="flex h-[68px] items-center overflow-hidden px-4 py-2 sm:h-full sm:px-3">
      <div class="flex items-center space-x-3">
        <div class="size-10 shrink-0 animate-pulse rounded-full bg-surface-gray-3" />
      </div>
      <div class="mx-3 min-w-0 flex-1 sm:ms-4 sm:me-4">
        <div class="h-4 w-4/5 max-w-80 animate-pulse rounded-4 bg-surface-gray-3" />
        <div class="mt-2 h-3.5 w-full max-w-[24rem] animate-pulse rounded-4 bg-surface-gray-2" />
      </div>
      <div class="ms-auto flex shrink-0 flex-col items-end">
        <div class="h-3 w-10 animate-pulse rounded-4 bg-surface-gray-2" />
        <div class="mt-2 h-4 w-6 animate-pulse rounded-full bg-surface-gray-2" />
      </div>
    </div>
    <div class="ps-1" v-if="showSeparator">
      <div class="ms-16 me-4 h-px border-t border-outline-gray-1 sm:me-3" />
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    showSeparator?: boolean
    label?: string
  }>(),
  { label: 'Loading' },
)
</script>
