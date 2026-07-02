<template>
  <div class="fixed inset-0 flex flex-col overflow-hidden touch-none">
    <div id="pageHeaderTarget" class="standalone:pt-[env(safe-area-inset-top)]" />

    <div
      id="scrollContainer"
      class="flex-1 overflow-y-auto overscroll-auto bg-surface-base [-webkit-overflow-scrolling:touch]"
    >
      <ReadOnlyBanner v-if="readOnlyMode" />
      <slot />
    </div>

    <div
      v-if="!isNewCommentOpen"
      class="shrink-0 border-t border-outline-gray-2 bg-surface-elevation-2 standalone:pb-4"
    >
      <div class="grid grid-cols-4">
        <button
          v-for="tab in tabs"
          :key="tab.name"
          type="button"
          :aria-label="tab.name"
          class="flex min-h-14 flex-col items-center justify-center gap-1 py-2 transition active:scale-95"
          @click="onTabClick(tab)"
        >
          <UserAvatar
            v-if="tab.name === 'You' && sessionUser.name"
            :user="sessionUser.name"
            class="size-6"
            :class="tab.isActive ? 'ring-2 ring-outline-gray-4' : ''"
          />
          <span
            v-else
            :class="[tab.icon, 'size-6', tab.isActive ? 'text-ink-gray-8' : 'text-ink-gray-5']"
          />
          <span
            class="text-xs-medium"
            :class="tab.isActive ? 'text-ink-gray-8' : 'text-ink-gray-5'"
          >
            {{ tab.name }}
          </span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineOptions({
  inheritAttrs: false,
})

import { computed } from 'vue'
import { useRoute, useRouter, type RouteLocationRaw } from 'vue-router'
import { isNewCommentOpen } from '@/data/newComment'
import { useSessionUser } from '@/data/users'
import { scrollTo } from '@/utils/scrollContainer'
import ReadOnlyBanner from './ReadOnlyBanner.vue'
import UserAvatar from './UserAvatar.vue'
import { readOnlyMode } from '@/data/readOnlyMode'
import { session } from '@/data/session'

interface MobileTab {
  name: 'Home' | 'Notifications' | 'Search' | 'You'
  icon: string
  route: RouteLocationRaw
  isActive: boolean
}

const route = useRoute()
const router = useRouter()
const sessionUser = useSessionUser()

const onCommunityRoute = computed(() => route.matched.some((record) => record.meta?.communityScope))
const isHomeRoute = computed(() => {
  return route.name === 'Home' || onCommunityRoute.value
})

const tabs = computed<MobileTab[]>(() => {
  const homeTab: MobileTab = {
    name: 'Home',
    icon: 'lucide-home',
    route: { name: 'Home' },
    isActive: isHomeRoute.value,
  }

  if (session.canBrowsePublicWeb) return [homeTab]

  return [
    homeTab,
    {
      name: 'Notifications',
      icon: 'lucide-bell',
      route: { name: 'Notifications' },
      isActive: route.name === 'Notifications',
    },
    {
      name: 'Search',
      icon: 'lucide-search',
      route: { name: 'Search' },
      isActive: route.name === 'Search',
    },
    {
      name: 'You',
      icon: 'lucide-menu',
      route: { name: 'More' },
      isActive: isMoreRoute(),
    },
  ]
})

function isMoreRoute() {
  const name = route.name?.toString() || ''
  return [
    'More',
    'Bookmarks',
    'People',
    'PersonProfile',
    'PersonProfileProfile',
    'PersonProfileAboutMe',
    'PersonProfilePosts',
    'PersonProfileReplies',
    'MyPages',
    'Page',
    'MyTasks',
    'Task',
    'Drafts',
  ].includes(name)
}

function onTabClick(tab: MobileTab) {
  if (tab.name === 'Home' && route.name !== 'Home') {
    router.push(tab.route)
    return
  }

  if (tab.isActive) {
    scrollTo({ top: 0, behavior: 'smooth' })
    return
  }

  router.push(tab.route)
}
</script>
