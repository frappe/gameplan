<template>
  <ScrollAreaViewport
    @mouseenter="onMouseEnter"
    @mouseleave="onMouseLeave"
    class="inline-flex group/sidebar h-full flex-1 flex-col overflow-y-auto border-r bg-surface-menu-bar pb-40 w-60"
  >
    <div class="flex flex-col px-2 py-2">
      <UserDropdown />
    </div>
    <div class="flex-1">
      <nav class="space-y-0.5 px-2">
        <AppSidebarLink
          class="group"
          :to="{ name: 'Home' }"
          :isActive="
            preferredHomePage === 'Discussions' ? testRoute(/Discussions/g) : testRoute(/Spaces/g)
          "
        >
          <template #prefix>
            <span
              v-if="preferredHomePage === 'Discussions'"
              class="lucide-newspaper h-4 w-4 text-ink-gray-6"
            />
            <span v-else class="lucide-layout-grid h-4 w-4 text-ink-gray-6" />
          </template>
          {{ preferredHomePage }}
          <template #suffix>
            <button
              @click.stop.prevent="showHomePageSettingsDialog = true"
              class="transition-opacity flex items-center justify-center p-0.5 hover:bg-surface-gray-1 rounded-sm"
              :class="{ 'opacity-100': showButtons, 'opacity-0': !showButtons }"
            >
              <span class="lucide-settings-2 h-4 w-4 text-ink-gray-6" />
            </button>
          </template>
        </AppSidebarLink>
        <AppSidebarLink
          v-for="link in navigation"
          :key="link.name"
          :to="link.route"
          :isActive="link.isActive"
        >
          <template #prefix>
            <span :class="[link.icon, 'h-4 w-4 text-ink-gray-6']" />
          </template>
          {{ link.name }}
          <template #suffix>
            <span v-if="link.count" class="block text-xs text-ink-gray-5">
              {{ link.count }}
            </span>
            <span v-if="link.name === 'Search'">
              <span class="text-sm text-ink-gray-4">
                <template v-if="$platform === 'mac'">⌘K</template>
                <template v-else>Ctrl+K</template>
              </span>
            </span>
          </template>
        </AppSidebarLink>
      </nav>
      <div class="mt-6 flex items-center justify-between px-2">
        <h3 class="px-2 py-1.5 text-sm text-ink-gray-5">Spaces</h3>
        <div class="space-x-1 flex items-center">
          <Button
            class="transition-opacity"
            :class="{ 'opacity-100': showButtons, 'opacity-0': !showButtons }"
            variant="ghost"
            @click="toggleAllGroups"
            :tooltip="allGroupsExpanded ? 'Collapse all' : 'Expand all'"
          >
            <span v-if="allGroupsExpanded" class="lucide-fold-vertical size-4 text-ink-gray-6" />
            <span v-else class="lucide-unfold-vertical size-4 text-ink-gray-6" />
          </Button>
          <Dropdown
            align="end"
            :options="[
              {
                label: 'Show all spaces',
                onClick: () => setSpaceFilter('all'),
                icon: spaceFilter === 'all' ? 'lucide-check' : undefined,
              },
              {
                label: 'Show joined spaces',
                onClick: () => setSpaceFilter('joined'),
                icon: spaceFilter === 'joined' ? 'lucide-check' : undefined,
              },
            ]"
            v-slot="{ open }"
          >
            <Button
              :variant="open ? 'subtle' : 'ghost'"
              class="transition-opacity focus:opacity-100"
              :class="{ 'opacity-100': showButtons || open, 'opacity-0': !showButtons && !open }"
            >
              <span class="lucide-more-horizontal size-4 text-ink-gray-6" />
            </Button>
          </Dropdown>
        </div>
      </div>
      <nav class="mt-1 space-y-1 px-2">
        <div v-for="group in groupedSpaces" :key="group.name">
          <button
            v-show="!noCategories"
            @click.prevent="
              () => {
                isGroupOpen[group.name] = !isGroupOpen[group.name]
              }
            "
            class="flex w-full items-center px-2 py-1.5 rounded hover:bg-surface-gray-2"
          >
            <ChevronTriangle
              class="h-3 w-3 ml-1.5 mr-1.5 text-ink-gray-4 transition duration-200"
              :class="[isGroupOpen[group.name] ? 'rotate-90' : 'rotate-0']"
            />
            <div class="flex w-full items-center">
              <span class="text-sm text-ink-gray-7">{{ group.title }}</span>
            </div>
          </button>
          <div
            class="mb-2 mt-0.5 space-y-0.5"
            :class="!noCategories && 'pl-6'"
            v-show="isGroupOpen[group.name]"
          >
            <AppLink
              v-for="space in group.spaces"
              :key="space.name"
              :to="{ name: 'Space', params: { spaceId: space.name } }"
              class="flex h-7 items-center rounded px-2 text-ink-gray-7 transition"
              activeClass="bg-surface-selected shadow-sm"
              inactiveClass="hover:bg-surface-gray-2"
            >
              <span class="inline-flex min-w-0 items-center w-full">
                <span class="flex-shrink-0 flex h-5 w-6 items-center justify-center text-xl">
                  {{ space.icon }}
                </span>
                <span class="truncate text-sm flex-grow w-full ml-2">
                  {{ space.title }}
                </span>
                <span v-if="space.is_private" class="lucide-lock flex-shrink-0 h-3 w-3 ml-2" />
                <span
                  v-if="getSpaceUnreadCount(space.name) > 0"
                  class="ml-auto pl-2 text-xs text-ink-gray-5"
                >
                  {{ getSpaceUnreadCount(space.name) }}
                </span>
              </span>
            </AppLink>
            <div
              class="flex h-7 items-center px-2 text-sm text-ink-gray-5"
              v-if="group.spaces.length === 0"
            >
              No spaces
            </div>
          </div>
        </div>
      </nav>
    </div>
    <NewSpaceDialog v-model="showAddTeamDialog" />
  </ScrollAreaViewport>
  <ScrollBar />
  <HomePageSettingsDialog v-model="showHomePageSettingsDialog" />
