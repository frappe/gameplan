<template>
  <div class="body-container py-8">
    <OfflineContentFallback
      class="mx-auto max-w-2xl px-6"
      v-bind="loadFailureCopy(`this ${what}`)"
      @retry="retry"
    />
  </div>
</template>

<script setup lang="ts">
// Where the router sends a space or community it can't check offline: it may well exist.
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePageMeta } from 'frappe-ui'
import OfflineContentFallback from '@/components/OfflineContentFallback.vue'
import { loadFailureCopy } from '@/data/loadFailure'

const route = useRoute()
const router = useRouter()
const what = computed(() => (route.query.what === 'community' ? 'community' : 'space'))

usePageMeta(() => ({
  title: "Can't load this offline",
}))

function retry() {
  const redirect = route.query.redirect
  router.replace(typeof redirect === 'string' ? redirect : { name: 'Home' })
}
</script>
