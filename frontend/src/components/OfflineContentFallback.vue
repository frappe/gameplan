<template>
  <EmptyStateBox>
    <span class="lucide-triangle-alert mb-3 size-7 text-ink-gray-4" aria-hidden="true" />
    <div class="text-base text-ink-gray-7">{{ title }}</div>
    <p class="mt-2 max-w-md text-center text-p-sm text-ink-gray-5">{{ message }}</p>
    <Button class="mt-4" icon-left="lucide-refresh-cw" @click="emit('retry')"> Retry </Button>
  </EmptyStateBox>
</template>

<script setup lang="ts">
// Presentational only: callers decide when to show it and what it says (see useLoadFailure).
import EmptyStateBox from './EmptyStateBox.vue'

defineProps<{
  title: string
  message: string
}>()

const emit = defineEmits<{ retry: [] }>()
</script>