</template>
<script setup lang="ts">
import { computed, ref, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { Dropdown } from 'frappe-ui'
import { useLocalStorage } from '@vueuse/core'
import { noCategories, useGroupedSpaces } from '@/data/groupedSpaces'
import { unreadNotifications } from '@/data/notifications'
import { joinedSpaces, getSpaceUnreadCount } from '@/data/spaces'
import { useSessionUser } from '@/data/users'
import { usePreferredHomePage } from '@/composables/usePreferredHomePage'
import NewSpaceDialog from './NewSpaceDialog.vue'
import AppSidebarLink from './AppSidebarLink.vue'
import AppLink from './AppLink.vue'
import UserDropdown from './UserDropdown.vue'
import { ScrollAreaViewport } from 'reka-ui'
import ScrollBar from './ScrollBar.vue'
import HomePageSettingsDialog from './HomePageSettingsDialog.vue'

import ChevronTriangle from './icons/ChevronTriangle.vue'
const showAddTeamDialog = ref(false)
const showHomePageSettingsDialog = ref(false)
const preferredHomePage = usePreferredHomePage()

const spaceFilter = useLocalStorage<'all' | 'joined'>('gameplan:spaceFilter', 'joined')
const isGroupOpen = useLocalStorage<{ [key: string]: boolean }>('gameplan:groupOpenState', {})

const route = useRoute()
const sessionUser = useSessionUser()

let groupedSpaces = computed(() => {
  let _groups = useGroupedSpaces({
    filterFn: (space) => {
      const isNotArchived = !space.archived_at
      if (spaceFilter.value === 'all') {
        return isNotArchived
      } else {
        return isNotArchived && joinedSpaces.data?.includes(space.name)
      }
    },
  })
  for (let group of _groups.value) {
    if (isGroupOpen.value[group.name] === undefined) {
      isGroupOpen.value[group.name] = true
    }
  }
  return _groups.value
})

function setSpaceFilter(filter: 'all' | 'joined') {
  spaceFilter.value = filter
}

const allGroupsExpanded = computed(() => {
  if (groupedSpaces.value.length === 0) return true
  return groupedSpaces.value.every((group) => isGroupOpen.value[group.name] === true)
})

function toggleAllGroups() {
  const shouldExpand = !allGroupsExpanded.value
  groupedSpaces.value.forEach((group) => {
    isGroupOpen.value[group.name] = shouldExpand
  })
}

const navigation = computed(() => {
  return [
    {
      name: 'Spaces',
      icon: 'lucide-layout-grid',
      route: {
        name: 'Spaces',
      },
      isActive: testRoute(/Spaces/g),
      condition: () => preferredHomePage.value == 'Discussions',
    },
    {
      name: 'Discussions',
      icon: 'lucide-newspaper',
      route: {
        name: 'DiscussionsTab',
        params: { feedType: 'recent' },
      },
      isActive: testRoute(/Discussions/g),
      condition: () => preferredHomePage.value == 'Spaces',
    },
    {
      name: 'Inbox',
      icon: 'lucide-inbox',
      route: {
        name: 'Notifications',
      },
      count: unreadNotifications.data || 0,
      isActive: testRoute(/Notifications/g),
    },
    {
      name: 'Drafts',
      icon: 'lucide-pencil-line',
      route: {
        name: 'Drafts',
      },
      isActive: testRoute(/Drafts/g),
    },
    {
      name: 'Tasks',
      icon: 'lucide-list-todo',
      route: {
        name: 'MyTasks',
      },
      isActive: testRoute(/MyTasks|Task/g),
    },
    {
      name: 'Pages',
      icon: 'lucide-files',
      route: {
        name: 'MyPages',
      },
      isActive: testRoute(/MyPages|Page/g),
    },
    {
      name: 'People',
      icon: 'lucide-users-2',
      route: {
        name: 'People',
      },
      isActive: testRoute(/People|PersonProfile/g),
      condition: () => sessionUser.isNotGuest,
    },
    {
      name: 'Search',
      icon: 'lucide-search',
      route: {
        name: 'Search',
      },
      isActive: testRoute(/Search/g),
    },
  ].filter((nav) => (nav.condition ? nav.condition() : true))
})

function testRoute(regex: RegExp) {
  return route.name ? regex.test(route.name.toString()) : false
}

// Show/hide buttons on hover

const showButtons = ref(false)
let hideTimeout: ReturnType<typeof setTimeout> | null = null

function onMouseEnter() {
  showButtons.value = true
  if (hideTimeout) {
    clearTimeout(hideTimeout)
    hideTimeout = null
  }
}

function onMouseLeave() {
  if (showButtons.value) {
    hideTimeout = setTimeout(() => {
      showButtons.value = false
    }, 2000)
  }
}

onUnmounted(() => {
  if (hideTimeout) {
    clearTimeout(hideTimeout)
  }
})
</script>
