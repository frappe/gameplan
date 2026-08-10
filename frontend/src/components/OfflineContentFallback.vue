<template>
  <EmptyStateBox>
    <LucideTriangleAlert class="mb-3 size-7 text-ink-gray-4" />
    <div class="text-base text-ink-gray-7">{{ title }}</div>
    <p class="mt-2 max-w-md text-center text-p-sm text-ink-gray-5">{{ message }}</p>
    <Button class="mt-4" icon-left="lucide-refresh-cw" @click="emit('retry')"> Retry </Button>
  </EmptyStateBox>
</template>

<script setup lang="ts">
// Presentational-only: callers decide *when* to show this (loading/empty/error
// state belongs to the resource, not this component) and *what* to say (offline
// vs. generic copy, via isBrowserOffline()/isNetworkError() from '@/offline').
// Kept generic so any failed useList/useDoc fetch can reuse it instead of each
// page hand-rolling its own dead-end card.
import EmptyStateBox from './EmptyStateBox.vue'

defineProps<{
  title: string
  message: string
}>()

const emit = defineEmits<{ retry: [] }>()
</script>
