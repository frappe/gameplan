<template>
  <div class="relative flex h-full flex-col" v-if="users.isFinished">
    <div class="h-full flex-1 standalone:border-t">
      <div class="app-shell-background flex h-full">
        <AppRail :show-border="onCommunityRoute" :show-community-active-state="onCommunityRoute" />
        <AppSidebar v-if="onCommunityRoute" />
        <div class="flex min-w-0 flex-1 py-2 pr-2">
          <div class="app-shell-card flex min-w-0 flex-1 overflow-hidden rounded-lg bg-surface-base">
            <div class="flex flex-1 min-w-0 flex-col">
              <div id="pageHeaderTarget" />
              <ScrollContainer>
                <ReadOnlyBanner v-if="readOnlyMode" class="mb-3" />
                <slot />
              </ScrollContainer>
            </div>
          </div>
        </div>
      </div>
    </div>
    <CommandPalette />
  </div>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ScrollContainer from './ScrollContainer.vue'
import AppRail from './AppRail'
import AppSidebar from './AppSidebar.vue'
import CommandPalette from './CommandPalette/CommandPalette.vue'
import ReadOnlyBanner from './ReadOnlyBanner.vue'
import { readOnlyMode } from '@/data/readOnlyMode'
import { users } from '@/data/users'
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
