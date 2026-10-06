<template>
  <div class="flex h-full flex-col bg-surface-base">
    <header
      class="flex shrink-0 items-center justify-between gap-3 border-b border-outline-gray-1 px-4 py-2.5 sm:px-6"
    >
      <div class="flex min-w-0 items-center gap-2">
        <GameplanLogo class="size-6 shrink-0" />
        <span class="truncate text-base-medium text-ink-gray-8">{{ title }}</span>
      </div>
      <PublicLoginButtons />
    </header>
    <main class="flex-1 overflow-y-auto">
      <PublicSpace
        v-if="spaceId && (route.name === 'Space' || route.name === 'SpaceDiscussions')"
        :key="spaceId"
        :spaceId="spaceId"
      />
      <PublicDiscussion
        v-else-if="spaceId && postId && route.name === 'Discussion'"
        :key="postId"
        :spaceId="spaceId"
        :postId="postId"
      />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { getCommunity } from '@/data/communities'
import { getSpace } from '@/data/spaces'
import GameplanLogo from '@/components/GameplanLogo.vue'
import PublicDiscussion from './PublicDiscussion.vue'
import PublicLoginButtons from './PublicLoginButtons.vue'
import PublicSpace from './PublicSpace.vue'

// What someone who is not signed in sees: a header that offers to log them in, and a
// read-only view of the public space or discussion in the URL. The router lets them
// reach only routes marked `public`, and the server only hands them Anonymous-tier
// content, so nothing here decides what they may read.
const route = useRoute()

function param(value: unknown): string | null {
  return typeof value === 'string' && value ? value : null
}
const spaceId = computed(() => param(route.params.spaceId))
const postId = computed(() => param(route.params.postId))
// The community being read, not the site's internal name (often a hostname).
const title = computed(() => {
  const team = spaceId.value ? getSpace(spaceId.value)?.team : null
  return (team && getCommunity(team)?.title) || 'Gameplan'
})
</script>
