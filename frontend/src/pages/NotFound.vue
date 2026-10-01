<template>
  <div class="body-container py-8">
    <EmptyStateBox class="mx-auto max-w-2xl px-6">
      <span class="lucide-triangle-alert mb-3 size-7 text-ink-gray-4" aria-hidden="true" />
      <div class="text-base text-ink-gray-7">Page not found</div>
      <p class="mt-2 max-w-md text-center text-p-sm text-ink-gray-5">
        The link is invalid or you no longer have access to this page.
      </p>
    </EmptyStateBox>
  </div>
</template>

<script setup lang="ts">
import { usePageMeta } from 'frappe-ui'
import EmptyStateBox from '@/components/EmptyStateBox.vue'

usePageMeta(() => {
  return {
    title: 'Page not found',
  }
})
</script>
