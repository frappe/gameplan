<template>
  <ScrollAreaViewport
    class="inline-flex h-full flex-1 flex-col overflow-y-auto border-r bg-surface-menu-bar pb-40 w-60"
  >
    <div class="flex flex-col px-2 py-2">
      <UserDropdown />
    </div>
    <div class="flex-1">
      <nav class="space-y-0.5 px-2">
        <AppSidebarLink
          class="group"
          :to="{ name: 'Home' }"
          :isActive="testRoute(/Discussions|Spaces/g)"
        >
          <template #prefix><LucideNewspaper class="h-4 w-4 text-ink-gray-6" /></template>
          Home
          <template #suffix>
            <button
              @click.stop.prevent="showHomePageSettingsDialog = true"
              class="group-hover:opacity-100 opacity-0 transition-opacity flex items-center justify-center p-0.5 hover:bg-surface-gray-1 rounded-sm"
            >
              <LucideSettings2 class="h-4 w-4 text-ink-gray-6" />
            </button>
          </template>
        </AppSidebarLink>
        <AppSidebarLink v-for="link in navigation" :key="link.name" :to="link.route">
          <template #prefix>
            <component :is="link.icon" class="h-4 w-4 text-ink-gray-6" />
          </template>
          {{ link.name }}
          <template #suffix>
            <span v-if="link.count" class="block text-xs text-ink-gray-5">
              {{ link.count }}
            </span>
          </template>
        </AppSidebarLink>
        <button
          v-if="sessionUser.isNotGuest"
          class="flex w-full items-center rounded px-2 py-1 text-ink-gray-7"
          :class="[
            testRoute(/Search/) ? 'bg-surface-selected shadow-sm' : 'hover:bg-surface-gray-2',
          ]"
          @click="showCommandPalette"
        >
          <div class="flex w-full items-center">
            <span class="grid h-5 w-6 place-items-center">
              <LucideSearch class="h-4 w-4 text-ink-gray-6" />
            </span>
            <span class="ml-2 text-sm">Search</span>
            <span class="ml-auto text-sm text-ink-gray-4">
              <template v-if="$platform === 'mac'">⌘K</template>
              <template v-else>Ctrl+K</template>
            </span>
          </div>
        </button>
      </nav>
      <div class="mt-6 flex items-center justify-between px-2">
        <h3 class="px-2 py-1.5 text-sm text-ink-gray-5">Spaces</h3>
        <div class="space-x-1 flex items-center">
          <DropdownMoreOptions
            placement="right"
            :options="[
              { label: 'View all spaces', onClick: () => $router.push({ name: 'Spaces' }) },
              { label: 'New Space', onClick: () => (showAddTeamDialog = true) },
            ]"
          />
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
                <LucideLock v-if="space.is_private" class="flex-shrink-0 h-3 w-3 ml-2" />
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
import { computed, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { noCategories, useGroupedSpaces } from '@/data/groupedSpaces'
import { unreadNotifications } from '@/data/notifications'
import { joinedSpaces, getSpaceUnreadCount } from '@/data/spaces'
import { useSessionUser } from '@/data/users'
import NewSpaceDialog from './NewSpaceDialog.vue'
import AppLink from './AppLink.vue'
import { showCommandPalette } from '@/components/CommandPalette/commandPalette.ts'
import UserDropdown from './UserDropdown.vue'
import { ScrollAreaViewport } from 'reka-ui'
import ScrollBar from './ScrollBar.vue'
import HomePageSettingsDialog from './HomePageSettingsDialog.vue'

import ChevronTriangle from './icons/ChevronTriangle.vue'
import LucideFiles from '~icons/lucide/files'
import LucideInbox from '~icons/lucide/inbox'
import LucideListTodo from '~icons/lucide/list-todo'
import LucideNewspaper from '~icons/lucide/newspaper'
import LucidePlus from '~icons/lucide/plus'
import LucideUsers2 from '~icons/lucide/users-2'
import LucideSettings2 from '~icons/lucide/settings-2'

const showAddTeamDialog = ref(false)
const showHomePageSettingsDialog = ref(false)

const route = useRoute()
const sessionUser = useSessionUser()

const isGroupOpen = reactive<{ [key: string]: boolean }>({})

let groupedSpaces = computed(() => {
  let _groups = useGroupedSpaces({
    filterFn: (space) => !space.archived_at && joinedSpaces.data?.includes(space.name),
  })
  for (let group of _groups.value) {
    isGroupOpen[group.name] = true
  }
  return _groups.value
})

const navigation = computed(() => {
  return [
    {
      name: 'Inbox',
      icon: LucideInbox,
      route: {
        name: 'Notifications',
      },
      count: unreadNotifications.data || 0,
    },
    {
      name: 'Tasks',
      icon: LucideListTodo,
      route: {
        name: 'MyTasks',
      },
      isActive: testRoute(/MyTasks|Task/g),
    },
    {
      name: 'Pages',
      icon: LucideFiles,
      route: {
        name: 'MyPages',
      },
      isActive: testRoute(/MyPages|Page/g),
    },
    {
      name: 'People',
      icon: LucideUsers2,
      route: {
        name: 'People',
      },
      isActive: testRoute(/People|PersonProfile/g),
      condition: () => sessionUser.isNotGuest,
    },
  ].filter((nav) => (nav.condition ? nav.condition() : true))
})

function testRoute(regex: RegExp) {
  return route.name ? regex.test(route.name.toString()) : false
}
</script>
