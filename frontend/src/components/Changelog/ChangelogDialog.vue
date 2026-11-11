<template>
  <BottomSheet v-if="isMobile" v-model:open="showChangelogDialog" title="What's new">
    <ChangelogReleases class="px-4 pb-8" />
  </BottomSheet>
  <Dialog v-else v-model:open="showChangelogDialog" title="What's new" size="2xl">
    <ChangelogReleases />
  </Dialog>
</template>

<script setup lang="ts">
import { defineAsyncComponent } from 'vue'
import { BottomSheet, Dialog } from 'frappe-ui'
import { showChangelogDialog } from '@/data/changelog'
import { useIsMobile } from '@/utils/useIsMobile'

// Loads on first open, with the Markdown parser it needs.
const ChangelogReleases = defineAsyncComponent(() => import('./ChangelogReleases.vue'))

const isMobile = useIsMobile()
</script>
