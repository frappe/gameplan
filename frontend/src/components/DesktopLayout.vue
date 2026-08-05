<template>
  <!-- usersReady, not users.isFinished: a mid-session reload of the user list would flip
       isFinished back to false and unmount the entire shell — the app blanks out. -->
  <div class="relative flex h-full flex-col" v-if="usersReady">
    <DesktopShell class="gameplan-desktop-shell h-full flex-1 standalone:border-t">
      <template #rail>
        <AppRail :show-border="onCommunityRoute" :show-community-active-state="onCommunityRoute" />
      </template>
      <template #sidebar>
        <AppSidebar v-if="onCommunityRoute" />
      </template>

      <ReadOnlyBanner v-if="readOnlyMode" class="mb-3" />
      <slot />
    </DesktopShell>
    <CommandPalette />
  </div>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { DesktopShell } from 'frappe-ui'
import AppRail from './AppRail'
import AppSidebar from './AppSidebar.vue'
import CommandPalette from './CommandPalette/CommandPalette.vue'
import ReadOnlyBanner from './ReadOnlyBanner.vue'
import { readOnlyMode } from '@/data/readOnlyMode'
import { usersReady } from '@/data/users'
import { settingsBackgroundPath } from '@/components/Settings'
import { getHomeRoute } from '@/router'

const route = useRoute()
const router = useRouter()

// While the settings dialog is open the URL is /settings/*, but the page it was
// opened over stays rendered behind the overlay (see App.vue's displayedRoute).
// Drive the layout off that background page so the sidebar and rail state don't
// change when settings opens over a community.
const effectiveRoute = computed(() => {
  if (!route.matched.some((record) => record.meta?.settingsOverlay)) return route
  return router.resolve(settingsBackgroundPath.value || getHomeRoute())
})

const onCommunityRoute = computed(() => {
  return effectiveRoute.value.matched.some((record) => record.meta?.communityScope)
})
</script>

<style scoped>
.gameplan-desktop-shell :deep([data-slot='desktop-shell-content']) {
  @apply border-l bg-surface-base;
}
</style>
