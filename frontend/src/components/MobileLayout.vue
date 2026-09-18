<template>
  <MobileShell>
    <ReadOnlyBanner v-if="readOnlyMode" />
    <slot />

    <template #nav>
      <MobileNav v-if="!isNewCommentOpen">
        <MobileNavItem
          label="Home"
          icon="lucide-home"
          :to="{ name: 'Home' }"
          :active="isHomeRoute"
        />
        <MobileNavItem
          label="Notifications"
          icon="lucide-bell"
          :to="{ name: 'Notifications' }"
          :active="route.name === 'Notifications'"
        />
        <MobileNavItem
          label="Search"
          icon="lucide-search"
          :to="{ name: 'Search' }"
          :active="route.name === 'Search'"
        />
        <MobileNavItem label="You" :to="{ name: 'More' }" :active="isMoreRoute">
          <template #default="{ active }">
            <UserAvatar
              v-if="sessionUser.name"
              :user="sessionUser.name"
              class="size-6"
              :class="active ? 'ring-2 ring-outline-gray-4' : ''"
            />
            <span
              v-else
              class="lucide-menu size-6"
              :class="active ? 'text-ink-gray-8' : 'text-ink-gray-5'"
              aria-hidden="true"
            />
          </template>
        </MobileNavItem>
      </MobileNav>
    </template>
  </MobileShell>
</template>

<script setup lang="ts">
defineOptions({
  inheritAttrs: false,
})

import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { MobileShell, MobileNav, MobileNavItem } from 'frappe-ui'
import { isNewCommentOpen } from '@/data/newComment'
import { useSessionUser } from '@/data/users'
import ReadOnlyBanner from './ReadOnlyBanner.vue'
import UserAvatar from './UserAvatar.vue'
import { readOnlyMode } from '@/data/readOnlyMode'

const route = useRoute()
const sessionUser = useSessionUser()

const onCommunityRoute = computed(() => route.matched.some((record) => record.meta?.communityScope))

// Home stays lit across every community route, not just the Home page — tapping it
// still navigates home (MobileNavItem decides scroll-vs-navigate off the current route).
const isHomeRoute = computed(() => route.name === 'Home' || onCommunityRoute.value)

// "You" spans the whole More section (profile, pages, tasks, bookmarks, drafts).
const isMoreRoute = computed(() => {
  const name = route.name?.toString() || ''
  return [
    'More',
    'Bookmarks',
    'People',
    'PersonProfile',
    'PersonProfileProfile',
    'PersonProfilePosts',
    'PersonProfileReplies',
    'MyPages',
    'Page',
    'MyTasks',
    'Task',
    'Drafts',
  ].includes(name)
})
</script>
