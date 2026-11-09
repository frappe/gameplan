<template>
  <BottomSheet v-if="isMobile" v-model:open="showChangelogDialog" title="What's new">
    <ChangelogReleases class="px-4 pb-8" />
  </BottomSheet>
  <Dialog v-else v-model:open="showChangelogDialog" title="What's new" size="2xl">
    <ChangelogReleases />
  </Dialog>
</template>

<script setup lang="ts">
import { BottomSheet, Dialog } from 'frappe-ui'
import { showChangelogDialog } from '@/data/changelog'
import { useIsMobile } from '@/utils/useIsMobile'
import ChangelogReleases from './ChangelogReleases.vue'

const isMobile = useIsMobile()
</script>
