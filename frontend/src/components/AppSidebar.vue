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
        <Links
          :links="navigation"
          class="flex items-center rounded px-2 py-1 text-ink-gray-8 transition"
          active="bg-surface-selected shadow-sm"
          inactive="hover:bg-surface-gray-2"
        >
          <template v-slot="{ link }">
            <div class="flex w-full items-center space-x-2">
              <span class="grid h-5 w-6 place-items-center">
                <component :is="link.icon" class="h-4 w-4 text-ink-gray-7" />
              </span>
              <span class="text-sm">{{ link.name }}</span>
              <span v-if="link.count" class="!ml-auto block text-xs text-ink-gray-5">
                {{ link.count }}
              </span>
            </div>
          </template>
        </Links>
        <button
          v-if="$user().isNotGuest"
          class="flex w-full items-center rounded px-2 py-1 text-ink-gray-8"
          :class="[
            /Search/.test($route.name)
              ? 'bg-surface-selected shadow-sm'
              : 'hover:bg-surface-gray-2',
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
      <div class="mt-6 flex items-center justify-between px-3">
        <h3 class="text-sm font-medium text-ink-gray-5">Spaces</h3>
        <DropdownMoreOptions
          :options="[
            { label: 'New Space', icon: LucidePlus, onClick: () => (showAddTeamDialog = true) },
            { label: 'Browse all spaces', icon: LucideTelescope, route: { name: 'Spaces' } },
          ]"
        />
      </div>
      <nav class="mt-1 space-y-0.5 px-2">
        <div v-for="group in groups" :key="group.name">
          <button
            @click.prevent="
              () => {
                group.open = !group.open
              }
            "
            class="flex w-full items-center px-2 py-1.5 rounded-[6px] hover:bg-surface-gray-3"
          >
            <ChevronTriangle
              class="h-3 w-3 mr-1.5 text-ink-gray-4 transition duration-200"
              :class="[group.open ? 'rotate-90' : 'rotate-0']"
            />
            <div class="flex w-full items-center">
              <span class="text-xs text-ink-gray-8">{{ group.title }}</span>
            </div>
          </button>
          <div class="mb-2 mt-0.5 space-y-0.5 pl-5" v-show="group.open">
            <Link
              v-for="space in group.spaces"
              :key="space.name"
              :link="space"
              ref="($comp) => setProjectRef($comp, project)"
              class="flex h-7 items-center rounded-md px-2 text-ink-gray-8 transition"
              active="bg-surface-selected shadow-sm"
              inactive="hover:bg-surface-gray-2"
            >
              <template v-slot="{ link: space }">
                <span class="inline-flex items-center space-x-2">
                  <span class="flex h-5 w-5 items-center justify-center text-xl">
                    {{ space.icon }}
                  </span>
                  <span class="text-sm">{{ space.title }}</span>
                  <LucideLock v-if="space.is_private" class="h-3 w-3" />
                </span>
              </template>
            </Link>
            <div
              class="flex h-7 items-center px-2 text-sm text-ink-gray-5"
              v-if="group.spaces.length === 0"
            >
              No spaces
            </div>
          </div>
        </div>
      </nav>
      <div v-if="teams.fetched && !activeTeams.length" class="px-3 py-2 text-sm text-ink-gray-4">
        No teams
      </div>
    </div>
    <NewSpaceDialog v-model="showAddTeamDialog" />
  </div>
</template>
<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import Links from './Links.vue'
import Link from './Link.vue'
import UserDropdown from './UserDropdown.vue'
import ChevronTriangle from './icons/ChevronTriangle.vue'
import { activeTeams, teams } from '@/data/teams'
import { getTeamProjects } from '@/data/projects'
import { unreadNotifications } from '@/data/notifications'
import { showCommandPalette } from '@/components/CommandPalette/CommandPalette.vue'
import LucideUsers2 from '~icons/lucide/users-2'
import LucideInbox from '~icons/lucide/inbox'
import LucideListTodo from '~icons/lucide/list-todo'
import LucideNewspaper from '~icons/lucide/newspaper'
import LucideFiles from '~icons/lucide/files'
import LucidePlus from '~icons/lucide/plus'
import LucideTelescope from '~icons/lucide/telescope'
import DropdownMoreOptions from './DropdownMoreOptions.vue'
import NewSpaceDialog from './NewSpaceDialog.vue'
import { useSessionUser } from '@/data/users'
import { useSidebarResize } from '@/utils/sidebarResize'
import { projects as spaces } from '@/data/projects'

const { startResize, sidebarResizing, sidebarWidth } = useSidebarResize()
const showAddTeamDialog = ref(false)

const route = useRoute()
const sessionUser = useSessionUser()

const joinedSpaces = computed(() => {
  return spaces.data
    .filter((space) => space.members.find((member) => member.user === sessionUser.name))
    .map((space) => space.name)
})

const groups = computed(() => {
  return activeTeams.value
    .map((team) => {
      team.spaces = getTeamProjects(team.name).filter(
        (project) => !project.archived_at && joinedSpaces.value.includes(project.name),
      )
      return team
    })
    .filter((team) => team.spaces.length)
})

const navigation = computed(() => {
  return [
    {
      name: 'Discussions',
      icon: LucideNewspaper,
      route: {
        name: 'Discussions',
      },
    },
    {
      name: 'My Tasks',
      icon: LucideListTodo,
      route: {
        name: 'MyTasks',
      },
      isActive: /MyTasks|Task/g.test(route.name),
    },
    {
      name: 'My Pages',
      icon: LucideFiles,
      route: {
        name: 'MyPages',
      },
      isActive: /MyPages|Page/g.test(route.name),
    },
    {
      name: 'People',
      icon: LucideUsers2,
      route: {
        name: 'People',
      },
      isActive: /People|PersonProfile/g.test(route.name),
      condition: () => sessionUser.isNotGuest,
    },
    {
      name: 'Notifications',
      icon: LucideInbox,
      route: {
        name: 'Notifications',
      },
      count: unreadNotifications.data || 0,
    },
  ].filter((nav) => (nav.condition ? nav.condition() : true))
})
</script>
