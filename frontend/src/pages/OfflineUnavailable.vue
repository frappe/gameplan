<template>
  <div class="body-container py-8">
    <OfflineContentFallback
      class="mx-auto max-w-2xl px-6"
      v-bind="loadFailureCopy('this space', true)"
      @retry="retry"
    />
  </div>
</template>

<script setup lang="ts">
// Where the router sends a space or community it can't check offline: it may well exist.
import { usePageMeta } from 'frappe-ui'
import OfflineContentFallback from '@/components/OfflineContentFallback.vue'
import { loadFailureCopy } from '@/data/loadFailure'

usePageMeta(() => ({
  title: "Can't load this offline",
}))

function retry() {
  // No specific resource to re-run (the router bailed before ever loading one) - a
  // reload re-runs the same navigation from scratch, which succeeds once back online
  // or once the relevant data has been cached.
  window.location.reload()
}
</script>
