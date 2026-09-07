<template>
  <div class="body-container py-8">
    <OfflineContentFallback
      class="mx-auto max-w-2xl px-6"
      title="This space isn't available offline"
      message="It hasn't been saved for offline use yet. Reconnect and retry to load it."
      @retry="retry"
    />
  </div>
</template>

<script setup lang="ts">
// Router destination for a community/space route the app can't validate while offline
// (router.ts's isRouteValidationUnavailable branches) - see the comment at those call
// sites. Unlike the generic NotFound.vue, this is reachable while genuinely offline, so
// it says so honestly instead of implying the space doesn't exist, and offers a Retry
// rather than a dead end - the space may well be real and just never cached.
import { usePageMeta } from 'frappe-ui'
import OfflineContentFallback from '@/components/OfflineContentFallback.vue'

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
