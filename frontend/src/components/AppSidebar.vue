<template>
  <div
    class="absolute right-0 z-10 h-full w-1 cursor-col-resize bg-surface-gray-4 opacity-0 transition-opacity hover:opacity-100"
    :class="{ 'opacity-100': sidebarResizing }"
    @mousedown="startResize"
  />
  <div
    v-show="sidebarResizing"
    class="fixed z-20 mt-3 -translate-x-[130%] rounded-md bg-surface-gray-6 px-2 py-1 text-base text-ink-white"
    :style="{ left: sidebarWidth + 'px' }"
  >
    {{ sidebarWidth }}
  </div>

  <div
    class="inline-flex h-full flex-1 flex-col overflow-auto border-r bg-surface-menu-bar pb-40"
    :style="{ width: `${sidebarWidth}px` }"
  >
    <div class="flex flex-col px-2 py-2">
      <UserDropdown />
    </div>
    <div class="flex-1">
      <nav class="space-y-0.5 px-2">
        <AppLink
          v-for="link in navigation"
          :key="link.name"
          :to="link.route"
          class="flex items-center rounded px-2 py-1 text-ink-gray-8 transition"
          activeClass="bg-surface-selected shadow-sm"
          inactiveClass="hover:bg-surface-gray-2"
        >
          <div class="flex w-full items-center space-x-2">
            <span class="grid h-5 w-6 place-items-center">
              <component :is="link.icon" class="h-4 w-4 text-ink-gray-7" />
            </span>
            <span class="text-sm">{{ link.name }}</span>
            <span v-if="link.count" class="!ml-auto block text-xs text-ink-gray-5">
              {{ link.count }}
            </span>
          </div>
        </AppLink>
        <button
          v-if="sessionUser.isNotGuest"
          class="flex w-full items-center rounded px-2 py-1 text-ink-gray-8"
          :class="[
            testRoute(/Search/) ? 'bg-surface-selected shadow-sm' : 'hover:bg-surface-gray-2',
          ]"
          @click="showCommandPalette"
        >
          <div class="flex w-full items-center">
            <span class="grid h-5 w-6 place-items-center">
              <LucideSearch class="h-4 w-4 text-ink-gray-7" />
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
        <AppLink
          class="flex w-full items-center justify-between group px-2 py-1.5 rounded hover:bg-surface-gray-2"
          :to="{ name: 'Spaces' }"
        >
          <h3 class="text-sm text-ink-gray-5">Spaces</h3>
          <span class="text-sm text-ink-gray-5 invisible group-hover:visible">Show all</span>
        </AppLink>
        <div class="space-x-1 flex items-center">
          <Button variant="ghost" @click="showAddTeamDialog = true">
            <template #icon>
              <LucidePlus class="h-4 w-4 text-ink-gray-7" />
            </template>
          </Button>
        </div>
      </div>
      <nav class="mt-1 space-y-1 px-2">
        <div v-for="group in groupedSpaces" :key="group.name">
          <button
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
              <span class="text-sm text-ink-gray-8">{{ group.title }}</span>
            </div>
          </button>
          <div class="mb-2 mt-0.5 space-y-0.5 pl-6" v-show="isGroupOpen[group.name]">
            <AppLink
              v-for="space in group.spaces"
              :key="space.name"
              :to="{ name: 'Space', params: { spaceId: space.name } }"
              class="flex h-7 items-center rounded px-2 text-ink-gray-8 transition"
              activeClass="bg-surface-selected shadow-sm"
              inactiveClass="hover:bg-surface-gray-2"
            >
              <span class="inline-flex min-w-0 items-center space-x-2">
                <span class="flex-shrink-0 flex h-5 w-6 items-center justify-center text-xl">
                  {{ space.icon }}
                </span>
                <span class="truncate text-sm flex-grow">
                  {{ space.title }}
                </span>
                <LucideLock v-if="space.is_private" class="flex-shrink-0 h-3 w-3" />
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
      <div v-if="teams.isFinished && !activeTeams.length" class="px-3 py-2 text-sm text-ink-gray-4">
        No teams
      </div>
    </div>
    <NewSpaceDialog v-model="showAddTeamDialog" />
  </div>
</template>
<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useGroupedSpaces } from '@/data/groupedSpaces'
import { unreadNotifications } from '@/data/notifications'
import { joinedSpaces, spaces } from '@/data/spaces'
import { activeTeams, teams } from '@/data/teams'
import { useSessionUser } from '@/data/users'
import { useSidebarResize } from '@/utils/sidebarResize'
import NewSpaceDialog from './NewSpaceDialog.vue'
import AppLink from './AppLink.vue'
import { showCommandPalette } from '@/components/CommandPalette/commandPalette.ts'
import UserDropdown from './UserDropdown.vue'

import ChevronTriangle from './icons/ChevronTriangle.vue'
import LucideFiles from '~icons/lucide/files'
import LucideInbox from '~icons/lucide/inbox'
import LucideListTodo from '~icons/lucide/list-todo'
import LucideNewspaper from '~icons/lucide/newspaper'
import LucidePlus from '~icons/lucide/plus'
import LucideUsers2 from '~icons/lucide/users-2'

const { startResize, sidebarResizing, sidebarWidth } = useSidebarResize()
const showAddTeamDialog = ref(false)

const route = useRoute()
const sessionUser = useSessionUser()

let groupedSpaces = useGroupedSpaces({
  filterFn: (space) => !space.archived_at && joinedSpaces.data?.includes(space.name),
})

const isGroupOpen = reactive<{ [key: string]: boolean }>({})
let unwatch = watch(
  () => teams.isFinished && spaces.isFinished,
  (val) => {
    if (val) {
      for (let group of groupedSpaces.value) {
        isGroupOpen[group.name] = true
      }
      unwatch()
    }
  },
)

const navigation = computed(() => {
  return [
    {
      name: 'Home',
      icon: LucideNewspaper,
      route: {
        name: 'Discussions',
      },
      open: true,
    },
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
