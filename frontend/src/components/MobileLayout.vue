<template>
  <MobileShell>
    <ReadOnlyBanner v-if="readOnlyMode" />
    <slot />

    <template #nav>
      <MobileNav v-if="!hideMobileNav">
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
import { useRoute, useRouter } from 'vue-router'
import { MobileShell, MobileNav, MobileNavItem } from 'frappe-ui'
import { useSessionUser } from '@/data/users'
import ReadOnlyBanner from './ReadOnlyBanner.vue'
import UserAvatar from './UserAvatar.vue'
import { readOnlyMode } from '@/data/readOnlyMode'

const route = useRoute()
const router = useRouter()
const sessionUser = useSessionUser()

// The app mounts before the first navigation settles, so on a reload `route` is still
// the empty start location and its meta says nothing. Read the meta off the URL being
// loaded until then, or the nav shows for a moment on a page that hides it.
const hideMobileNav = computed(() => {
  const current = route.matched.length ? route : router.resolve(router.options.history.location)
  return Boolean(current.meta.hideMobileNav)
})

const onCommunityRoute = computed(() => route.matched.some((record) => record.meta?.communityScope))

// Home stays lit across every community route, not just the Home page — tapping it
// still navigates home (MobileNavItem decides scroll-vs-navigate off the current route).
const isHomeRoute = computed(() => route.name === 'Home' || onCommunityRoute.value)

// "You" spans the whole More section (profile, pages, tasks, bookmarks, drafts,
// and the settings pages the More menu links to).
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
    'SettingsTab',
    'SettingsCommunity',
  ].includes(name)
})
</script>
