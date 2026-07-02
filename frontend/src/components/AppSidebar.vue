<template>
  <div class="flex h-full w-56 flex-col bg-surface-sidebar">
    <template v-if="communityState.doc">
      <div class="flex shrink-0 items-center p-2">
        <AppDropdown v-if="session.isAuthenticated" />
        <div v-else class="flex h-9 min-w-0 items-center px-2 text-lg-medium text-ink-gray-7">
          <span class="truncate">Gameplan</span>
        </div>
      </div>

      <ScrollAreaRoot class="relative flex min-h-0 flex-1 flex-col">
        <ScrollAreaViewport class="h-full w-full overflow-y-auto px-2 pt-0.5 pb-10">
          <div class="group/spaces">
            <div class="flex h-7 items-center justify-between pl-2 text-base text-ink-gray-5">
              <span>Spaces</span>
              <div class="flex items-center">
                <Dropdown v-if="session.isAuthenticated" :options="spaceSortOptions" align="end">
                  <template #trigger="{ open }">
                    <Button
                      variant="ghost"
                      size="sm"
                      icon="lucide-arrow-up-down text-ink-gray-5"
                      label="Sort spaces"
                      tooltip="Sort spaces"
                      :active="open || hasCustomSpaceSidebarOptions"
                    />
                  </template>
                </Dropdown>
                <Button
                  v-if="session.isAuthenticated"
                  variant="ghost"
                  size="sm"
                  icon="lucide-plus text-ink-gray-5"
                  label="New space"
                  @click="openNewSpaceDialog"
                />
              </div>
            </div>

            <nav class="mt-0.5 space-y-0.5">
              <div
                v-for="space in spacesList"
                :key="space.name"
                class="group/space flex h-7 items-center rounded transition"
                :class="
                  isActiveSpace(space.name)
                    ? 'bg-surface-elevation-3 text-ink-gray-8 shadow-sm'
                    : 'text-ink-gray-6 hover:bg-surface-gray-2'
                "
              >
                <AppLink
                  :to="{ name: 'Space', params: { communityId: space.team, spaceId: space.name } }"
                  class="flex h-full min-w-0 flex-1 items-center pl-2"
                  activeClass=""
                  inactiveClass=""
                >
                  <span class="flex w-full min-w-0 items-center">
                    <SpaceIcon :icon="space.icon" class="size-4" />
                    <span class="ml-2 flex-1 truncate text-sm">{{ space.title }}</span>
                    <LucideLock
                      v-if="space.is_private"
                      class="ml-1 size-3 shrink-0 text-ink-gray-5"
                    />
                  </span>
                </AppLink>
                <div
                  v-if="session.isAuthenticated"
                  class="relative mr-1 flex h-7 w-7 shrink-0 items-center justify-end"
                >
                  <span
                    v-if="getSpaceUnreadCount(space.name) > 0"
                    class="absolute right-1 text-xs text-ink-gray-5 transition-opacity group-hover/space:opacity-0 group-focus-within/space:opacity-0"
                  >
                    {{ getSpaceUnreadCount(space.name) }}
                  </span>
                  <Dropdown :options="spaceOptions(space)" align="start" side="right">
                    <template #default="{ open }">
                      <Button
                        :variant="open ? 'subtle' : 'ghost'"
                        size="xs"
                        icon="lucide-more-horizontal text-ink-gray-5"
                        :label="`${space.title} options`"
                        class="absolute right-0 opacity-0 group-hover/space:opacity-100 group-focus-within/space:opacity-100 -mr-0.5"
                        :class="open ? 'opacity-100' : ''"
                      />
                    </template>
                  </Dropdown>
                </div>
              </div>

              <div
                v-if="spacesList.length === 0"
                class="mt-1 px-2 text-xs leading-relaxed text-ink-gray-5"
              >
                {{ communitySpaces.emptyMessage }}
                <Button
                  v-if="
                    session.isAuthenticated &&
                    communitySpaces.archived.length === 0 &&
                    !communitySpaces.hasHiddenInactive
                  "
                  size="sm"
                  icon-left="lucide-plus"
                  class="mt-2"
                  @click="openNewSpaceDialog"
                >
                  Create a space
                </Button>
              </div>
            </nav>
          </div>
        </ScrollAreaViewport>
        <ScrollBar />
      </ScrollAreaRoot>
    </template>
  </div>

  <NewSpaceDialog
    v-if="session.isAuthenticated"
    v-model="showNewSpaceDialog"
    :lockedCommunityId="communityState.id ?? undefined"
  />
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ScrollAreaRoot, ScrollAreaViewport } from 'reka-ui'
import { Button, Dropdown } from 'frappe-ui'
import type { DropdownOptions } from 'frappe-ui'
import { communityState } from '@/data/communityState'
import { communitySpaces } from '@/data/communitySpaces'
import {
  currentHideInactiveSpaces,
  currentSpaceSidebarSort,
  setHideInactiveSpaces,
  setSpaceSidebarSort,
  type SpaceSidebarSort,
} from '@/data/sidebarPreferences'
import { getSpaceUnreadCount, markAllAsRead, spaces, type Space } from '@/data/spaces'
import { session } from '@/data/session'
import AppLink from './AppLink.vue'
import AppDropdown from './AppDropdown.vue'
import NewSpaceDialog from './NewSpaceDialog.vue'
import ScrollBar from './ScrollBar.vue'
import SpaceIcon from './SpaceIcon.vue'
import LucideLock from '~icons/lucide/lock'

const route = useRoute()

const spacesList = computed(() => communitySpaces.list)
const hasCustomSpaceSidebarOptions = computed(() => {
  return currentSpaceSidebarSort.value !== 'Recent activity' || currentHideInactiveSpaces.value
})

const spaceSortOptions = computed<DropdownOptions>(() => [
  {
    group: 'Sort by',
    options: spaceSortValues.map((sort) => ({
      label: sort,
      icon: currentSpaceSidebarSort.value === sort ? 'lucide-check' : null,
      onClick: () => setSpaceSidebarSort(sort),
    })),
  },
  {
    group: 'Visibility',
    options: [
      {
        label: 'Hide inactive spaces',
        description: 'No activity for 2 months',
        switch: true,
        switchValue: currentHideInactiveSpaces.value,
        onClick: setHideInactiveSpaces,
      },
    ],
  },
])

const showNewSpaceDialog = ref(false)
const spaceSortValues: SpaceSidebarSort[] = ['Recent activity', 'Alphabetical']
const communitySpaceList = computed(() => {
  return (spaces.data || []).filter((space) => {
    return !space.archived_at && space.team === communityState.id
  })
})
const activeSpaceId = computed(() => {
  const routeName = route.name?.toString() || ''
  if (routeName.startsWith('Space') || routeName === 'Discussion') {
    return route.params.spaceId?.toString() || null
  }
  if (routeName === 'NewDiscussion') return routeQueryString(route.query.spaceId)
  return null
})

function isActiveSpace(spaceId: string) {
  return activeSpaceId.value === spaceId
}

function openNewSpaceDialog() {
  showNewSpaceDialog.value = true
}

function spaceOptions(space: Space) {
  return [
    {
      label: 'Mark all as read',
      icon: 'lucide-check',
      onClick: () => markAllAsRead([space.name], space.title),
    },
  ]
}

function routeQueryString(value: unknown): string | null {
  const resolved = Array.isArray(value) ? value[0] : value
  return typeof resolved === 'string' && resolved.length > 0 ? resolved : null
}
</script>
